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
