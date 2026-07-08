from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.source_index import REQUIRED_SOURCE_FIELDS


STRONG_RELEVANCE_KEYWORDS = [
    "刘辉",
    "大G羽毛球",
]


def _date_from_epoch(value: object) -> str:
    if not value:
        return "unknown"
    return datetime.fromtimestamp(int(value), tz=timezone.utc).date().isoformat()


def _source_id(prefix: str, bvid: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", bvid).strip("_").upper()
    return f"{prefix}_{slug}"


def _text(item: dict[str, object]) -> str:
    upper = item.get("upper") if isinstance(item.get("upper"), dict) else {}
    return " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("intro") or ""),
            str(upper.get("name") or ""),
        ]
    )


def _is_relevant(item: dict[str, object]) -> bool:
    text = _text(item)
    upper = item.get("upper") if isinstance(item.get("upper"), dict) else {}
    upper_name = str(upper.get("name") or "")
    if any(keyword in text for keyword in STRONG_RELEVANCE_KEYWORDS):
        return True
    if upper_name == "大G羽毛球":
        return True
    return False


def _authorization_status(item: dict[str, object]) -> str:
    text = _text(item)
    if "授权" in text or "大G羽毛球" in text:
        return "authorized"
    return "public"


def _infer_tags(title: str) -> tuple[str, str]:
    topic_tags: list[str] = []
    stroke_tags: list[str] = []
    keyword_map = [
        ("高远", "high_clear", "high_clear"),
        ("杀球", "smash", "smash"),
        ("点杀", "smash", "smash"),
        ("步伐", "footwork", "footwork"),
        ("步法", "footwork", "footwork"),
        ("转髋", "hip_rotation", "smash"),
        ("内旋", "internal_rotation", "high_clear"),
        ("发力", "power", "all"),
        ("顶肘", "top_elbow", "high_clear"),
        ("接发", "serve_receive", "serve_receive"),
        ("发球", "serve_receive", "serve_receive"),
        ("反手", "backhand", "backhand"),
        ("网前", "net", "net"),
        ("双打", "doubles", "doubles"),
    ]
    for keyword, topic, stroke in keyword_map:
        if keyword in title:
            topic_tags.append(topic)
            stroke_tags.append(stroke)
    if not topic_tags:
        topic_tags.append("bilibili_public_metadata")
    if not stroke_tags:
        stroke_tags.append("all")
    return ",".join(dict.fromkeys(topic_tags)), ",".join(dict.fromkeys(stroke_tags))


def iter_medias(paths: list[Path]) -> list[dict[str, object]]:
    medias: list[dict[str, object]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        data = payload.get("data", {})
        medias.extend(data.get("medias") or [])
    return medias


def convert_item(item: dict[str, object], source_prefix: str) -> dict[str, str] | None:
    if not _is_relevant(item):
        return None
    bvid = str(item.get("bvid") or item.get("bv_id") or "")
    if not bvid:
        return None
    title = str(item.get("title") or "Untitled Bilibili public metadata item")
    upper = item.get("upper") if isinstance(item.get("upper"), dict) else {}
    topic_tags, stroke_tags = _infer_tags(title)
    return {
        "source_id": _source_id(source_prefix, bvid),
        "title": title.replace("\t", " "),
        "platform": "Bilibili",
        "url": f"https://www.bilibili.com/video/{bvid}/",
        "published_at": _date_from_epoch(item.get("pubtime")),
        "access_type": "public",
        "authorization_status": _authorization_status(item),
        "source_type": "video",
        "topic_tags": topic_tags,
        "stroke_tags": stroke_tags,
        "timestamps": "",
        "usability": "candidate",
        "confidence": "medium",
        "notes": (
            "Imported from Bilibili public favorite/list metadata; "
            f"upper={upper.get('name', 'unknown')}; review timestamps before rule use."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Bilibili favorite/list API JSON pages into source-index TSV rows."
    )
    parser.add_argument("json", type=Path, nargs="+")
    parser.add_argument("--source-prefix", default="LH_BILI_FAV")
    args = parser.parse_args()

    rows = [
        row
        for item in iter_medias(args.json)
        if (row := convert_item(item, args.source_prefix)) is not None
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=REQUIRED_SOURCE_FIELDS, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)


if __name__ == "__main__":
    main()
