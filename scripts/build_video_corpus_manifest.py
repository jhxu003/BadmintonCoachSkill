from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import (  # noqa: E402
    build_processing_job,
    load_yaml,
    select_public_video_sources,
    write_yaml,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a public-safe full-corpus manifest for Liu Hui video parsing."
    )
    parser.add_argument("--source-index", default="data/source-index.tsv")
    parser.add_argument("--output", default="data/corpus/video-corpus-manifest.yaml")
    parser.add_argument(
        "--platform",
        action="append",
        default=None,
        help="Platform to include. Can be passed more than once. Defaults to Bilibili.",
    )
    parser.add_argument(
        "--include-auxiliary",
        action="store_true",
        help="Include auxiliary public videos for discovery coverage. They still require review before promotion.",
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--job-prefix", default="corpus")
    parser.add_argument(
        "--existing-manifest",
        default="data/corpus/video-corpus-manifest.yaml",
        help="Canonical manifest used to preserve stable job ids and availability state.",
    )
    return parser.parse_args()


def existing_jobs(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    manifest = load_yaml(path)
    return {str(job["source_id"]): job for job in manifest.get("jobs", [])}


def main() -> None:
    args = parse_args()
    platforms = args.platform or ["Bilibili"]
    selected = select_public_video_sources(
        ROOT / args.source_index,
        platforms=set(platforms),
        include_auxiliary=args.include_auxiliary,
    )
    if args.offset:
        selected = selected[args.offset :]
    if args.limit:
        selected = selected[: args.limit]
    prior_jobs = existing_jobs(ROOT / args.existing_manifest)
    used_job_ids = {str(job["job_id"]) for job in prior_jobs.values()}
    used_indices = [
        int(parts[1])
        for job_id in used_job_ids
        if len(parts := job_id.split("-", 2)) > 1
        and parts[0] == args.job_prefix
        and parts[1].isdigit()
    ]
    next_index = max(used_indices, default=0) + 1
    jobs = []
    for item in selected:
        source_id = str(item.source["source_id"])
        prior = prior_jobs.get(source_id)
        if prior:
            job_id = str(prior["job_id"])
        else:
            while True:
                job_id = f"{args.job_prefix}-{next_index:03d}-{source_id.lower()}"
                next_index += 1
                if job_id not in used_job_ids:
                    break
        used_job_ids.add(job_id)
        job = build_processing_job(
            item,
            next_index,
            job_prefix=args.job_prefix,
            job_id=job_id,
        )
        if prior and prior.get("processing_status") == "unavailable":
            job["processing_status"] = "unavailable"
            job["review_status"] = prior.get("review_status", "access_unavailable")
            job["availability_note"] = prior.get("availability_note", "")
        jobs.append(job)
    manifest = {
        "manifest_id": "liu_hui_video_corpus_public_manifest_20260710",
        "created_at": "2026-07-10",
        "purpose": (
            "Full public-source content-level parsing manifest for Liu Hui badminton "
            "teaching videos. Raw media, ASR transcripts, OCR dumps, VLM dumps, "
            "cookies, and model logs stay private."
        ),
        "selection_policy": {
            "platforms": platforms,
            "include_auxiliary": args.include_auxiliary,
            "access_type": "public",
            "source_type": "video",
            "source_jobs": len(jobs),
            "preserve_existing_job_ids": True,
        },
        "jobs": jobs,
    }
    write_yaml(ROOT / args.output, manifest)
    print(f"wrote {args.output}")
    print(f"jobs {len(jobs)}")
    for job in jobs[:10]:
        print(f"{job['job_id']}\t{job['source_id']}\t{job['title']}")


if __name__ == "__main__":
    main()
