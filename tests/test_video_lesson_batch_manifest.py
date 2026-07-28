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
