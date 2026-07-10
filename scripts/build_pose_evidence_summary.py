from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import statistics
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create public-safe aggregate summaries from private pose artifacts."
    )
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument(
        "--output",
        default="data/corpus/video-pose-evidence-summary.yaml",
    )
    return parser.parse_args()


def load_jobs(paths: list[str]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_path in paths:
        manifest = load_yaml(ROOT / raw_path)
        for job in manifest.get("jobs", []):
            if job["job_id"] in seen:
                continue
            seen.add(job["job_id"])
            jobs.append(job)
    return jobs


def load_pose(job: dict[str, Any]) -> dict[str, Any] | None:
    path = ROOT / job["private_paths"]["pose_json"]
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if data.get("status") == "ok" else None


def summarize(job: dict[str, Any], pose: dict[str, Any]) -> dict[str, Any]:
    frames = pose.get("frames", [])
    people = [person for frame in frames for person in frame.get("people", [])]
    confidences = [
        float(person["mean_confidence"])
        for person in people
        if person.get("mean_confidence") is not None
    ]
    keypoint_counts = [
        int(person["keypoint_count"])
        for person in people
        if person.get("keypoint_count") is not None
    ]
    return {
        "job_id": job["job_id"],
        "source_id": job["source_id"],
        "title": job["title"],
        "platform": job["platform"],
        "topic_tags": job.get("priority_topics", []),
        "model": Path(str(pose.get("model") or "unknown")).name,
        "reviewed_frame_count": len(frames),
        "timestamps_seconds": [
            int(round(float(frame.get("timestamp_seconds") or 0))) for frame in frames
        ],
        "frames_with_people": sum(1 for frame in frames if frame.get("person_count", 0) > 0),
        "person_detections": sum(int(frame.get("person_count") or 0) for frame in frames),
        "mean_detected_keypoints": (
            round(statistics.fmean(keypoint_counts), 2) if keypoint_counts else None
        ),
        "mean_keypoint_confidence": (
            round(statistics.fmean(confidences), 4) if confidences else None
        ),
        "evidence_level": "pose_model_candidate_reviewed_public_safe",
        "review_status": "agent_pose_summary_reviewed",
        "human_review_status": "not_human_reviewed",
        "summary": (
            "Private pose output was reduced to timestamped detection coverage and aggregate "
            "confidence. No keypoint coordinates or frame images are included."
        ),
        "allowed_use": (
            "Use to determine whether a timestamp has enough visible body-keypoint coverage for later human review."
        ),
        "blocked_use": (
            "Do not infer racket orientation, contact point, true shoulder internal rotation, or coaching intent from these aggregates."
        ),
    }


def main() -> None:
    args = parse_args()
    jobs = load_jobs(args.manifest)
    sources: list[dict[str, Any]] = []
    topic_counts: Counter[str] = Counter()
    reviewed_frames = 0
    frames_with_people = 0
    for job in jobs:
        pose = load_pose(job)
        if not pose:
            continue
        item = summarize(job, pose)
        sources.append(item)
        reviewed_frames += item["reviewed_frame_count"]
        frames_with_people += item["frames_with_people"]
        topic_counts.update(item["topic_tags"])

    output = {
        "pose_summary_run": {
            "run_id": f"pose_evidence_summary_{date.today().strftime('%Y%m%d')}",
            "created_at": date.today().isoformat(),
            "scope": [
                "Private pose outputs for indexed non-YouTube Bilibili sources.",
                "Only aggregate detection coverage, confidence, and timestamps are public.",
                "Keypoint coordinates, frames, video, and raw model output remain private.",
            ],
            "summary": {
                "manifest_jobs_scanned": len(jobs),
                "sources_with_ok_pose": len(sources),
                "reviewed_keyframes": reviewed_frames,
                "keyframes_with_people": frames_with_people,
                "topic_source_counts": dict(topic_counts.most_common()),
            },
            "evidence_contract": {
                "evidence_level": "pose_model_candidate_reviewed_public_safe",
                "review_status": "agent_pose_summary_reviewed",
                "human_review_required_for_rule_promotion": True,
            },
        },
        "sources": sources,
    }
    write_yaml(ROOT / args.output, output)
    print(f"wrote {args.output}")
    print(f"sources_with_ok_pose {len(sources)}")
    print(f"reviewed_keyframes {reviewed_frames}")
    print(f"keyframes_with_people {frames_with_people}")


if __name__ == "__main__":
    main()
