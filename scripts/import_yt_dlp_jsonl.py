from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.source_index import REQUIRED_SOURCE_FIELDS


def _published_at(item: dict[str, object]) -> str:
    raw = str(item.get("upload_date") or item.get("release_date") or "unknown")
    if re.fullmatch(r"\d{8}", raw):
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


def _source_id(prefix: str, item: dict[str, object]) -> str:
    raw = str(item.get("id") or item.get("display_id") or item.get("title") or "item")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_").upper()
    return f"{prefix}_{slug}" if slug else f"{prefix}_ITEM"


def _url(item: dict[str, object]) -> str:
    return str(item.get("webpage_url") or item.get("url") or "")


def _infer_tags(title: str) -> tuple[str, str]:
    topic_tags: list[str] = []
    stroke_tags: list[str] = []
    keyword_map = [
        ("高远", "high_clear", "high_clear"),
        ("杀球", "smash", "smash"),
        ("重杀", "smash", "smash"),
        ("步伐", "footwork", "footwork"),
        ("步法", "footwork", "footwork"),
        ("转髋", "hip_rotation", "smash"),
        ("内旋", "internal_rotation", "high_clear"),
        ("鞭打", "whip", "smash"),
        ("顶肘", "top_elbow", "high_clear"),
        ("击球点", "contact_point", "high_clear"),
        ("发力", "power", "all"),
    ]
    for keyword, topic, stroke in keyword_map:
        if keyword in title:
            topic_tags.append(topic)
            stroke_tags.append(stroke)

    if not topic_tags:
        topic_tags.append("imported_metadata")
    if not stroke_tags:
        stroke_tags.append("all")

    return ",".join(dict.fromkeys(topic_tags)), ",".join(dict.fromkeys(stroke_tags))


def convert_item(
    item: dict[str, object],
    source_prefix: str,
    authorization_status: str,
    platform: str,
) -> dict[str, str]:
    title = str(item.get("title") or "Untitled public metadata item")
    topic_tags, stroke_tags = _infer_tags(title)
    return {
        "source_id": _source_id(source_prefix, item),
        "title": title.replace("\t", " "),
        "platform": platform,
        "url": _url(item),
        "published_at": _published_at(item),
        "access_type": "public",
        "authorization_status": authorization_status,
        "source_type": "video",
        "topic_tags": topic_tags,
        "stroke_tags": stroke_tags,
        "timestamps": "",
        "usability": "candidate",
        "confidence": "medium",
        "notes": "Imported from yt-dlp public metadata JSONL; review timestamps before rule use.",
    }


def read_jsonl(path: Path) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    return items


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert yt-dlp JSONL metadata into BadmintonCoachSkill source-index TSV rows."
    )
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--source-prefix", default="LH_YT_AUTO")
    parser.add_argument(
        "--authorization-status",
        default="public",
        choices=["official", "authorized", "public", "third_party"],
    )
    parser.add_argument("--platform", default="YouTube")
    args = parser.parse_args()

    writer = csv.DictWriter(sys.stdout, fieldnames=REQUIRED_SOURCE_FIELDS, delimiter="\t")
    writer.writeheader()
    for item in read_jsonl(args.jsonl):
        writer.writerow(
            convert_item(
                item,
                source_prefix=args.source_prefix,
                authorization_status=args.authorization_status,
                platform=args.platform,
            )
        )


if __name__ == "__main__":
    main()
