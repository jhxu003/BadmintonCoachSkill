from __future__ import annotations

import json
from pathlib import Path

import pytest

from badminton_coach_skill.coach_registry import find_topic_teaching_units, load_coach_knowledge
from badminton_coach_skill.issue_matcher import match_diagnosis
from badminton_coach_skill.student_plan_presenter import validate_presentation_coverage
from badminton_coach_skill.teaching_plan import generate_coaching_plan


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("coach_id", "observation_name", "expected_issue"),
    [
        ("liu-hui", "high_clear_late_arrival.json", "late-arrival"),
        ("li-yuxuan", "li_yuxuan_rear_clear_timing.json", "lyx-late-start"),
        ("zheng-siwei", "zheng_siwei_front_player_watching.json", "zsw-front-player-disconnected"),
    ],
)
def test_each_coach_converts_structured_observation_to_teaching(
    coach_id: str, observation_name: str, expected_issue: str
) -> None:
    payload = json.loads(
        (ROOT / "examples" / "observations" / observation_name).read_text(encoding="utf-8")
    )
    knowledge = load_coach_knowledge(coach_id, ROOT)
    validate_presentation_coverage(knowledge)
    source_topic_index = knowledge["source_topic_index"]
    assert source_topic_index["coach_id"] == coach_id
    assert source_topic_index["source_count"] > 0
    assert source_topic_index["sources"]
    topic_units = knowledge["topic_teaching_units"]
    assert topic_units["coach_id"] == coach_id
    assert topic_units["unit_count"] > 0
    assert all(unit["source_ids"] for unit in topic_units["units"])
    first_unit = topic_units["units"][0]
    assert find_topic_teaching_units(
        coach_id,
        ROOT,
        topic_id=first_unit["topic_id"],
        source_id=first_unit["source_ids"][0],
    ) == [first_unit]
    diagnosis = match_diagnosis(
        payload["player_profile"],
        payload["video_observation"],
        knowledge,
    )
    assert expected_issue in diagnosis["priority_order"]
    assert diagnosis["training_plan"]
    assert diagnosis["retest_metrics"]
    plan = generate_coaching_plan(
        coach_id=coach_id,
        player_profile=payload["player_profile"],
        video_observation=payload["video_observation"],
        root=ROOT,
    )
    focus = plan["lesson_focus"]
    assert focus is not None
    assert focus["now"]["issue_id"] == expected_issue
    assert len(focus["next"]) <= 2
    assert [item["issue_id"] for item in plan["teaching_sequence"]][0] == expected_issue
