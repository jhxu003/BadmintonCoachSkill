from __future__ import annotations

import argparse
import copy
from collections import defaultdict
from datetime import date
from pathlib import Path
import statistics
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


TOPIC_WEIGHTS = {
    "internal_rotation": 10,
    "top_elbow": 10,
    "hip_rotation": 9,
    "contact_point": 9,
    "footwork": 9,
    "smash": 8,
    "high_clear": 8,
    "drop": 7,
    "drive": 7,
    "serve_receive": 7,
    "doubles": 6,
    "racket_preparation": 6,
    "wrist": 5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dense temporal Pose review windows for every critical visual source."
    )
    parser.add_argument(
        "--manifest", default="data/corpus/video-visual-pipeline-manifest.yaml"
    )
    parser.add_argument(
        "--output", default="data/corpus/video-temporal-review-manifest.yaml"
    )
    parser.add_argument("--max-sequences-per-source", type=int, default=2)
    parser.add_argument("--radius-seconds", type=float, default=1.5)
    parser.add_argument("--step-seconds", type=float, default=0.25)
    return parser.parse_args()


def dense_frames(
    anchor: float, radius: float, step: float, window_id: str, topics: list[str]
) -> list[dict[str, Any]]:
    count = int(round((2 * radius) / step)) + 1
    frames: list[dict[str, Any]] = []
    seen: set[float] = set()
    for index in range(count):
        relative = round(-radius + index * step, 3)
        timestamp = round(max(anchor + relative, 0.0), 3)
        if timestamp in seen:
            continue
        seen.add(timestamp)
        frames.append(
            {
                "timestamp_seconds": timestamp,
                "relative_seconds": relative,
                "phase_sample": "dense_temporal",
                "source_window_id": window_id,
                "topic_tags": topics,
            }
        )
    return frames


def window_score(topics: set[str], frame_count: int) -> int:
    return sum(TOPIC_WEIGHTS.get(topic, 1) for topic in topics) + min(frame_count, 3)


def build_sequences(
    job: dict[str, Any], max_sequences: int, radius: float, step: float
) -> list[dict[str, Any]]:
    if job.get("review_priority") != "critical":
        return []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for frame in job.get("planned_frames", []):
        window_id = str(frame.get("source_window_id") or "unassigned")
        grouped[window_id].append(frame)
    candidates: list[dict[str, Any]] = []
    for window_id, frames in grouped.items():
        timestamps = sorted(float(frame["timestamp_seconds"]) for frame in frames)
        topics = sorted(
            {
                str(topic)
                for frame in frames
                for topic in frame.get("topic_tags", [])
            }
        )
        anchor = round(float(statistics.median(timestamps)), 3)
        candidates.append(
            {
                "source_window_id": window_id,
                "anchor_timestamp_seconds": anchor,
                "topic_tags": topics,
                "selection_score": window_score(set(topics), len(frames)),
            }
        )
    candidates.sort(
        key=lambda item: (
            -item["selection_score"],
            item["anchor_timestamp_seconds"],
            item["source_window_id"],
        )
    )
    sequences: list[dict[str, Any]] = []
    for sequence_index, candidate in enumerate(candidates[: max(max_sequences, 0)], start=1):
        sequence_id = f"{job['job_id']}-temporal-{sequence_index:02d}"
        frames = dense_frames(
            candidate["anchor_timestamp_seconds"],
            radius,
            step,
            candidate["source_window_id"],
            candidate["topic_tags"],
        )
        sequences.append(
            {
                "sequence_id": sequence_id,
                **candidate,
                "radius_seconds": radius,
                "step_seconds": step,
                "planned_frames": frames,
                "evidence_limits": [
                    "Monocular Pose is a body-geometry proxy, not motion capture.",
                    "Racket face, shuttle contact, grip pressure, force, and true internal rotation remain unproven.",
                ],
            }
        )
    return sequences


def temporal_private_paths(job_id: str) -> dict[str, str]:
    root = Path("data/raw-private/video-corpus-temporal") / job_id
    return {
        "job_dir": str(root),
        "metadata_json": str(root / "metadata.json"),
        "video_file": str(root / "source_video"),
        "audio_file": str(root / "audio.m4a"),
        "keyframes_dir": str(root / "keyframes"),
        "asr_json": str(root / "asr.json"),
        "ocr_json": str(root / "ocr.json"),
        "vlm_json": str(root / "vlm.json"),
        "pose_json": str(root / "pose.json"),
        "run_log": str(root / "run.log"),
    }


def main() -> None:
    args = parse_args()
    source = load_yaml(ROOT / args.manifest)
    jobs: list[dict[str, Any]] = []
    planned_frames = 0
    planned_sequences = 0
    for source_job in source.get("jobs", []):
        sequences = build_sequences(
            source_job,
            max_sequences=args.max_sequences_per_source,
            radius=args.radius_seconds,
            step=args.step_seconds,
        )
        if not sequences:
            continue
        job = copy.deepcopy(source_job)
        job["source_private_paths"] = copy.deepcopy(source_job.get("private_paths", {}))
        job["private_paths"] = temporal_private_paths(job["job_id"])
        job["public_outputs"] = {
            "timestamp_evidence": str(
                Path("data/raw-private/video-corpus-temporal")
                / job["job_id"]
                / "public-evidence-staging.yaml"
            )
        }
        job["temporal_sequences"] = sequences
        job["planned_frames"] = [
            frame for sequence in sequences for frame in sequence["planned_frames"]
        ]
        planned_sequences += len(sequences)
        planned_frames += len(job["planned_frames"])
        jobs.append(job)
    output = {
        "manifest_id": f"liu_hui_temporal_review_{date.today().strftime('%Y%m%d')}",
        "created_at": date.today().isoformat(),
        "source_manifest": args.manifest,
        "summary": {
            "critical_sources": len(jobs),
            "planned_sequences": planned_sequences,
            "planned_dense_frames": planned_frames,
            "max_sequences_per_source": args.max_sequences_per_source,
            "radius_seconds": args.radius_seconds,
            "step_seconds": args.step_seconds,
        },
        "jobs": jobs,
    }
    write_yaml(ROOT / args.output, output)
    print(f"wrote {args.output}")
    print(f"critical_sources {len(jobs)}")
    print(f"planned_sequences {planned_sequences}")
    print(f"planned_dense_frames {planned_frames}")


if __name__ == "__main__":
    main()
