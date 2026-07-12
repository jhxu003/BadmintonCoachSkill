from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.source_index import REQUIRED_SOURCE_FIELDS  # noqa: E402


TOPIC_KEYWORDS = [
    ("smash", ["杀球", "重杀", "点杀", "跳杀", "劈杀"]),
    ("high_clear", ["高远", "高球", "后场球"]),
    ("drop", ["吊球", "劈吊", "滑板", "切球"]),
    ("frontcourt", ["网前", "搓球", "勾球", "扑球", "放网", "挑球"]),
    ("drive", ["平抽", "平挡", "抽挡", "推球", "接杀", "防守"]),
    ("serve_receive", ["发球", "接发"]),
    ("backhand", ["反手", "头顶区"]),
    ("footwork", ["步法", "步伐", "启动", "回位", "蹬跨", "并步", "交叉步"]),
    ("power", ["发力", "挥拍", "鞭打", "爆发力", "借力"]),
    ("hip_rotation", ["转髋", "髋", "转体", "蹬转"]),
    ("elbow_frame", ["顶肘", "架拍", "肘", "框架"]),
    ("internal_rotation", ["内旋", "小臂旋转", "旋臂"]),
    ("grip", ["握拍", "手指", "手腕", "抓拍"]),
    ("contact_point", ["击球点", "高点", "身前", "迎球"]),
    ("doubles", ["双打", "混双", "轮转", "封网", "搭档"]),
    ("singles", ["单打", "拉吊", "突击"]),
    ("tactics", ["战术", "球路", "套路", "节奏", "落点", "线路"]),
    ("training", ["训练", "练习", "多球", "连贯", "一致性", "稳定"]),
    ("student_fit", ["新手", "业余", "进阶", "适合", "基础", "错误", "纠正"]),
    ("fitness", ["体能", "力量", "核心", "热身", "拉伸", "伤病"]),
    ("equipment", ["球拍", "磅数", "球线", "装备"]),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build one coach's public source index.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-prefix", required=True)
    parser.add_argument("--official-mid", type=int, required=True)
    parser.add_argument("--channel-title", required=True)
    parser.add_argument("--channel-url", required=True)
    parser.add_argument("--course-catalog-url", default="")
    return parser.parse_args()


def topic_tags(title: str) -> list[str]:
    tags: list[str] = []
    for topic, keywords in TOPIC_KEYWORDS:
        if any(keyword in title for keyword in keywords):
            tags.append(topic)
    return tags or ["unclassified_public_video"]


def _stroke_tags(topics: list[str]) -> list[str]:
    families = [
        topic
        for topic in topics
        if topic
        in {
            "smash",
            "high_clear",
            "drop",
            "frontcourt",
            "drive",
            "serve_receive",
            "backhand",
            "footwork",
            "doubles",
            "singles",
        }
    ]
    return families or ["all"]


def _date(timestamp: Any) -> str:
    if not isinstance(timestamp, (int, float)):
        return "unknown"
    return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()


def video_row(
    video: dict[str, Any],
    *,
    prefix: str,
    official_mid: int,
) -> dict[str, str]:
    detail = video.get("detail") or {}
    title = str(detail.get("title") or video.get("discovery_metadata", {}).get("title") or video["bvid"])
    topics = topic_tags(title)
    owner_mid = detail.get("owner_mid")
    detail_available = bool(detail)
    paid = bool(
        detail.get("arc_pay")
        or detail.get("ugc_pay")
        or detail.get("is_upower_exclusive")
        or detail.get("is_chargeable_season")
    )
    state = detail.get("state")
    accessible = detail_available and state == 0 and not paid
    methods = ",".join(video.get("discovery_methods") or [])
    collections = " | ".join(video.get("collection_titles") or [])
    notes = (
        f"Official-account public metadata; duration={detail.get('duration', 'unknown')}s; "
        f"discovered_by={methods or 'unknown'}"
    )
    if collections:
        notes += f"; collections={collections}"
    if not detail_available:
        notes += "; public detail endpoint unavailable; excluded from content parsing"
    elif paid:
        notes += "; paid/exclusive metadata only and excluded from content parsing"
    return {
        "source_id": f"{prefix}_{video['bvid'].upper()}",
        "title": title.replace("\t", " ").replace("\n", " "),
        "platform": "Bilibili",
        "url": f"https://www.bilibili.com/video/{video['bvid']}",
        "published_at": _date(detail.get("pubdate")),
        "access_type": "public" if accessible else "restricted",
        "authorization_status": "official" if owner_mid == official_mid else "public",
        "source_type": "video",
        "topic_tags": ",".join(topics),
        "stroke_tags": ",".join(_stroke_tags(topics)),
        "timestamps": "",
        "usability": "candidate" if accessible else "auxiliary",
        "confidence": "high" if detail else "medium",
        "notes": notes,
    }


def discovery_row(args: argparse.Namespace) -> dict[str, str]:
    return {
        "source_id": f"{args.source_prefix}_OFFICIAL_CHANNEL",
        "title": args.channel_title,
        "platform": "Bilibili",
        "url": args.channel_url,
        "published_at": "unknown",
        "access_type": "public",
        "authorization_status": "official",
        "source_type": "channel",
        "topic_tags": "official,teaching,discovery",
        "stroke_tags": "all",
        "timestamps": "",
        "usability": "usable",
        "confidence": "high",
        "notes": "Canonical official-account discovery seed; not direct technical evidence.",
    }


def course_row(args: argparse.Namespace) -> dict[str, str] | None:
    if not args.course_catalog_url:
        return None
    return {
        "source_id": f"{args.source_prefix}_PAID_COURSE_CATALOG",
        "title": f"{args.channel_title} paid course catalog",
        "platform": "Bilibili",
        "url": args.course_catalog_url,
        "published_at": "unknown",
        "access_type": "restricted",
        "authorization_status": "official",
        "source_type": "course_catalog",
        "topic_tags": "course_catalog,gap_analysis",
        "stroke_tags": "all",
        "timestamps": "",
        "usability": "auxiliary",
        "confidence": "high",
        "notes": "Public catalog metadata only; paid lessons are excluded from parsing and technical evidence.",
    }


def main() -> None:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = [discovery_row(args)]
    paid_catalog = course_row(args)
    if paid_catalog:
        rows.append(paid_catalog)
    rows.extend(
        video_row(video, prefix=args.source_prefix, official_mid=args.official_mid)
        for video in manifest.get("videos", [])
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_SOURCE_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output}")
    print(f"rows {len(rows)}")
    print(f"public_videos {sum(row['source_type'] == 'video' and row['access_type'] == 'public' for row in rows)}")


if __name__ == "__main__":
    main()
