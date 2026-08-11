from __future__ import annotations

import json
from pathlib import Path
from subprocess import CalledProcessError

from fastapi.testclient import TestClient
import pytest

from badminton_coach_skill.video_evidence.agent import (
    ActionRoute,
    observation_value_whitelist,
    select_eligible_routes,
    validate_agent_observation,
)
from badminton_coach_skill.video_evidence.contracts import ActionPackageSegment, FrameRef
from badminton_coach_skill.video_evidence.ffmpeg import VideoMetadata
from badminton_coach_skill.video_evidence.phases import ACTION_PACKAGE_STAGE_OFFSETS_MS
from badminton_coach_skill.video_evidence.vlm_review import (
    QwenLocalActionRouter,
    QwenLocalSegmentObserver,
)
from badminton_coach_skill.video_evidence.worker import VideoEvidenceResult
from badminton_coach_skill.web.analysis_runner import AGENT_ANALYSIS_MODE, run_analysis_job
from badminton_coach_skill.web.app import create_app
from badminton_coach_skill.web.database import Database
from badminton_coach_skill.web.jobs import create_analysis_job, expire_jobs
from badminton_coach_skill.web.media_store import LocalMediaStore
from badminton_coach_skill.web.models import MediaAsset
from badminton_coach_skill.web.settings import Settings


ROOT = Path(__file__).resolve().parents[1]


class RecordingDispatcher:
    def __init__(self) -> None:
        self.analysis_ids: list[str] = []

    def enqueue(self, analysis_id: str) -> None:
        self.analysis_ids.append(analysis_id)

    def close(self) -> None:
        return None


def _focus_plan(*_args: object, **_kwargs: object) -> dict[str, object]:
    return {
        "coach_id": "liu-hui",
        "coach_name": "刘辉",
        "official_status": "non-official research synthesis",
        "notice": "仅依据可见的连续动作证据。",
        "lesson_focus": {
            "now": {
                "issue_id": "verified-visible-timing",
                "title_zh": "先把启动接到动作链里",
                "visible_evidence_zh": ["连续阶段已通过可见性检查"],
                "correction_zh": "先完成完整移动与回位，再提高速度。",
                "drill": {"drill_id": "safe-drill", "title_zh": "连续步法练习", "dosage_zh": "每组 6 次"},
                "retest_zh": "复拍时完整保留准备到回位。",
                "topic_unit": {
                    "topic_id": "safe-topic",
                    "topic_name_zh": "完整动作链",
                    "learning_goal_zh": "保持连续过程。",
                    "knowledge_status": "reviewed",
                    "media_status": "reviewed_media_unavailable",
                    "media_notice_zh": "没有同主题连续示范时不替代。",
                },
            },
            "next": [],
        },
        "selected_topic_unit": {"topic_id": "safe-topic"},
        "coach_lenses": [],
        "video_lesson_status": "no_reliable_video_lesson_package",
        "limitations": ["structured_observation_required_before_coach_diagnosis"],
        "_video_lessons": (),
        # This must never be copied to an Agent report.
        "raw_model_output": "do_not_publish",
        "diagnosis": {"issues": [{"issue": "do_not_publish"}]},
    }


class FakeAgentPipeline:
    def __init__(self, routes: tuple[ActionRoute, ...], *, complete: bool = True) -> None:
        self.routes = routes
        self.complete = complete
        self.analyzed: list[str] = []

    def route_agent(self, _video_path: Path, _output_dir: Path) -> tuple[ActionRoute, ...]:
        return self.routes

    def analyze_agent_route(
        self,
        _video_path: Path,
        output_dir: Path,
        route: ActionRoute,
        _allowed_values: dict[str, tuple[str, ...]],
    ) -> tuple[VideoEvidenceResult, dict[str, object]]:
        self.analyzed.append(route.unit_id)
        root = output_dir / "agent-units" / route.unit_id
        phases = tuple(ACTION_PACKAGE_STAGE_OFFSETS_MS)
        if not self.complete:
            phases = phases[:-1]
        frames: list[FrameRef] = []
        segments: list[ActionPackageSegment] = []
        keyframes: list[dict[str, object]] = []
        for index, (phase, offset_ms) in enumerate(phases, start=1):
            timestamp_ms = max(10, 2500 + offset_ms)
            frame_key = f"agent-units/{route.unit_id}/frames/{phase}.jpg"
            segment_key = f"agent-units/{route.unit_id}/segments/{phase}.mp4"
            frame_path = output_dir / frame_key
            segment_path = output_dir / segment_key
            frame_path.parent.mkdir(parents=True, exist_ok=True)
            segment_path.parent.mkdir(parents=True, exist_ok=True)
            frame_path.write_bytes(f"frame-{route.unit_id}-{phase}".encode())
            segment_path.write_bytes(f"segment-{route.unit_id}-{phase}".encode())
            frame_id = f"{route.unit_id}-frame-{index}"
            frames.append(
                FrameRef(
                    frame_id=frame_id,
                    owner="student",
                    phase=phase,
                    timestamp_ms=timestamp_ms,
                    media_key=frame_key,
                    confidence="high",
                    visible_facts=("visible_2d_motion",),
                    limitations=("single_view_2d_pose_proxy",),
                )
            )
            segments.append(
                ActionPackageSegment(
                    segment_id=f"{route.unit_id}-segment-{index}",
                    phase=phase,
                    anchor_ms=timestamp_ms,
                    start_ms=max(0, timestamp_ms - 100),
                    end_ms=timestamp_ms + 100,
                    confidence="high",
                    caption=f"{phase} context",
                    limitations=("action_package_context_proxy",),
                    media_key=segment_key,
                )
            )
            keyframes.append({"frame_id": frame_id, "phase": phase})
        return (
            VideoEvidenceResult(
                observation={
                    "action": route.action,
                    "camera_view": "side",
                    "keyframes": keyframes,
                    "missing_observations": [],
                },
                frames=tuple(frames),
                candidates=(),
                action_package=tuple(segments),
            ),
            {"confidence": "high", "untrusted_free_text": "must_not_escape"},
        )


def _agent_job(tmp_path: Path) -> tuple[Database, LocalMediaStore, object]:
    database = Database(f"sqlite:///{tmp_path / 'analysis.db'}")
    database.create_all()
    media_store = LocalMediaStore(tmp_path / "student-media")
    job = create_analysis_job(
        database,
        "auto",
        None,
        {"analysis_mode": AGENT_ANALYSIS_MODE, "level": "beginner", "training_goal": "technique_diagnosis"},
    )
    upload_key = media_store.write_bytes(job.id, "upload.mp4", b"private upload placeholder")
    database.add_media_asset(
        MediaAsset(
            id="upload-asset",
            job_id=job.id,
            media_key=upload_key,
            kind="upload",
            expires_at=job.expires_at,
        )
    )
    database.set_state(job.id, "queued", 2, "Queued for test.")
    return database, media_store, job


def _stub_coach_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "badminton_coach_skill.web.analysis_runner.available_coaches",
        lambda _root: ["liu-hui"],
    )
    monkeypatch.setattr(
        "badminton_coach_skill.web.analysis_runner.available_coach_actions",
        lambda _coach_id, _root: ["high_clear", "smash", "drive"],
    )
    monkeypatch.setattr(
        "badminton_coach_skill.web.analysis_runner.load_coach_knowledge",
        lambda _coach_id, _root: {"rules": []},
    )


def test_local_router_samples_interior_time_buckets_and_skips_one_bad_seek(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slightly long container duration must not fail an otherwise valid upload."""
    samples: list[int] = []
    monkeypatch.setattr(
        "badminton_coach_skill.video_evidence.ffmpeg.probe_video",
        lambda _path: VideoMetadata(duration_ms=30_000, width=1280, height=720, fps=30.0),
    )

    def extract(_video: Path, timestamp_ms: int, _output: Path) -> None:
        samples.append(timestamp_ms)
        if timestamp_ms == 27_000:
            raise CalledProcessError(234, ["ffmpeg"])

    monkeypatch.setattr("badminton_coach_skill.video_evidence.ffmpeg.extract_frame", extract)
    router = QwenLocalActionRouter("not-loaded-in-this-test", maximum_samples=5)
    seen_paths: list[Path] = []

    def generated(image_paths: tuple[Path, ...], _prompt: str) -> dict[str, object]:
        seen_paths.extend(image_paths)
        return {
            # The requested schema omits ``decision``.  Qwen may still wrap
            # its one valid candidate in ``units``; it must not be discarded
            # merely because that optional internal field is absent.
            "units": [{
                "action": "smash",
                # The visible sheet captions include timestamps.  A valid
                # model can copy those exact labels into the sample fields;
                # they are normalized only through this known sample map.
                "start_sample": 9_000,
                "end_sample": 21_000,
                "confidence": 0.95,
            }],
        }

    monkeypatch.setattr(router._model, "generate_json", generated)
    routes = router.route(tmp_path / "learner.mp4", tmp_path / "work")

    assert samples == [3_000, 9_000, 15_000, 21_000, 27_000]
    assert 29_999 not in samples
    assert len(seen_paths) == 4
    assert [(route.action, route.start_ms, route.end_ms) for route in routes] == [
        ("smash", 0, 24_000)
    ]


def test_local_router_scalar_timestamps_keep_preparation_and_recovery_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "badminton_coach_skill.video_evidence.ffmpeg.probe_video",
        lambda _path: VideoMetadata(duration_ms=12_000, width=1280, height=720, fps=30.0),
    )
    monkeypatch.setattr(
        "badminton_coach_skill.video_evidence.ffmpeg.extract_frame",
        lambda _video, _timestamp, output: output.parent.mkdir(parents=True, exist_ok=True) or output.write_bytes(b"frame"),
    )
    router = QwenLocalActionRouter("not-loaded-in-this-test", maximum_samples=4)
    monkeypatch.setattr(
        router._model,
        "generate_json",
        lambda _images, _prompt: {
            "action": "smash",
            "start_ms": 3_000,
            "end_ms": 7_000,
            "confidence": 0.95,
        },
    )
    routes = router.route(tmp_path / "learner.mp4", tmp_path / "work")
    assert [(route.action, route.start_ms, route.end_ms) for route in routes] == [
        ("smash", 500, 8_200)
    ]


def test_local_observer_projects_flat_safe_vocabulary_only(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    observer = QwenLocalSegmentObserver("not-loaded-in-this-test")
    monkeypatch.setattr(
        observer._model,
        "generate_json",
        lambda _images, _prompt: {
            "confidence": "high",
            "camera_view": "side",
            "observations": {
                "elbow_height_before_hit": "below_shoulder",
                "footwork_observations.arrival": "late",
                "phase_observations.racket_face": "open",
                "untrusted_free_text": "ignore this",
            },
        },
    )
    result = observer.observe(
        action="smash",
        image_paths=(Path("private-frame.jpg"),),
        base_observation={},
        allowed_values={
            "elbow_height_before_hit": ("below_shoulder",),
            "footwork_observations.arrival": ("late",),
        },
    )
    assert result == {
        "confidence": "high",
        "camera_view": "side",
        "elbow_height_before_hit": "below_shoulder",
    }


def test_local_observer_checks_a_small_safe_proxy_sequence_until_one_is_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observer = QwenLocalSegmentObserver("not-loaded-in-this-test")
    calls: list[str] = []

    def generated(_images: tuple[Path, ...], prompt: str) -> dict[str, object]:
        calls.append(prompt)
        if "phase_observations.arm_path" in prompt:
            return {"confidence": "low", "camera_view": "side", "observations": {}}
        return {
            "confidence": "high",
            "camera_view": "side",
            "observations": {"elbow_height_before_hit": "below_shoulder"},
        }

    monkeypatch.setattr(observer._model, "generate_json", generated)
    result = observer.observe(
        action="smash",
        image_paths=(Path("private-frame.jpg"),),
        base_observation={},
        allowed_values={
            "phase_observations.arm_path": ("big_arm_pull",),
            "elbow_height_before_hit": ("below_shoulder",),
        },
    )

    assert len(calls) == 2
    assert result == {
        "confidence": "high",
        "camera_view": "side",
        "elbow_height_before_hit": "below_shoulder",
    }


def test_agent_validation_whitelists_only_safe_rule_fields() -> None:
    knowledge_sets = [{
        "rules": [{
            "applicable_actions": ["smash"],
            "observable_evidence": [
                {"path": "footwork_observations.first_step", "equals": "late"},
                {"path": "contact_point", "equals": "low"},
                {"path": "phase_observations.racket_face", "equals": "open"},
                {"path": "phase_observations.shot_intent", "equals": "passive"},
            ],
            "required_observations": ["footwork_observations.first_step", "contact_point"],
        }]
    }]
    allowed = observation_value_whitelist(knowledge_sets, "smash")
    assert allowed == {"footwork_observations.first_step": ("late",)}
    validation = validate_agent_observation(
        action="smash",
        raw_observation={
            "confidence": "high",
            "contact_point": "low",
            "phase_observations": {"racket_face": "open", "shot_intent": "passive"},
            "footwork_observations": {"first_step": "late"},
            "untrusted_free_text": "diagnose everything",
        },
        base_observation={"keyframes": [{"frame_id": "one"}]},
        knowledge_sets=knowledge_sets,
    )
    assert validation.accepted
    assert validation.observation["contact_point"] == "unknown"
    assert validation.observation["footwork_observations"] == {"first_step": "late"}
    assert "untrusted_free_text" not in validation.observation


def test_route_gate_rejects_low_confidence_and_overlapping_windows() -> None:
    routes = (
        ActionRoute("low", "smash", 0, 2600, 0.79),
        ActionRoute("first", "smash", 0, 2600, 0.95),
        ActionRoute("overlap", "drop", 1000, 3600, 0.99),
        ActionRoute("second", "drive", 4000, 6400, 0.91),
    )
    # The overlapping pair is resolved by the stronger route rather than by
    # arbitrary input order; the low-confidence candidate is never eligible.
    assert [route.unit_id for route in select_eligible_routes(routes, minimum_confidence=0.8, maximum_units=5)] == ["overlap", "second"]


def test_agent_runner_isolates_two_units_and_never_publishes_raw_model_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, media_store, job = _agent_job(tmp_path)
    pipeline = FakeAgentPipeline(
        (
            ActionRoute("unit-a", "high_clear", 0, 6400, 0.96),
            ActionRoute("unit-b", "smash", 8000, 14400, 0.93),
        )
    )
    _stub_coach_registry(monkeypatch)
    monkeypatch.setattr("badminton_coach_skill.web.analysis_runner.generate_coaching_plan", _focus_plan)
    completed = run_analysis_job(
        database=database,
        media_store=media_store,
        project_root=ROOT,
        job_id=job.id,
        pipeline=pipeline,  # type: ignore[arg-type]
    )
    report = database.get_report(job.id)
    assert completed.state == "completed"
    assert report and report["report_type"] == "agent_video_coaching_report"
    assert [unit["status"] for unit in report["action_units"]] == ["teaching_ready", "teaching_ready"]
    assert pipeline.analyzed == ["unit-a", "unit-b"]
    first, second = report["action_units"]
    assert {item["frame_id"] for item in first["student_frames"]}.isdisjoint(
        {item["frame_id"] for item in second["student_frames"]}
    )
    assert {item["segment_id"] for item in first["action_package"]}.isdisjoint(
        {item["segment_id"] for item in second["action_package"]}
    )
    public_json = json.dumps(report, ensure_ascii=False)
    assert "raw_model_output" not in public_json
    assert "untrusted_free_text" not in public_json
    assert "private upload placeholder" not in public_json
    assert "/public/home/" not in public_json
    assert len(database.list_media_assets(job.id, kind="student_frame")) == 14
    assert len(database.list_media_assets(job.id, kind="student_segment")) == 14


def test_incomplete_or_low_confidence_agent_units_never_call_coaching_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, media_store, job = _agent_job(tmp_path)
    called = False

    def unexpected_plan(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal called
        called = True
        return _focus_plan()

    pipeline = FakeAgentPipeline(
        (
            ActionRoute("low", "smash", 0, 4000, 0.3),
            ActionRoute("short-evidence", "smash", 5000, 9000, 0.98),
        ),
        complete=False,
    )
    _stub_coach_registry(monkeypatch)
    monkeypatch.setattr("badminton_coach_skill.web.analysis_runner.generate_coaching_plan", unexpected_plan)
    run_analysis_job(
        database=database,
        media_store=media_store,
        project_root=ROOT,
        job_id=job.id,
        pipeline=pipeline,  # type: ignore[arg-type]
    )
    report = database.get_report(job.id)
    assert report is not None
    assert called is False
    assert {unit["status"] for unit in report["action_units"]} == {"needs_retake"}
    assert all(unit["coaching_plan"] is None for unit in report["action_units"])
    assert not database.list_media_assets(job.id, kind="student_frame")


def test_invalid_segment_observation_fails_closed_to_retake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, media_store, job = _agent_job(tmp_path)
    pipeline = FakeAgentPipeline((ActionRoute("invalid-json", "smash", 0, 5000, 0.98),))
    original = pipeline.analyze_agent_route

    def invalid_observation(*args: object, **kwargs: object) -> tuple[VideoEvidenceResult, object]:
        evidence, _ = original(*args, **kwargs)  # type: ignore[arg-type]
        return evidence, None

    pipeline.analyze_agent_route = invalid_observation  # type: ignore[method-assign]
    _stub_coach_registry(monkeypatch)
    monkeypatch.setattr(
        "badminton_coach_skill.web.analysis_runner.generate_coaching_plan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not diagnose")),
    )
    completed = run_analysis_job(
        database=database,
        media_store=media_store,
        project_root=ROOT,
        job_id=job.id,
        pipeline=pipeline,  # type: ignore[arg-type]
    )
    report = database.get_report(job.id)
    assert completed.state == "completed"
    assert report is not None
    unit = report["action_units"][0]
    assert unit["status"] == "needs_retake"
    assert unit["observation_confidence"] == "low"
    assert unit["coaching_plan"] is None


def test_agent_upload_accepts_auto_mode_and_manual_upload_contract_remains(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'analysis.db'}",
        media_root=tmp_path / "student-media",
        coach_media_root=tmp_path / "coach-media",
        project_root=ROOT,
        dispatch_mode="local",
    )
    dispatcher = RecordingDispatcher()
    with TestClient(create_app(settings, dispatcher=dispatcher)) as client:
        agent = client.post(
            "/api/analyses",
            files={"video": ("learner.mp4", b"video", "video/mp4")},
            data={"analysis_mode": AGENT_ANALYSIS_MODE, "coach_id": "auto", "player_profile": '{"level":"beginner"}'},
        )
        manual = client.post(
            "/api/analyses",
            files={"video": ("learner.mp4", b"video", "video/mp4")},
            data={"coach_id": "liu-hui", "action_hint": "high_clear", "player_profile": "{}"},
        )
        rejected = client.post(
            "/api/analyses",
            files={"video": ("learner.mp4", b"video", "video/mp4")},
            data={"analysis_mode": AGENT_ANALYSIS_MODE, "coach_id": "liu-hui"},
        )
    assert agent.status_code == 202
    assert manual.status_code == 202
    assert rejected.status_code == 422
    assert len(dispatcher.analysis_ids) == 2
    database = Database(settings.database_url)
    assert database.get_player_profile(agent.json()["analysis_id"])["analysis_mode"] == AGENT_ANALYSIS_MODE
    assert database.get_job(manual.json()["analysis_id"]).coach_id == "liu-hui"


def test_agent_report_media_is_private_then_expires_to_410_and_deletes_job_dir(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'analysis.db'}",
        media_root=tmp_path / "student-media",
        coach_media_root=tmp_path / "coach-media",
        project_root=ROOT,
        dispatch_mode="local",
    )
    with TestClient(create_app(settings, dispatcher=RecordingDispatcher())) as client:
        created = client.post(
            "/api/analyses",
            files={"video": ("learner.mp4", b"video", "video/mp4")},
            data={"analysis_mode": AGENT_ANALYSIS_MODE, "coach_id": "auto"},
        ).json()
        analysis_id = created["analysis_id"]
        token = created["access_token"]
        database = Database(settings.database_url)
        media_store = LocalMediaStore(settings.media_root)
        frame_key = media_store.write_bytes(analysis_id, "agent-frame.jpg", b"frame")
        job = database.get_job(analysis_id)
        database.add_media_asset(
            MediaAsset(
                id="agent-frame",
                job_id=analysis_id,
                media_key=frame_key,
                kind="student_frame",
                expires_at=job.expires_at,
            )
        )
        database.save_report(analysis_id, {"report_type": "agent_video_coaching_report", "action_units": []})
        database.set_state(analysis_id, "completed", 100, "Ready for test.")
        headers = {"X-Analysis-Token": token}
        assert client.get(f"/api/analyses/{analysis_id}/frames/agent-frame", headers=headers).headers["cache-control"] == "private, no-store"
        assert client.get(f"/api/analyses/{analysis_id}/report", headers=headers).status_code == 200
        assert expire_jobs(database, media_store, now=job.expires_at) == 1
        assert not media_store.job_dir(analysis_id).exists()
        assert client.get(f"/api/analyses/{analysis_id}/report", headers=headers).status_code == 410
        assert client.get(f"/api/analyses/{analysis_id}/frames/agent-frame", headers=headers).status_code == 410
