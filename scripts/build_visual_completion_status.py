from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit full visual pipeline artifacts and build a retry manifest."
    )
    parser.add_argument(
        "--manifest",
        default="data/corpus/video-visual-pipeline-manifest.yaml",
    )
    parser.add_argument(
        "--output",
        default="data/corpus/video-visual-completion-status.yaml",
    )
    parser.add_argument(
        "--retry-output",
        default="data/raw-private/video-corpus/video-visual-retry-manifest.yaml",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def artifact_status(data: dict[str, Any] | None, expected: int, version: int | None) -> dict[str, Any]:
    status = data.get("status", "missing") if data else "missing"
    frame_count = int(data.get("frame_count") or 0) if data else 0
    artifact_version = data.get("artifact_version") if data else None
    complete = status == "ok" and frame_count == expected
    if version is not None:
        complete = complete and artifact_version == version
    return {
        "status": status,
        "frame_count": frame_count,
        "artifact_version": artifact_version,
        "complete": complete,
    }


def main() -> None:
    args = parse_args()
    manifest = load_yaml(ROOT / args.manifest)
    statuses: list[dict[str, Any]] = []
    retry_jobs: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    planned_total = 0
    extracted_total = 0

    for job in manifest.get("jobs", []):
        planned = len(job.get("planned_frames", []))
        planned_total += planned
        paths = job["private_paths"]
        keyframes = load_json(ROOT / paths["keyframes_dir"] / "manifest.json")
        vlm = load_json(ROOT / paths["vlm_json"])
        pose = load_json(ROOT / paths["pose_json"])
        keyframe_status = artifact_status(keyframes, planned, None)
        vlm_status = artifact_status(vlm, planned, 2)
        pose_status = artifact_status(pose, planned, 2)
        extracted_total += keyframe_status["frame_count"]
        complete = all(
            item["complete"] for item in [keyframe_status, vlm_status, pose_status]
        )
        counts["complete" if complete else "pending"] += 1
        counts[f"keyframes_{keyframe_status['status']}"] += 1
        counts[f"vlm_{vlm_status['status']}"] += 1
        counts[f"pose_{pose_status['status']}"] += 1
        statuses.append(
            {
                "job_id": job["job_id"],
                "source_id": job["source_id"],
                "review_priority": job.get("review_priority"),
                "planned_frame_count": planned,
                "keyframes": keyframe_status,
                "vlm": vlm_status,
                "pose": pose_status,
                "complete": complete,
            }
        )
        if not complete:
            retry_jobs.append(job)

    output = {
        "visual_completion_run": {
            "run_id": f"visual_completion_{date.today().strftime('%Y%m%d')}",
            "created_at": date.today().isoformat(),
            "manifest": args.manifest,
            "summary": {
                "total_jobs": len(statuses),
                "complete_jobs": counts["complete"],
                "pending_jobs": counts["pending"],
                "planned_frames": planned_total,
                "extracted_frames": extracted_total,
                "status_counts": dict(counts),
            },
            "completion_rule": (
                "A job is complete only when exact planned keyframes, VLM artifact v2, "
                "and Pose artifact v2 are all status ok with matching frame counts."
            ),
        },
        "jobs": statuses,
    }
    retry = {
        "manifest_id": f"visual_retry_{date.today().strftime('%Y%m%d')}",
        "created_at": date.today().isoformat(),
        "base_manifest": args.manifest,
        "summary": {
            "retry_jobs": len(retry_jobs),
            "planned_frames": sum(len(job.get("planned_frames", [])) for job in retry_jobs),
        },
        "jobs": retry_jobs,
    }
    write_yaml(ROOT / args.output, output)
    write_yaml(ROOT / args.retry_output, retry)
    print(f"wrote {args.output}")
    print(f"wrote {args.retry_output}")
    print(f"complete_jobs {counts['complete']}")
    print(f"pending_jobs {counts['pending']}")
    print(f"planned_frames {planned_total}")
    print(f"extracted_frames {extracted_total}")


if __name__ == "__main__":
    main()
