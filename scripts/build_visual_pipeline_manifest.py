from __future__ import annotations

import argparse
import copy
from datetime import date
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


VLM_MODEL_NAME = "Qwen3-VL-8B-Instruct"
VLM_ARTIFACT_VERSION = 4
VLM_SCHEMA = "visible_still_frame_v2"
POSE_MODEL_NAME = "yolo11n-pose.pt"
POSE_ARTIFACT_VERSION = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an executable pipeline manifest from the visual review queue."
    )
    parser.add_argument(
        "--review-manifest",
        default="data/corpus/video-visual-review-manifest.yaml",
    )
    parser.add_argument(
        "--source-manifest",
        action="append",
        default=[],
        help="Original pipeline manifest. May be passed more than once.",
    )
    parser.add_argument(
        "--output",
        default="data/corpus/video-visual-pipeline-manifest.yaml",
    )
    parser.add_argument("--coach-id", default="liu-hui")
    return parser.parse_args()


def source_jobs(paths: list[str]) -> dict[str, dict[str, Any]]:
    jobs: dict[str, dict[str, Any]] = {}
    for raw_path in paths:
        data = load_yaml(ROOT / raw_path)
        for job in data.get("jobs", []):
            jobs[job["job_id"]] = job
    return jobs


def main() -> None:
    args = parse_args()
    manifests = args.source_manifest or [
        "data/corpus/video-corpus-manifest.yaml",
    ]
    review = load_yaml(ROOT / args.review_manifest)
    originals = source_jobs(manifests)
    jobs: list[dict[str, Any]] = []
    missing: list[str] = []
    planned_frames = 0

    for review_job in review.get("jobs", []):
        job_id = review_job["job_id"]
        original = originals.get(job_id)
        if not original:
            missing.append(job_id)
            continue
        job = copy.deepcopy(original)
        job["review_priority"] = review_job["review_priority"]
        job["visual_review_targets"] = review_job.get("review_targets", [])
        job["weak_topic_targets"] = review_job.get("weak_topic_targets", [])
        job["biomechanical_targets"] = review_job.get("biomechanical_targets", [])
        job["planned_frames"] = copy.deepcopy(review_job.get("planned_frames", []))
        job["visual_processing_status"] = review_job.get("processing_status")
        job.setdefault("models", {})["vlm"] = VLM_MODEL_NAME
        job["models"]["pose"] = POSE_MODEL_NAME
        planned_frames += len(job["planned_frames"])
        jobs.append(job)

    output = {
        "manifest_id": f"{args.coach_id.replace('-', '_')}_visual_pipeline_{date.today().strftime('%Y%m%d')}",
        "created_at": date.today().isoformat(),
        "purpose": (
            "Executable non-YouTube visual pipeline manifest using the exact reviewed "
            "teaching-window frame plan."
        ),
        "source_manifests": manifests,
        "review_manifest": args.review_manifest,
        "model_contract": {
            "vlm_model": VLM_MODEL_NAME,
            "vlm_artifact_version": VLM_ARTIFACT_VERSION,
            "vlm_schema": VLM_SCHEMA,
            "pose_model": POSE_MODEL_NAME,
            "pose_artifact_version": POSE_ARTIFACT_VERSION,
        },
        "summary": {
            "review_jobs": len(review.get("jobs", [])),
            "pipeline_jobs": len(jobs),
            "planned_frames": planned_frames,
            "missing_source_jobs": len(missing),
        },
        "missing_source_job_ids": missing,
        "jobs": jobs,
    }
    write_yaml(ROOT / args.output, output)
    print(f"wrote {args.output}")
    print(f"pipeline_jobs {len(jobs)}")
    print(f"planned_frames {planned_frames}")
    print(f"missing_source_jobs {len(missing)}")


if __name__ == "__main__":
    main()
