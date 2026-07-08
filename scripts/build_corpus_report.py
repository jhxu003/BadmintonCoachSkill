from __future__ import annotations

from pathlib import Path
import csv
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.source_index import read_source_index, summarize_source_index


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def main() -> None:
    source_rows = read_source_index(ROOT / "data" / "source-index.tsv")
    teaching_points = yaml.safe_load(
        (ROOT / "data" / "corpus" / "teaching-points.yaml").read_text(
            encoding="utf-8"
        )
    )
    taxonomy = yaml.safe_load(
        (ROOT / "data" / "corpus" / "system-taxonomy.yaml").read_text(
            encoding="utf-8"
        )
    )
    source_topic_map = yaml.safe_load(
        (ROOT / "data" / "corpus" / "source-topic-map.yaml").read_text(
            encoding="utf-8"
        )
    )
    with (ROOT / "data" / "corpus" / "public-access-log.tsv").open(
        newline="", encoding="utf-8"
    ) as handle:
        access_rows = list(csv.DictReader(handle, delimiter="\t"))
    archive_manifest = yaml.safe_load(
        (ROOT / "data" / "corpus" / "archive-manifest.yaml").read_text(
            encoding="utf-8"
        )
    )
    timestamp_review_path = ROOT / "data" / "corpus" / "timestamp-review.yaml"
    timestamp_review = (
        yaml.safe_load(timestamp_review_path.read_text(encoding="utf-8"))
        if timestamp_review_path.exists()
        else {"teaching_point_reviews": [], "core_video_timestamp_notes": []}
    )
    dedup_path = ROOT / "data" / "corpus" / "deduplication-map.yaml"
    dedup = (
        yaml.safe_load(dedup_path.read_text(encoding="utf-8"))
        if dedup_path.exists()
        else {"deduplication_run": {"summary": {}}}
    )
    summary = summarize_source_index(source_rows)
    ready_points = [
        point for point in teaching_points if point["status"] == "ready_for_skill"
    ]
    review_points = [
        point
        for point in teaching_points
        if point["status"] == "needs_timestamp_review"
    ]

    print("# Corpus Build Report")
    print()
    print(f"Total sources: {summary['total_sources']}")
    print(f"Teaching points: {len(teaching_points)}")
    print(f"Ready for skill: {len(ready_points)}")
    print(f"Needs timestamp review: {len(review_points)}")
    print()
    print("Official/authorized/public separation:")
    print(_format_counts(summary["by_authorization_status"]))
    print()
    print("Platforms:")
    print(_format_counts(summary["by_platform"]))
    print()
    print("Usability:")
    print(_format_counts(summary["by_usability"]))
    print()
    print("Taxonomy sections:")
    print(_format_counts({key: len(value) for key, value in taxonomy.items()}))
    print()
    print(f"Source-topic mappings: {len(source_topic_map)}")
    print(f"Access attempts: {len(access_rows)}")
    print(f"Archive manifests: {len(archive_manifest['archives'])}")
    print()
    print("Timestamp review:")
    print(
        _format_counts(
            {
                "core_video_notes": len(
                    timestamp_review.get("core_video_timestamp_notes") or []
                ),
                "teaching_point_reviews": len(
                    timestamp_review.get("teaching_point_reviews") or []
                ),
            }
        )
    )
    print()
    print("Deduplication:")
    print(_format_counts(dedup.get("deduplication_run", {}).get("summary", {})))


if __name__ == "__main__":
    main()
