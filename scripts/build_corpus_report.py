from __future__ import annotations

from pathlib import Path
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


if __name__ == "__main__":
    main()
