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
        "--include-already-evidenced",
        action="store_true",
        help="Include sources already represented by existing public video evidence.",
    )
    parser.add_argument(
        "--evidence-dir",
        default="data/corpus/video-evidence",
        help="Public evidence directory used to detect already represented source_ids.",
    )
    return parser.parse_args()


def existing_evidence_source_ids(evidence_dir: Path) -> set[str]:
    source_ids: set[str] = set()
    for path in sorted(evidence_dir.glob("*.yaml")):
        try:
            data = load_yaml(path)
        except Exception:
            continue
        source_id = data.get("source_id")
        if source_id:
            source_ids.add(str(source_id))
    return source_ids


def main() -> None:
    args = parse_args()
    platforms = args.platform or ["Bilibili"]
    selected = select_public_video_sources(
        ROOT / args.source_index,
        platforms=set(platforms),
        include_auxiliary=args.include_auxiliary,
    )
    already_evidenced = (
        set()
        if args.include_already_evidenced
        else existing_evidence_source_ids(ROOT / args.evidence_dir)
    )
    selected = [
        item for item in selected if item.source["source_id"] not in already_evidenced
    ]
    if args.offset:
        selected = selected[args.offset :]
    if args.limit:
        selected = selected[: args.limit]
    jobs = [
        build_processing_job(item, index + 1, job_prefix=args.job_prefix)
        for index, item in enumerate(selected)
    ]
    manifest = {
        "manifest_id": "liu_hui_video_corpus_public_manifest_20260709",
        "created_at": "2026-07-09",
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
            "exclude_existing_public_evidence": not args.include_already_evidenced,
            "existing_evidence_source_count": len(already_evidenced),
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
