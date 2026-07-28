from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/liu-hui-badminton-coach/scripts/export_public_lesson.py"
)


def load_export_module():
    spec = importlib.util.spec_from_file_location("export_public_lesson_for_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def valid_review() -> dict[str, object]:
    return {
        "source_id": "PUBLIC_SOURCE",
        "source_url": "https://example.invalid/video",
        "action_start_seconds": 30.0,
        "action_end_seconds": 33.0,
        "context_start_seconds": 0.0,
        "context_end_seconds": 63.0,
        "demonstrator_role": "coach",
        "example_polarity": "correct",
        "context_review_status": "agent_reviewed",
        "review_basis": ["surrounding lesson identifies the coach's accepted demonstration"],
    }


def write_review(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_public_export_rejects_missing_review_manifest(tmp_path: Path) -> None:
    module = load_export_module()
    with pytest.raises(SystemExit, match="review manifest does not exist"):
        module.load_review_manifest(tmp_path / "missing.json", 30.0, 33.0)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("demonstrator_role", "learner", "demonstrator_role=coach"),
        ("example_polarity", "incorrect", "example_polarity=correct"),
        ("context_review_status", "model_candidate", "context_review_status=agent_reviewed"),
    ],
)
def test_public_export_rejects_unpublishable_role_or_polarity(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    module = load_export_module()
    payload = valid_review()
    payload[field] = value
    manifest = write_review(tmp_path / "review.json", payload)

    with pytest.raises(SystemExit, match=message):
        module.load_review_manifest(manifest, 30.0, 33.0)


def test_public_export_rejects_short_context_before_action(tmp_path: Path) -> None:
    module = load_export_module()
    payload = valid_review()
    payload["context_start_seconds"] = 11.0
    manifest = write_review(tmp_path / "review.json", payload)

    with pytest.raises(SystemExit, match="at least 20 seconds"):
        module.load_review_manifest(manifest, 30.0, 33.0)


def test_public_export_rejects_short_context_after_action(tmp_path: Path) -> None:
    module = load_export_module()
    payload = valid_review()
    payload["context_end_seconds"] = 52.0
    manifest = write_review(tmp_path / "review.json", payload)

    with pytest.raises(SystemExit, match="at least 20 seconds"):
        module.load_review_manifest(manifest, 30.0, 33.0)


def test_public_export_rejects_negative_context_boundary(tmp_path: Path) -> None:
    module = load_export_module()
    payload = valid_review()
    payload["context_start_seconds"] = -1.0
    manifest = write_review(tmp_path / "review.json", payload)

    with pytest.raises(SystemExit, match="invalid action/context boundaries"):
        module.load_review_manifest(manifest, 30.0, 33.0)


def test_public_export_writes_only_public_safe_review_fields(tmp_path: Path) -> None:
    module = load_export_module()
    payload = valid_review()
    payload["private_note"] = "must not be copied"
    manifest = write_review(tmp_path / "review.json", payload)

    result = module.load_review_manifest(manifest, 30.0, 33.0)

    assert result["demonstrator_role"] == "coach"
    assert result["example_polarity"] == "correct"
    assert "private_note" not in result


def test_all_public_lesson_assets_have_publishable_review_context() -> None:
    module = load_export_module()
    repo = Path(__file__).resolve().parents[1]
    roots = sorted((repo / "web/public/pages-demo").glob("liu-hui-*"))

    assert len(roots) == 7
    for lesson_root in roots:
        review_path = lesson_root / "review.json"
        payload = json.loads(review_path.read_text(encoding="utf-8"))
        reviewed = module.load_review_manifest(
            review_path,
            float(payload["action_start_seconds"]),
            float(payload["action_end_seconds"]),
        )

        assert reviewed["demonstrator_role"] == "coach"
        assert reviewed["example_polarity"] == "correct"
        assert (lesson_root / "action.mp4").is_file()
        assert len(list((lesson_root / "keyframes").glob("*.jpg"))) == 7
