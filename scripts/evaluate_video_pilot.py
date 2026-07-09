from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate whether pilot video evidence is ready for skill promotion."
    )
    parser.add_argument(
        "--manifest",
        default="data/corpus/video-pilot-manifest.yaml",
    )
    parser.add_argument(
        "--output",
        default="data/corpus/video-pilot-evaluation.yaml",
    )
    parser.add_argument(
        "--teaching-windows",
        default="data/corpus/video-asr-teaching-windows.yaml",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_yaml(ROOT / args.manifest)
    jobs = manifest.get("jobs", [])
    evidence_items = []
    topic_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    review_counts: Counter[str] = Counter()
    stage_status_counts: dict[str, Counter[str]] = {}

    for job in jobs:
        evidence_path = ROOT / job["public_outputs"]["timestamp_evidence"]
        if not evidence_path.exists():
            continue
        evidence = load_yaml(evidence_path)
        evidence_items.append(evidence)
        for stage, status_record in evidence.get("stage_status", {}).items():
            if stage not in stage_status_counts:
                stage_status_counts[stage] = Counter()
            stage_status_counts[stage].update([status_record.get("status", "missing")])
        for segment in evidence.get("segments", []):
            topic_counts.update(segment.get("topic_tags", []))
            level_counts.update([segment.get("evidence_level", "missing")])
            review_counts.update([segment.get("review_status", "missing")])

    promoted_ready = level_counts.get("content_model_candidate", 0)
    title_only = level_counts.get("needs_content_model_review", 0)
    teaching_windows_path = ROOT / args.teaching_windows
    teaching_windows = []
    model_notes = {}
    if teaching_windows_path.exists():
        teaching_window_data = load_yaml(teaching_windows_path)
        teaching_windows = teaching_window_data.get("windows", [])
        model_notes = teaching_window_data.get("review_run", {}).get("model_notes", {})
    recommendation = (
        "proceed_to_human_review"
        if promoted_ready >= 10
        else "do_not_promote_adjust_or_run_models"
    )
    report = {
        "manifest_id": manifest.get("manifest_id"),
        "jobs_total": len(jobs),
        "evidence_files_found": len(evidence_items),
        "topic_counts": dict(topic_counts),
        "evidence_level_counts": dict(level_counts),
        "review_status_counts": dict(review_counts),
        "stage_status_counts": {
            stage: dict(counter) for stage, counter in sorted(stage_status_counts.items())
        },
        "promotion_ready_segments": promoted_ready,
        "title_or_metadata_only_segments": title_only,
        "teaching_window_candidates": len(teaching_windows),
        "teaching_window_review_status_counts": dict(
            Counter(item.get("review_status", "missing") for item in teaching_windows)
        ),
        "model_notes": model_notes,
        "recommendation": recommendation,
        "acceptance_policy": {
            "minimum_content_model_candidate_segments_for_pilot": 10,
            "minimum_topics_expected": [
                "smash",
                "high_clear",
                "rear_footwork",
                "top_elbow",
                "hip_rotation",
                "internal_rotation",
                "power_framework",
                "student_fit",
            ],
            "rule": (
                "Do not promote needs_content_model_review evidence into skill rules. "
                "Run ASR/OCR/VLM/Pose or do human timestamp review first."
            ),
        },
    }
    write_yaml(ROOT / args.output, report)
    print(f"wrote {args.output}")
    print(f"recommendation {recommendation}")
    print(f"evidence_files_found {len(evidence_items)}")
    print(f"promotion_ready_segments {promoted_ready}")


if __name__ == "__main__":
    main()
