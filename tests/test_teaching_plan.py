from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from badminton_coach_skill.teaching_plan import (
    _select_topic_lessons,
    generate_coaching_plan,
    main,
    serialize_coaching_plan,
)
from badminton_coach_skill.coach_media.video_lessons import load_video_lessons
from badminton_coach_skill.web.app import create_app
from badminton_coach_skill.web.database import Database
from badminton_coach_skill.web.demonstration_runner import run_demonstration_job
from badminton_coach_skill.web.jobs import create_demonstration_job
from badminton_coach_skill.web.media_store import LocalMediaStore
from badminton_coach_skill.web.settings import Settings


ROOT = Path(__file__).resolve().parents[1]


def _payload(name: str) -> dict[str, object]:
    return json.loads((ROOT / "examples" / "observations" / name).read_text(encoding="utf-8"))


def test_liu_hui_plan_focuses_diagnosis_and_does_not_borrow_wrong_topic_lesson() -> None:
    payload = _payload("high_clear_late_arrival.json")
    plan = generate_coaching_plan(
        coach_id="liu-hui",
        player_profile=payload["player_profile"],  # type: ignore[arg-type]
        video_observation=payload["video_observation"],  # type: ignore[arg-type]
        root=ROOT,
    )
    assert plan["report_type"] == "structured_coaching_plan"
    assert plan["teaching_sequence"]
    assert plan["lesson_focus"]["now"]["issue_id"] == "late-arrival"  # type: ignore[index]
    assert plan["lesson_focus"]["now"]["topic_unit"]["topic_id"] == "liu-rear-footwork"  # type: ignore[index]
    assert plan["lesson_focus"]["now"]["topic_unit"]["media_status"] == "knowledge_only_no_reviewed_media"  # type: ignore[index]
    # The installed high-clear package is not the audited rear-footwork
    # package, so it must not be borrowed just because the action matches.
    assert plan["video_lesson_status"] == "no_reliable_video_lesson_package"
    serialized = serialize_coaching_plan(plan)
    assert "_video_lessons" not in serialized
    assert not serialized["video_lessons"]


def test_liu_hui_big_arm_issue_prefers_exact_overhead_path_topic() -> None:
    plan = generate_coaching_plan(
        coach_id="liu-hui",
        player_profile={
            "level": "intermediate",
            "dominant_hand": "right",
            "training_goal": "technique_diagnosis",
        },
        video_observation={
            "action": "smash",
            "camera_view": "side",
            "fps_quality": "high",
            "phase_observations": {"arm_path": "big_arm_pull"},
        },
        root=ROOT,
    )
    assert plan["diagnosis"]["issues"][0]["issue_id"] == "big-arm-dominant-swing"  # type: ignore[index]
    topic = plan["lesson_focus"]["now"]["topic_unit"]  # type: ignore[index]
    assert topic["topic_id"] == "liu-overhead-arm-path-release"  # type: ignore[index]
    # The public checkout has no private staged package; fail closed rather
    # than borrowing the unrelated match-transfer source topic.
    assert topic["media_status"] == "reviewed_media_unavailable"  # type: ignore[index]
    assert not plan["_video_lessons"]


def test_zheng_siwei_plan_keeps_video_course_gap_explicit() -> None:
    payload = _payload("zheng_siwei_front_player_watching.json")
    plan = generate_coaching_plan(
        coach_id="zheng-siwei",
        player_profile=payload["player_profile"],  # type: ignore[arg-type]
        video_observation=payload["video_observation"],  # type: ignore[arg-type]
        root=ROOT,
    )
    assert plan["video_lesson_status"] == "no_reliable_video_lesson_package"
    assert plan["teaching_sequence"][0]["issue_id"] == "zsw-front-player-disconnected"  # type: ignore[index]
    assert plan["lesson_focus"]["now"]["topic_unit"]["topic_id"] == "zsw-net-pressure"  # type: ignore[index]
    assert not plan["_video_lessons"]


def test_auto_recommends_one_compatible_lens_and_explicit_choice_wins() -> None:
    payload = _payload("high_clear_late_arrival.json")
    auto_plan = generate_coaching_plan(
        coach_id="auto",
        player_profile=payload["player_profile"],  # type: ignore[arg-type]
        video_observation=payload["video_observation"],  # type: ignore[arg-type]
        root=ROOT,
    )
    assert auto_plan["requested_coach_id"] == "auto"
    assert auto_plan["recommendation_mode"] == "auto_recommended_teaching_lens"
    lenses = auto_plan["coach_lenses"]
    assert sum(bool(item["selected"]) for item in lenses) == 1  # type: ignore[index]
    assert {item["coach_id"] for item in lenses} == {"liu-hui", "li-yuxuan"}  # type: ignore[index]

    explicit_plan = generate_coaching_plan(
        coach_id="liu-hui",
        player_profile=payload["player_profile"],  # type: ignore[arg-type]
        video_observation=payload["video_observation"],  # type: ignore[arg-type]
        root=ROOT,
    )
    assert explicit_plan["coach_id"] == "liu-hui"
    assert explicit_plan["recommendation_mode"] == "explicit_coach_selection"
    assert next(item for item in explicit_plan["coach_lenses"] if item["selected"])["coach_id"] == "liu-hui"  # type: ignore[index]


def test_low_evidence_stays_fail_closed_without_focus_or_lesson() -> None:
    payload = _payload("high_clear_late_arrival.json")
    observation = dict(payload["video_observation"])
    observation.update(
        {
            "camera_view": "front",
            "fps_quality": "low",
            "contact_point": "not_visible",
            "elbow_height_before_hit": "not_visible",
            "wrist_elbow_sequence": "not_visible",
            "hip_shoulder_sequence": "not_visible",
            "racket_side_structure": "not_visible",
            "follow_through": "not_visible",
            "footwork_observations": {"arrival_timing": "not_visible", "recovery": "not_visible"},
            "missing_observations": [
                "contact_point", "elbow_height_before_hit", "wrist_elbow_sequence",
                "hip_shoulder_sequence", "racket_side_structure", "follow_through",
                "footwork_observations.arrival_timing", "footwork_observations.recovery",
            ],
        }
    )
    plan = generate_coaching_plan(
        coach_id="liu-hui",
        player_profile=payload["player_profile"],  # type: ignore[arg-type]
        video_observation=observation,
        root=ROOT,
    )
    assert plan["diagnosis"]["confidence"] == "low"  # type: ignore[index]
    assert plan["lesson_focus"] is None
    assert not plan["_video_lessons"]
    assert plan["retake_guidance_zh"]


def test_topic_bound_media_accepts_only_the_audited_course(monkeypatch: pytest.MonkeyPatch) -> None:
    package = next(
        lesson
        for lesson in load_video_lessons("liu-hui", ROOT)
        if lesson.completeness == "complete_demonstration"
    )
    audited = replace(package, lesson_id="liu-hui-backcourt-footwork")
    unrelated = package
    monkeypatch.setattr(
        "badminton_coach_skill.teaching_plan.load_video_lessons",
        lambda _coach_id, _root: [unrelated, audited],
    )
    lessons = _select_topic_lessons(
        coach_id="liu-hui",
        root=ROOT,
        unit={
            "media_status": "teaching_ready",
            "reviewed_lesson_ids": ["liu-hui-backcourt-footwork"],
        },
        limit=2,
    )
    assert [lesson.lesson_id for lesson in lessons] == ["liu-hui-backcourt-footwork"]


def test_learner_focus_is_chinese_safe_and_bounded() -> None:
    payload = _payload("li_yuxuan_rear_clear_timing.json")
    plan = generate_coaching_plan(
        coach_id="li-yuxuan",
        player_profile=payload["player_profile"],  # type: ignore[arg-type]
        video_observation=payload["video_observation"],  # type: ignore[arg-type]
        root=ROOT,
    )
    focus = plan["lesson_focus"]
    assert focus["now"]["issue_id"] == "lyx-late-start"  # type: ignore[index]
    assert len(focus["next"]) <= 2  # type: ignore[index]
    drill_ids = [focus["now"]["drill"]["drill_id"], *(item["drill"]["drill_id"] for item in focus["next"] if item["drill"])]  # type: ignore[index]
    assert len(drill_ids) == len(set(drill_ids))
    learner_text = json.dumps(focus, ensure_ascii=False).lower()
    assert "movement begins after" not in learner_text
    assert "true internal rotation" not in learner_text
    assert "exact contact" not in learner_text


def test_cli_serializes_plan_without_private_runtime_fields(tmp_path: Path, capsys) -> None:
    payload = _payload("high_clear_late_arrival.json")
    request = tmp_path / "plan.json"
    request.write_text(
        json.dumps({"coach_id": "liu-hui", **payload}), encoding="utf-8"
    )
    main(["--input", str(request), "--project-root", str(ROOT)])
    result = json.loads(capsys.readouterr().out)
    assert result["report_type"] == "structured_coaching_plan"
    assert "_video_lessons" not in result


class RecordingDispatcher:
    def __init__(self) -> None:
        self.analysis_ids: list[str] = []

    def enqueue(self, analysis_id: str) -> None:
        self.analysis_ids.append(analysis_id)

    def close(self) -> None:
        return None


def test_api_and_worker_create_structured_plan_with_lesson(tmp_path: Path) -> None:
    payload = _payload("high_clear_late_arrival.json")
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'analysis.db'}",
        media_root=tmp_path / "student-media",
        coach_media_root=tmp_path / "coach-media",
        project_root=ROOT,
        dispatch_mode="local",
    )
    dispatcher = RecordingDispatcher()
    with TestClient(create_app(settings, dispatcher=dispatcher)) as client:
        response = client.post(
            "/api/coaching-plans",
            json={"coach_id": "auto", **payload},
        )
    assert response.status_code == 202
    job_payload = response.json()
    assert dispatcher.analysis_ids == [job_payload["analysis_id"]]

    database = Database(settings.database_url)
    completed = run_demonstration_job(
        database=database,
        media_store=LocalMediaStore(settings.media_root),
        project_root=ROOT,
        job_id=job_payload["analysis_id"],
        lesson_materializer=lambda lesson, _: lesson,
    )
    report = database.get_report(completed.id)
    assert completed.state == "completed"
    assert report is not None
    assert report["report_type"] == "structured_coaching_plan"
    assert report["requested_coach_id"] == "auto"
    assert report["lesson_focus"]
    assert not report["video_lessons"]


def test_api_rejects_action_unsupported_by_every_coach(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'analysis.db'}",
        media_root=tmp_path / "student-media",
        coach_media_root=tmp_path / "coach-media",
        project_root=ROOT,
        dispatch_mode="local",
    )
    with TestClient(create_app(settings, dispatcher=RecordingDispatcher())) as client:
        response = client.post(
            "/api/coaching-plans",
            json={
                "coach_id": "auto",
                "player_profile": {"level": "beginner"},
                "video_observation": {"action": "not-a-badminton-action"},
            },
        )
    assert response.status_code == 422
    assert response.json()["detail"] == "Unsupported action for all coaches"
