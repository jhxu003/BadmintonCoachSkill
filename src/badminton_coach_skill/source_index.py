from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


REQUIRED_SOURCE_FIELDS = [
    "source_id",
    "title",
    "platform",
    "url",
    "published_at",
    "access_type",
    "authorization_status",
    "source_type",
    "topic_tags",
    "stroke_tags",
    "timestamps",
    "usability",
    "confidence",
    "notes",
]


def read_source_index(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != REQUIRED_SOURCE_FIELDS:
            raise ValueError("source index header does not match the required contract")
        return list(reader)


def summarize_source_index(rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        "total_sources": len(rows),
        "by_platform": dict(Counter(row["platform"] for row in rows)),
        "by_authorization_status": dict(
            Counter(row["authorization_status"] for row in rows)
        ),
        "by_source_type": dict(Counter(row["source_type"] for row in rows)),
        "by_usability": dict(Counter(row["usability"] for row in rows)),
    }
