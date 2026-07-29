from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inventory_reconciles_context_review_without_raw_model_output(tmp_path: Path) -> None:
    module = load_script("build_private_coach_media_inventory.py")
    corpus = tmp_path / ".runtime" / "full-corpus-processing-v1"
    for _coach, _pass_name, directory, _priority in module.BATCHES:
        root = corpus / directory
        root.mkdir(parents=True)
        (root / "manifest.json").write_text(
            json.dumps({"videos": []}), encoding="utf-8"
        )

    batch = corpus / "liu-hui-context-v1"
    video = {
        "video_index": 0,
        "job_id": "job-001",
        "source_id": "SOURCE-001",
        "title": "公开原始标题",
        "url": "https://example.invalid/video",
        "duration_seconds": 30.0,
    }
    (batch / "manifest.json").write_text(
        json.dumps({"videos": [video]}), encoding="utf-8"
    )
    video_root = batch / "videos" / "job-001"
    clip = video_root / "episodes" / "_shared" / "candidate-001" / "action.mp4"
    clip.parent.mkdir(parents=True)
    clip.write_bytes(b"private-video-placeholder")
    frames = []
    for index in range(1, 8):
        frame = clip.parent / "frames" / f"stage-{index:02d}.jpg"
        frame.parent.mkdir(parents=True, exist_ok=True)
        frame.write_bytes(f"frame-{index}".encode())
        frames.append(
            {
                "label_zh": f"阶段 {index}",
                "anchor_seconds": float(index),
                "teaching_point_zh": "只描述可见二维动作。",
                "image": str(frame.relative_to(video_root)),
            }
        )
    episode = {
        "episode_id": "high-clear-episode-01",
        "candidate_id": "candidate-001",
        "classification": "continuous_demonstration",
        "confidence": "high",
        "demonstration_purity": "high",
        "semantic_compatibility": "yes",
        "action_start_seconds": 1.0,
        "action_end_seconds": 7.0,
        "clip_start_seconds": 1.0,
        "clip_end_seconds": 8.0,
        "clip": str(clip.relative_to(video_root)),
        "frames": frames,
        "scope_limitations": [],
    }
    (video_root / "lesson-package.json").write_text(
        json.dumps(
            {
                "techniques": [
                    {
                        "action": "high_clear",
                        "label_zh": "后场高远球",
                        "family_id": "overhead",
                        "teaching_summary_zh": "完整连续示范。",
                        "episodes": [episode],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (video_root / "context-review.jsonl").write_text(
        json.dumps(
            {
                "action": "high_clear",
                "episode_id": "high-clear-episode-01",
                "decision": "approve",
                "demonstrator_role": "coach",
                "example_polarity": "correct",
                "context_review_status": "agent_reviewed",
                "context_start_seconds": 0.0,
                "context_end_seconds": 30.0,
                "context_evidence": ["single_complete_demonstration_visible"],
                "model": "MODEL_PATH_SHOULD_NOT_LEAK",
                "raw_output": "RAW_OUTPUT_SHOULD_NOT_LEAK",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary, rows = module.build_inventory(tmp_path)

    assert summary["source_count"] == 1
    assert summary["teaching_approved_canonical_asset_count"] == 1
    assert rows[0]["state"] == "ready_existing"
    assert rows[0]["existing_frame_count"] == 7
    decision = rows[0]["context_decisions"][0]
    assert decision["decision"] == "approve"
    assert "model" not in decision
    assert "raw_output" not in decision


def test_preview_embeds_relative_private_media_paths(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory"
    inventory.mkdir()
    (inventory / "summary.json").write_text(
        json.dumps(
            {
                "source_count": 2,
                "canonical_asset_count": 1,
                "existing_canonical_frame_count": 7,
                "teaching_approved_canonical_asset_count": 1,
                "source_state_counts": {"ready_existing": 1, "no_reliable_episode": 1},
                "sources": [
                    {
                        "coach": "liu_hui",
                        "source_id": "SOURCE-001",
                        "title": "可靠动作",
                        "url": "https://example.invalid/one",
                        "state": "ready_existing",
                    },
                    {
                        "coach": "li_yuxuan",
                        "source_id": "SOURCE-002",
                        "title": "没有可靠连续示范",
                        "url": "https://example.invalid/two",
                        "state": "no_reliable_episode",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    asset = {
        "asset_id": "asset-001",
        "duplicate_of": None,
        "coach": "liu_hui",
        "source_id": "SOURCE-001",
        "title": "可靠动作",
        "url": "https://example.invalid/one",
        "state": "ready_existing",
        "pass": "primary",
        "actions": ["high_clear"],
        "labels_zh": ["后场高远球"],
        "teaching_summaries_zh": ["完整连续示范。"],
        "classification": "continuous_demonstration",
        "confidence": "high",
        "action_start_seconds": 1.0,
        "action_end_seconds": 7.0,
        "clip_start_seconds": 1.0,
        "clip_end_seconds": 8.0,
        "clip": ".runtime/private/action.mp4",
        "frames": [f".runtime/private/stage-{index}.jpg" for index in range(1, 8)],
        "frame_labels_zh": [f"阶段 {index}" for index in range(1, 8)],
        "frame_anchor_seconds": [float(index) for index in range(1, 8)],
        "frame_teaching_points_zh": ["只描述可见二维动作。"] * 7,
        "scope_limitations": [],
    }
    (inventory / "assets.jsonl").write_text(
        json.dumps(asset, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (inventory / "validation.json").write_text(
        json.dumps({"warnings": []}), encoding="utf-8"
    )
    output = inventory / "index.html"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_private_coach_media_preview.py"),
            "--inventory",
            str(inventory),
            "--output",
            str(output),
        ],
        check=True,
    )

    page = output.read_text(encoding="utf-8")
    assert "教练动作素材，按原视频逐拍审阅" in page
    assert "../../../.runtime/private/action.mp4" in page
    assert "没有可靠连续示范" in page
