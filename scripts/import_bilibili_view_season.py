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


def _date_from_epoch(value: object) -> str:
    if not value:
        return "unknown"
    return datetime.fromtimestamp(int(value), tz=timezone.utc).date().isoformat()


def _source_id(prefix: str, bvid: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", bvid).strip("_").upper()
    return f"{prefix}_{slug}"


def _infer_tags(title: str) -> tuple[str, str]:
    topic_tags: list[str] = []
    stroke_tags: list[str] = []
    keyword_map = [
        ("高远", "high_clear", "high_clear"),
        ("杀球", "smash", "smash"),
        ("重杀", "smash", "smash"),
        ("点杀", "smash", "smash"),
        ("霸王杀", "smash", "smash"),
        ("跳杀", "smash", "smash"),
        ("劈杀", "smash", "smash"),
        ("滑拍", "smash", "smash"),
        ("吊球", "drop", "drop"),
        ("劈吊", "drop", "drop"),
        ("击球点", "contact_point", "smash"),
        ("实战", "match_transfer", "all"),
        ("熟练", "match_transfer", "all"),
        ("比赛", "match_transfer", "all"),
        ("力传导", "kinetic_chain", "smash"),
        ("发力", "power", "all"),
        ("框架", "power_framework", "all"),
        ("学习顺序", "learning_order", "all"),
        ("顺序", "learning_order", "all"),
        ("改动作", "action_correction", "all"),
        ("内旋", "internal_rotation", "high_clear"),
        ("转髋", "hip_rotation", "smash"),
        ("髋", "hip_rotation", "smash"),
        ("手腕", "wrist", "all"),
        ("大臂", "arm_path", "all"),
        ("顶肘", "top_elbow", "high_clear"),
        ("挥拍", "swing", "all"),
        ("步伐", "footwork", "footwork"),
        ("步法", "footwork", "footwork"),
        ("启动", "footwork", "footwork"),
        ("腿懒", "recovery", "footwork"),
        ("回位", "recovery", "footwork"),
        ("反手", "backhand", "backhand"),
        ("网前", "net", "net"),
        ("接发", "serve_receive", "serve_receive"),
        ("发球", "serve_receive", "serve_receive"),
        ("双打", "doubles", "doubles"),
        ("装备", "equipment", "all"),
        ("球拍", "equipment", "all"),
        ("卸力", "deceleration", "smash"),
        ("随摆", "follow_through", "smash"),
    ]
    for keyword, topic, stroke in keyword_map:
        if keyword in title:
            topic_tags.append(topic)
            stroke_tags.append(stroke)
    if not topic_tags:
        topic_tags.append("bilibili_season_metadata")
    if not stroke_tags:
        stroke_tags.append("all")
    return ",".join(dict.fromkeys(topic_tags)), ",".join(dict.fromkeys(stroke_tags))


def _authorization_status(parent: dict[str, object]) -> str:
    owner = parent.get("owner") if isinstance(parent.get("owner"), dict) else {}
    text = " ".join(
        [
            str(parent.get("title") or ""),
            str(parent.get("desc") or ""),
            str(owner.get("name") or ""),
        ]
    )
    if "授权" in text or str(owner.get("name") or "") == "大G羽毛球":
        return "authorized"
    return "public"


def iter_episodes(path: Path) -> list[tuple[dict[str, object], str, str, dict[str, object]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    parent = payload.get("data", {})
    season = parent.get("ugc_season") or {}
    season_title = str(season.get("title") or "unknown season")
    rows: list[tuple[dict[str, object], str, str, dict[str, object]]] = []
    for section in season.get("sections") or []:
        section_title = str(section.get("title") or "unknown section")
        for episode in section.get("episodes") or []:
            rows.append((parent, season_title, section_title, episode))
    return rows


def convert_episode(
    parent: dict[str, object],
    season_title: str,
    section_title: str,
    episode: dict[str, object],
    source_prefix: str,
) -> dict[str, str] | None:
    bvid = str(episode.get("bvid") or "")
    if not bvid:
        return None
    title = str(episode.get("title") or "Untitled Bilibili season episode")
    arc = episode.get("arc") if isinstance(episode.get("arc"), dict) else {}
    author = arc.get("author") if isinstance(arc.get("author"), dict) else {}
    topic_tags, stroke_tags = _infer_tags(title)
    return {
        "source_id": _source_id(source_prefix, bvid),
        "title": title.replace("\t", " "),
        "platform": "Bilibili",
        "url": f"https://www.bilibili.com/video/{bvid}/",
        "published_at": _date_from_epoch(arc.get("pubdate")),
        "access_type": "public",
        "authorization_status": _authorization_status(parent),
        "source_type": "video",
        "topic_tags": topic_tags,
        "stroke_tags": stroke_tags,
        "timestamps": "",
        "usability": "candidate",
        "confidence": "medium",
        "notes": (
            "Imported from Bilibili UGC season public metadata; "
            f"season_id={(parent.get('ugc_season') or {}).get('id', 'unknown')}; "
            f"season={season_title}; section={section_title}; "
            f"upper={author.get('name', 'unknown')}; review timestamps before rule use."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Bilibili view API UGC season episodes into source-index TSV rows."
    )
    parser.add_argument("json", type=Path, nargs="+")
    parser.add_argument("--source-prefix", default="LH_BILI_SEASON")
    args = parser.parse_args()

    rows = [
        row
        for path in args.json
        for parent, season_title, section_title, episode in iter_episodes(path)
        if (
            row := convert_episode(
                parent,
                season_title,
                section_title,
                episode,
                args.source_prefix,
            )
        )
        is not None
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=REQUIRED_SOURCE_FIELDS, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)


if __name__ == "__main__":
    main()
