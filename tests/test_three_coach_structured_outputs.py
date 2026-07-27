from __future__ import annotations

import json
from pathlib import Path

import pytest

from badminton_coach_skill.coach_registry import load_coach_knowledge
from badminton_coach_skill.issue_matcher import match_diagnosis


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
    diagnosis = match_diagnosis(
        payload["player_profile"],
        payload["video_observation"],
        load_coach_knowledge(coach_id, ROOT),
    )
    assert expected_issue in diagnosis["priority_order"]
    assert diagnosis["training_plan"]
    assert diagnosis["retest_metrics"]
