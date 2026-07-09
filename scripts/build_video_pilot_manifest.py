from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import (  # noqa: E402
    build_processing_job,
    select_pilot_sources,
    write_yaml,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a public-safe pilot manifest for Liu Hui video parsing."
    )
    parser.add_argument(
        "--source-index",
        default="data/source-index.tsv",
        help="TSV source index to select public Bilibili videos from.",
    )
    parser.add_argument(
        "--output",
        default="data/corpus/video-pilot-manifest.yaml",
        help="Public-safe manifest path.",
    )
    parser.add_argument("--limit", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected = select_pilot_sources(ROOT / args.source_index, limit=args.limit)
    jobs = [
        build_processing_job(item, index + 1)
        for index, item in enumerate(selected)
    ]
    manifest = {
        "manifest_id": "liu_hui_video_pilot_20260708",
        "created_at": "2026-07-08",
        "purpose": (
            "Pilot content-level parsing for Liu Hui public badminton teaching videos. "
            "Raw videos, subtitles, OCR dumps, VLM dumps, and model logs stay private."
        ),
        "selection_policy": {
            "platform": "Bilibili",
            "access_type": "public",
            "source_type": "video",
            "priority_topics": [
                "smash",
                "high_clear",
                "rear_footwork",
                "top_elbow",
                "hip_rotation",
                "internal_rotation",
                "power_framework",
                "student_fit",
                "match_transfer",
            ],
        },
        "jobs": jobs,
    }
    write_yaml(ROOT / args.output, manifest)
    print(f"wrote {args.output}")
    print(f"jobs {len(jobs)}")
    for job in jobs[:5]:
        print(f"{job['job_id']}\t{','.join(job['priority_topics'])}\t{job['title']}")


if __name__ == "__main__":
    main()
