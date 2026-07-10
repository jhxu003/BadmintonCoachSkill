from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


WEAK_TOPICS = {"doubles", "drive", "serve_receive", "drop", "footwork"}
BIOMECHANICAL_TOPICS = {
    "top_elbow",
    "contact_point",
    "hip_rotation",
    "internal_rotation",
    "wrist",
    "racket_preparation",
}
ACTION_TOPICS = {
    "high_clear",
    "smash",
    "drop",
    "drive",
    "serve_receive",
    "doubles",
    "footwork",
    *BIOMECHANICAL_TOPICS,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a complete non-YouTube visual-review queue from reviewed ASR windows."
    )
    parser.add_argument(
        "--review",
        default="data/corpus/video-asr-timestamp-review.yaml",
    )
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument(
        "--output",
        default="data/corpus/video-visual-review-manifest.yaml",
    )
    parser.add_argument("--max-windows-per-source", type=int, default=8)
    parser.add_argument("--max-frames-per-source", type=int, default=18)
    return parser.parse_args()


def load_jobs(paths: list[str]) -> dict[str, dict[str, Any]]:
    jobs: dict[str, dict[str, Any]] = {}
    for raw_path in paths:
        manifest = load_yaml(ROOT / raw_path)
        for job in manifest.get("jobs", []):
            jobs[job["job_id"]] = job
    return jobs


def has_ok_vlm(job: dict[str, Any]) -> bool:
    path = ROOT / job["private_paths"]["vlm_json"]
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status") == "ok"
    except Exception:
        return False


def frame_points(window: dict[str, Any]) -> list[dict[str, Any]]:
    start = int(window.get("start_seconds") or 0)
    end = int(window.get("end_seconds") or start)
    duration = max(end - start, 0)
    offsets = [0.5]
    if duration >= 12 and set(window.get("topic_tags", [])) & BIOMECHANICAL_TOPICS:
        offsets = [0.2, 0.5, 0.8]
    elif duration >= 6:
        offsets = [0.35, 0.7]
    labels = {0.2: "early", 0.35: "early", 0.5: "middle", 0.7: "late", 0.8: "late"}
    return [
        {
            "timestamp_seconds": int(round(start + duration * offset)),
            "phase_sample": labels[offset],
            "source_window_id": window["window_id"],
            "topic_tags": window.get("topic_tags", []),
        }
        for offset in offsets
    ]


def priority_for(topics: set[str]) -> str:
    if topics & WEAK_TOPICS and topics & BIOMECHANICAL_TOPICS:
        return "critical"
    if topics & (WEAK_TOPICS | BIOMECHANICAL_TOPICS):
        return "high"
    if topics & ACTION_TOPICS:
        return "standard"
    return "asr_only"


def main() -> None:
    args = parse_args()
    review = load_yaml(ROOT / args.review)
    jobs = load_jobs(args.manifest)
    all_manifest_vlm_sources = sum(1 for job in jobs.values() if has_ok_vlm(job))
    windows_by_job: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for window in review.get("windows", []):
        windows_by_job[window["job_id"]].append(window)

    visual_jobs: list[dict[str, Any]] = []
    asr_only_sources: list[dict[str, Any]] = []
    target_source_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    existing_vlm_visual_sources = 0
    existing_vlm_asr_only_sources = 0
    planned_frame_count = 0

    for job_id in sorted(windows_by_job):
        job = jobs.get(job_id)
        if not job:
            continue
        windows = sorted(
            windows_by_job[job_id],
            key=lambda item: (item.get("start_seconds", 0), item["window_id"]),
        )[: args.max_windows_per_source]
        topics = {
            topic
            for window in windows
            for topic in window.get("topic_tags", [])
        }
        visual_topics = sorted(topics & ACTION_TOPICS)
        if not visual_topics:
            existing_vlm = has_ok_vlm(job)
            if existing_vlm:
                existing_vlm_asr_only_sources += 1
            asr_only_sources.append(
                {
                    "job_id": job_id,
                    "source_id": job["source_id"],
                    "title": job["title"],
                    "topic_tags": sorted(topics),
                    "existing_private_vlm_artifact": existing_vlm,
                    "reason": "The reviewed windows are conceptual or planning-oriented and do not require corpus visual proof.",
                }
            )
            continue

        planned_frames: list[dict[str, Any]] = []
        seen_timestamps: set[int] = set()
        for window in windows:
            if not set(window.get("topic_tags", [])) & ACTION_TOPICS:
                continue
            for frame in frame_points(window):
                timestamp = frame["timestamp_seconds"]
                if timestamp in seen_timestamps:
                    continue
                seen_timestamps.add(timestamp)
                planned_frames.append(frame)
                if len(planned_frames) >= args.max_frames_per_source:
                    break
            if len(planned_frames) >= args.max_frames_per_source:
                break

        existing_vlm = has_ok_vlm(job)
        if existing_vlm:
            existing_vlm_visual_sources += 1
        priority = priority_for(topics)
        priority_counts[priority] += 1
        target_source_counts.update(visual_topics)
        planned_frame_count += len(planned_frames)
        visual_jobs.append(
            {
                "job_id": job_id,
                "source_id": job["source_id"],
                "title": job["title"],
                "platform": job["platform"],
                "url": job["url"],
                "authorization_status": job["authorization_status"],
                "review_priority": priority,
                "review_targets": visual_topics,
                "weak_topic_targets": sorted(topics & WEAK_TOPICS),
                "biomechanical_targets": sorted(topics & BIOMECHANICAL_TOPICS),
                "existing_private_vlm_artifact": existing_vlm,
                "processing_status": (
                    "existing_vlm_needs_public_safe_summary"
                    if existing_vlm
                    else "queued_visual_review"
                ),
                "planned_frames": planned_frames,
                "required_observations": [
                    "player and racket visibility",
                    "racket preparation and contact or pre-contact phase",
                    "lower-body orientation and balance",
                    "recovery state after the action",
                    "occlusion, camera angle, and confidence limits",
                ],
                "pose_requirement": (
                    "Use 2D pose only as a body-keypoint proxy; racket and true shoulder rotation need VLM or human visual review."
                ),
                "promotion_boundary": (
                    "Visual model output remains a candidate until a human reviewer checks the referenced frames."
                ),
            }
        )

    output = {
        "visual_review_run": {
            "run_id": f"non_youtube_visual_review_manifest_{date.today().strftime('%Y%m%d')}",
            "created_at": date.today().isoformat(),
            "scope": [
                "All indexed Bilibili sources with agent-reviewed ASR timestamp windows.",
                "YouTube is excluded by project decision.",
                "Douyin and Instagram are recorded as access gaps until stable public metadata or media access is available.",
            ],
            "inputs": {
                "timestamp_review": args.review,
                "manifests": args.manifest,
            },
            "summary": {
                "sources_with_reviewed_asr_windows": len(windows_by_job),
                "visual_review_jobs": len(visual_jobs),
                "asr_only_sources": len(asr_only_sources),
                "existing_private_vlm_sources_with_reviewed_asr": (
                    existing_vlm_visual_sources + existing_vlm_asr_only_sources
                ),
                "existing_private_vlm_sources_without_reviewed_asr": (
                    all_manifest_vlm_sources
                    - existing_vlm_visual_sources
                    - existing_vlm_asr_only_sources
                ),
                "existing_private_vlm_sources_all_manifests": all_manifest_vlm_sources,
                "existing_private_vlm_visual_jobs": existing_vlm_visual_sources,
                "existing_private_vlm_asr_only_sources": existing_vlm_asr_only_sources,
                "queued_visual_sources": len(visual_jobs) - existing_vlm_visual_sources,
                "planned_keyframes": planned_frame_count,
                "priority_counts": dict(priority_counts),
                "target_source_counts": dict(target_source_counts.most_common()),
            },
            "runtime_guidance": {
                "download_and_keyframes": "Run download,keyframes with teaching-window timestamps on a compute node using node-local private storage.",
                "vlm": "Use a badminton-specific visible-evidence prompt and do not infer invisible biomechanics.",
                "pose": "Use pose for coarse body geometry only; it cannot see racket orientation or prove internal rotation.",
                "public_output": "Commit only aggregate statuses and original summaries; keep media, frames, model text, and keypoints private.",
            },
            "non_youtube_access_gaps": [
                {
                    "platform": "Douyin",
                    "status": "blocked_dynamic_profile",
                    "last_checked": date.today().isoformat(),
                    "reason": "The public profile request still returns a dynamic 404 and no stable per-video metadata export.",
                },
                {
                    "platform": "Instagram",
                    "status": "blocked_timeout",
                    "last_checked": date.today().isoformat(),
                    "reason": "The indexed public reel timed out in both direct HTTP and yt-dlp access attempts.",
                },
            ],
        },
        "jobs": visual_jobs,
        "asr_only_sources": asr_only_sources,
    }
    write_yaml(ROOT / args.output, output)
    print(f"wrote {args.output}")
    print(f"visual_review_jobs {len(visual_jobs)}")
    print(f"asr_only_sources {len(asr_only_sources)}")
    print(
        "existing_private_vlm_sources_all_manifests "
        f"{all_manifest_vlm_sources}"
    )
    print(f"planned_keyframes {planned_frame_count}")


if __name__ == "__main__":
    main()
