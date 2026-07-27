from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from badminton_coach_skill.teaching_plan import (
    generate_coaching_plan,
    main,
    serialize_coaching_plan,
)
from badminton_coach_skill.web.app import create_app
from badminton_coach_skill.web.database import Database
from badminton_coach_skill.web.demonstration_runner import run_demonstration_job
from badminton_coach_skill.web.jobs import create_demonstration_job
from badminton_coach_skill.web.media_store import LocalMediaStore
from badminton_coach_skill.web.settings import Settings


ROOT = Path(__file__).resolve().parents[1]


def _payload(name: str) -> dict[str, object]:
    return json.loads((ROOT / "examples" / "observations" / name).read_text(encoding="utf-8"))


def test_liu_hui_plan_orders_diagnosis_and_verified_lesson() -> None:
    payload = _payload("high_clear_late_arrival.json")
    plan = generate_coaching_plan(
        coach_id="liu-hui",
        player_profile=payload["player_profile"],  # type: ignore[arg-type]
        video_observation=payload["video_observation"],  # type: ignore[arg-type]
        root=ROOT,
    )
    assert plan["report_type"] == "structured_coaching_plan"
    assert plan["teaching_sequence"]
    assert plan["video_lesson_status"] == "available"
    serialized = serialize_coaching_plan(plan)
    assert "_video_lessons" not in serialized
    assert serialized["video_lessons"]
    assert serialized["video_lessons"][0]["completeness"] == "complete_demonstration"  # type: ignore[index]


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
    assert not plan["_video_lessons"]


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
            json={"coach_id": "liu-hui", **payload},
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
    assert report["video_lesson_status"] == "available"
    assert report["video_lessons"]
