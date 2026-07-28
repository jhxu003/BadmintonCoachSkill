from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/liu-hui-badminton-coach/scripts/video_lesson_batch.py"
)


def load_batch_module():
    spec = importlib.util.spec_from_file_location("video_lesson_batch_for_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def prepare_args(manifest: Path, batch_root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        temporal_pose_only=False,
        temporal_pose_root=None,
        manifest=manifest,
        batch_root=batch_root,
        routing=Path("unused-routing.yaml"),
        source_cache=None,
    )


def test_prepare_snapshots_its_input_manifest(tmp_path, monkeypatch):
    module = load_batch_module()
    manifest = tmp_path / "source-manifest.json"
    payload = {"batch_version": 1, "videos": []}
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(module, "load_routes", lambda _: {})
    monkeypatch.setattr(module, "selected_rows", lambda *_: [])

    module.command_prepare(prepare_args(manifest, tmp_path / "batch"))

    assert json.loads((tmp_path / "batch/manifest.json").read_text(encoding="utf-8")) == payload


def test_prepare_rejects_a_conflicting_existing_batch_manifest(tmp_path, monkeypatch):
    module = load_batch_module()
    manifest = tmp_path / "source-manifest.json"
    manifest.write_text(json.dumps({"batch_version": 1, "videos": []}), encoding="utf-8")
    batch_root = tmp_path / "batch"
    batch_root.mkdir()
    (batch_root / "manifest.json").write_text(
        json.dumps({"batch_version": 1, "videos": [{"job_id": "different"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "load_routes", lambda _: {})
    monkeypatch.setattr(module, "selected_rows", lambda *_: [])

    with pytest.raises(RuntimeError, match="batch_manifest_conflicts_with_prepare_manifest"):
        module.command_prepare(prepare_args(manifest, batch_root))


def test_prepare_allows_exact_subset_of_existing_batch_manifest(tmp_path, monkeypatch):
    module = load_batch_module()
    full_video = {"job_id": "same", "source_id": "source", "title": "fixture"}
    manifest = tmp_path / "remaining-manifest.json"
    manifest.write_text(
        json.dumps({"batch_version": 1, "videos": [full_video]}), encoding="utf-8"
    )
    batch_root = tmp_path / "batch"
    batch_root.mkdir()
    (batch_root / "manifest.json").write_text(
        json.dumps(
            {
                "batch_version": 1,
                "videos": [
                    full_video,
                    {"job_id": "already-done", "source_id": "other", "title": "other"},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "load_routes", lambda _: {})
    monkeypatch.setattr(module, "selected_rows", lambda *_: [])

    module.command_prepare(prepare_args(manifest, batch_root))


def reviewed_episode() -> dict[str, object]:
    return {
        "action_start_seconds": 30.0,
        "action_end_seconds": 33.0,
    }


def reviewed_decision() -> dict[str, object]:
    return {
        "demonstrator_role": "coach",
        "example_polarity": "correct",
        "context_review_status": "agent_reviewed",
        "context_start_seconds": 0.0,
        "context_end_seconds": 63.0,
        "context_evidence": ["surrounding lesson identifies the coach's accepted demonstration"],
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("demonstrator_role", "learner", "demonstrator_role_must_be_coach"),
        ("example_polarity", "incorrect", "example_polarity_must_be_correct"),
        ("context_review_status", "model_candidate", "context_must_be_agent_reviewed"),
        ("context_evidence", [], "context_evidence_required"),
    ],
)
def test_publish_context_review_fails_closed(field, value, message):
    module = load_batch_module()
    decision = reviewed_decision()
    decision[field] = value

    with pytest.raises(RuntimeError, match=message):
        module.publish_context_review(decision, reviewed_episode())


def test_publish_context_review_requires_20_seconds_before_action():
    module = load_batch_module()
    decision = reviewed_decision()
    decision["context_start_seconds"] = 11.0

    with pytest.raises(RuntimeError, match="context_requires_20_seconds_each_side"):
        module.publish_context_review(decision, reviewed_episode())


def test_publish_context_review_requires_20_seconds_after_action():
    module = load_batch_module()
    decision = reviewed_decision()
    decision["context_end_seconds"] = 52.0

    with pytest.raises(RuntimeError, match="context_requires_20_seconds_each_side"):
        module.publish_context_review(decision, reviewed_episode())


def test_publish_context_review_rejects_negative_context_boundary():
    module = load_batch_module()
    decision = reviewed_decision()
    decision["context_start_seconds"] = -1.0

    with pytest.raises(RuntimeError, match="invalid_context_boundary"):
        module.publish_context_review(decision, reviewed_episode())


def test_publish_context_review_normalizes_approved_evidence():
    module = load_batch_module()
    decision = reviewed_decision()
    decision["context_evidence"] = ["  coach accepted this demonstration  "]

    result = module.publish_context_review(decision, reviewed_episode())

    assert result["demonstrator_role"] == "coach"
    assert result["example_polarity"] == "correct"
    assert result["context_evidence"] == ["coach accepted this demonstration"]


def context_payload() -> dict[str, object]:
    return {
        "classification": "coach_correct_demonstration",
        "demonstrator_role": "coach",
        "example_polarity": "correct",
        "action_subject_continuity": "yes",
        "context_evidence": [
            "source_lesson_presenter_visible",
            "same_presenter_executes_candidate",
            "single_complete_demonstration_visible",
            "normative_instruction_context_visible",
        ],
        "context_limitations": [],
    }


def reviewed_context_episode() -> dict[str, object]:
    return {
        "automatic_admission": True,
        "review_context_only": False,
        "semantic_assignment_status": "resolved",
    }


def test_context_review_accepts_only_complete_consistent_coach_evidence():
    module = load_batch_module()
    payload, error = module.parse_context_review(json.dumps(context_payload()))

    assert error is None
    assert payload == context_payload()
    assert module.context_admitted(reviewed_context_episode(), payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("demonstrator_role", "learner"),
        ("example_polarity", "incorrect"),
        ("action_subject_continuity", "unclear"),
        ("context_evidence", ["source_lesson_presenter_visible"]),
        ("context_limitations", ["surrounding_context_ambiguous"]),
    ],
)
def test_context_review_fails_closed_on_inconsistent_positive_output(field, value):
    module = load_batch_module()
    document = context_payload()
    document[field] = value

    payload, error = module.parse_context_review(json.dumps(document))

    assert error is None
    assert payload is not None
    assert payload["classification"] == "unclear"
    assert not module.context_admitted(reviewed_context_episode(), payload)


def test_context_review_does_not_promote_unresolved_or_partial_episode():
    module = load_batch_module()
    payload, error = module.parse_context_review(json.dumps(context_payload()))
    assert error is None

    partial = reviewed_context_episode()
    partial["automatic_admission"] = False
    assert not module.context_admitted(partial, payload)
    unresolved = reviewed_context_episode()
    unresolved["semantic_assignment_status"] = "agent_review_required"
    assert not module.context_admitted(unresolved, payload)


def test_summary_does_not_mark_prepare_only_video_complete(tmp_path):
    module = load_batch_module()
    manifest = tmp_path / "manifest.json"
    video = {
        "video_index": 0,
        "job_id": "prepare-only",
        "source_id": "source",
        "title": "fixture",
    }
    manifest.write_text(json.dumps({"videos": [video]}), encoding="utf-8")
    root = tmp_path / "batch" / "videos" / "prepare-only"
    root.mkdir(parents=True)
    (root / "status.json").write_text(
        json.dumps({"stage": "prepare", "state": "succeeded"}), encoding="utf-8"
    )
    (root / "candidates.json").write_text(
        json.dumps({"candidate_count": 3}), encoding="utf-8"
    )

    module.command_summarize(
        SimpleNamespace(
            manifest=manifest,
            batch_root=tmp_path / "batch",
            high_confidence_sample_rate=0.2,
        )
    )

    summary = json.loads((tmp_path / "batch" / "summary.json").read_text())
    assert summary["status"] == "incomplete"
    assert summary["succeeded_video_count"] == 0
    assert summary["candidate_count"] == 3


def test_context_review_recovers_legacy_action_admission_from_gate(tmp_path):
    module = load_batch_module()
    video = {
        "job_id": "legacy-video",
        "source_id": "legacy-source",
        "title": "legacy fixture",
        "duration_seconds": 100.0,
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"videos": [video]}), encoding="utf-8")
    root = tmp_path / "batch" / "videos" / "legacy-video"
    root.mkdir(parents=True)
    (root / "source.json").write_text(
        json.dumps({"path": str(tmp_path / "missing.mp4"), "duration_seconds": 100.0}),
        encoding="utf-8",
    )
    (root / "gate-results.jsonl").write_text(
        json.dumps({"candidate_id": "candidate-001", "admitted": True}) + "\n",
        encoding="utf-8",
    )
    legacy_episode = {
        "episode_id": "footwork-episode-01",
        "candidate_id": "candidate-001",
        "semantic_assignment_status": "resolved",
        "action_start_seconds": 30.0,
        "action_end_seconds": 33.0,
        "frames": [],
    }
    (root / "lesson-package.json").write_text(
        json.dumps({"techniques": [{"action": "footwork", "episodes": [legacy_episode]}]}),
        encoding="utf-8",
    )

    module.command_context_review(
        SimpleNamespace(
            manifest=manifest,
            batch_root=tmp_path / "batch",
            start=0,
            stop=None,
            shard=0,
            shards=1,
            job_id=[],
            frames_per_side=2,
            model=tmp_path / "unused-model",
            ffmpeg=tmp_path / "unused-ffmpeg",
            coach_name="fixture",
            max_new_tokens=1,
        )
    )

    review = json.loads((root / "context-review.jsonl").read_text().splitlines()[0])
    assert review["candidate_id"] == "candidate-001"
    assert review["parse_error"] == "insufficient_20_second_context"
