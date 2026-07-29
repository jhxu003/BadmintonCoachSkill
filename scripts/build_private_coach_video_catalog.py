#!/usr/bin/env python3
"""Build a private, media-free technical catalogue for the three coach corpora.

The catalogue reads the existing lesson-package JSON files only.  It does not
download, transcode, copy, or publish video, frames, ASR, or model outputs.
Each video may belong to more than one technical family; a title fallback is
kept visibly separate from the semantic inventory so uncertainty is not hidden.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Batch:
    coach_id: str
    coach_name: str
    directory: str


DEFAULT_BATCHES = (
    Batch("liu-hui", "刘辉", ".runtime/full-corpus-processing-v1/liu-hui-context-v1"),
    Batch("li-yuxuan", "李宇轩", ".runtime/full-corpus-processing-v1/li-yuxuan-v1"),
    Batch("zheng-siwei", "郑思维", ".runtime/full-corpus-processing-v1/zheng-siwei-v1"),
)


CATEGORIES = (
    ("overhead_attack", "后场头顶与进攻"),
    ("overhead_variation", "高远、吊球与后场变化"),
    ("midcourt_exchange", "中前场平抽挡与快速交换"),
    ("frontcourt", "网前控球与前场进攻"),
    ("backhand", "反手与被动过渡"),
    ("serve_receive", "发接发与前三拍"),
    ("footwork", "步法、启动、到位与回收"),
    ("defense", "防守、接杀与反击过渡"),
    ("doubles", "双打轮转与战术通道"),
    ("preparation_power", "持拍准备与动作发力链"),
    ("equipment", "装备、球拍与安全"),
    ("conditioning", "训练计划、体能与康复"),
    ("match_analysis", "实战、比赛与战术复盘"),
    ("coaching_meta", "学习路径、诊断与技术问答"),
    ("non_instructional", "非教学／生活／产品信息"),
    ("unresolved", "待进一步路由"),
)
CATEGORY_NAMES = dict(CATEGORIES)


ACTION_CATEGORY = {
    "smash": "overhead_attack",
    "jump_smash": "overhead_attack",
    "forehand_attack": "overhead_attack",
    "overhead_skill": "overhead_attack",
    "high_clear": "overhead_variation",
    "drop": "overhead_variation",
    "slice_drop": "overhead_variation",
    "light_drop": "overhead_variation",
    "heavy_slice_drop": "overhead_variation",
    "drive": "midcourt_exchange",
    "forehand_drive": "midcourt_exchange",
    "backhand_drive": "midcourt_exchange",
    "drive_exchange": "midcourt_exchange",
    "forehand_transition": "midcourt_exchange",
    "net": "frontcourt",
    "net_skill": "frontcourt",
    "backhand": "backhand",
    "serve_receive": "serve_receive",
    "rear_footwork": "footwork",
    "front_footwork": "footwork",
    "footwork": "footwork",
    "defense": "defense",
    "smash_defense": "defense",
    "defense_transition": "defense",
    "doubles": "doubles",
    "racket_preparation": "preparation_power",
    "equipment": "equipment",
    "conditioning": "conditioning",
    "tactical_review": "match_analysis",
}

FAMILY_CATEGORY = {
    "overhead": "overhead_attack",
    "overhead_variation": "overhead_variation",
    "midcourt_fast_exchange": "midcourt_exchange",
    "drive_exchange": "midcourt_exchange",
    "forehand_transition": "midcourt_exchange",
    "frontcourt": "frontcourt",
    "frontcourt_skill": "frontcourt",
    "backhand": "backhand",
    "serve_receive": "serve_receive",
    "footwork": "footwork",
    "defense": "defense",
    "defense_transition": "defense",
    "doubles_context": "doubles",
    "preparation": "preparation_power",
    "equipment": "equipment",
    "conditioning": "conditioning",
}


def _as_strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def _category_for_technique(technique: dict[str, Any]) -> str | None:
    action = str(technique.get("action", "")).strip()
    family = str(technique.get("family_id", "")).strip()
    return ACTION_CATEGORY.get(action) or FAMILY_CATEGORY.get(family)


def title_fallback(title: str) -> tuple[str, str]:
    """Return a visible, deterministic fallback for packages with no route."""
    normalized = title.lower()
    rules = (
        (("旅游", "衣服", "日常", "vlog"), "non_instructional", "title_fallback_non_instructional"),
        (("搓球", "勾球", "网前", "挑球", "推球", "扑球", "封网"), "frontcourt", "title_fallback"),
        (("杀球", "杀的", "重杀", "跳杀"), "overhead_attack", "title_fallback"),
        (("高远", "吊球", "劈吊", "滑板"), "overhead_variation", "title_fallback"),
        (("接发", "发球", "前三拍"), "serve_receive", "title_fallback"),
        (("步法", "移动", "到位", "回位"), "footwork", "title_fallback"),
        (("反手",), "backhand", "title_fallback"),
        (("防守", "接杀", "反击"), "defense", "title_fallback"),
        (("双打", "混双", "轮转"), "doubles", "title_fallback"),
        (("单打", "比赛", "实战", "对抗"), "match_analysis", "title_fallback"),
        (("卷腹", "体能", "康复", "热身", "球感", "训练"), "conditioning", "title_fallback"),
        (("后仰", "闪动", "甜区", "顶髋", "发力", "握拍"), "preparation_power", "title_fallback"),
        (("课程", "网课", "技术", "战术", "问答"), "coaching_meta", "title_fallback"),
    )
    for keywords, category_id, source in rules:
        if any(keyword in normalized for keyword in keywords):
            return category_id, source
    return "unresolved", "title_fallback_unresolved"


def _compact_techniques(package: dict[str, Any]) -> list[dict[str, Any]]:
    """Merge top-level and per-window technique routes without episode/media data."""
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}

    def add(raw: Any, *, window_id: str | None = None) -> None:
        if not isinstance(raw, dict):
            return
        action = str(raw.get("action", "")).strip()
        family = str(raw.get("family_id", "")).strip()
        label = str(raw.get("label_zh", "")).strip()
        if not any((action, family, label)):
            return
        key = action, family, label
        item = merged.setdefault(
            key,
            {
                "action": action,
                "family_id": family,
                "label_zh": label,
                "taxonomy_paths": [],
                "semantic_bases": [],
                "semantic_review_status": str(raw.get("semantic_review_status", "model_candidate")),
                "window_ids": [],
            },
        )
        path = _as_strings(raw.get("taxonomy_path"))
        if path and path not in item["taxonomy_paths"]:
            item["taxonomy_paths"].append(path)
        basis = str(raw.get("semantic_basis", "")).strip()
        if basis and basis not in item["semantic_bases"]:
            item["semantic_bases"].append(basis)
        status = str(raw.get("semantic_review_status", "")).strip()
        if status == "agent_reviewed":
            item["semantic_review_status"] = status
        if window_id and window_id not in item["window_ids"]:
            item["window_ids"].append(window_id)

    for technique in package.get("techniques", []):
        add(technique)
    for unit in package.get("semantic_inventory", []):
        if not isinstance(unit, dict):
            continue
        window_id = str(unit.get("window_id", "")).strip() or None
        for technique in unit.get("techniques", []):
            add(technique, window_id=window_id)
    return sorted(merged.values(), key=lambda item: (item["family_id"], item["action"], item["label_zh"]))


def video_record(package: dict[str, Any], coach: Batch) -> dict[str, Any]:
    video = package.get("video") if isinstance(package.get("video"), dict) else {}
    techniques = _compact_techniques(package)
    categories: dict[str, set[str]] = {}
    for technique in techniques:
        category_id = _category_for_technique(technique)
        if category_id:
            categories.setdefault(category_id, set()).add("semantic_inventory")

    title = str(video.get("title", "")).strip() or "未命名视频"
    if not categories:
        category_id, source = title_fallback(title)
        categories.setdefault(category_id, set()).add(source)

    source_id = str(video.get("source_id", "")).strip()
    review_statuses = {item["semantic_review_status"] for item in techniques}
    evidence_status = "agent_reviewed" if "agent_reviewed" in review_statuses else "model_candidate"
    if not techniques:
        evidence_status = next(iter(next(iter(categories.values()))))
    return {
        "source_id": source_id,
        "job_id": str(video.get("job_id", "")).strip(),
        "title": title,
        "url": str(video.get("url", "")).strip(),
        "duration_seconds": video.get("duration_seconds"),
        "source_upload_date": str(video.get("source_upload_date", "")).strip(),
        "source_tags": _as_strings(video.get("source_tags")),
        "evidence_status": evidence_status,
        "techniques": techniques,
        "categories": [
            {
                "id": category_id,
                "name": CATEGORY_NAMES[category_id],
                "sources": sorted(sources),
            }
            for category_id, sources in sorted(categories.items(), key=lambda item: list(CATEGORY_NAMES).index(item[0]))
        ],
    }


def _package_paths(batch_root: Path) -> list[Path]:
    return sorted((batch_root / "videos").glob("*/lesson-package.json"))


def build_catalog(project_root: Path, batches: Iterable[Batch] = DEFAULT_BATCHES) -> dict[str, Any]:
    coach_payloads: list[dict[str, Any]] = []
    for batch in batches:
        batch_root = project_root / batch.directory
        paths = _package_paths(batch_root)
        if not paths:
            raise SystemExit(f"no lesson packages found for {batch.coach_id}: {batch_root}")
        records = []
        for path in paths:
            try:
                package = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SystemExit(f"invalid lesson package: {path}") from exc
            if not isinstance(package, dict):
                raise SystemExit(f"lesson package is not an object: {path}")
            records.append(video_record(package, batch))

        if len({record["source_id"] for record in records}) != len(records):
            raise SystemExit(f"duplicate source ids in {batch.coach_id} lesson packages")
        counts = Counter(category["id"] for record in records for category in record["categories"])
        evidence_counts = Counter(record["evidence_status"] for record in records)
        coach_payloads.append(
            {
                "coach_id": batch.coach_id,
                "coach_name": batch.coach_name,
                "source_batch": batch.directory,
                "video_count": len(records),
                "category_counts": [
                    {"id": category_id, "name": name, "video_count": counts.get(category_id, 0)}
                    for category_id, name in CATEGORIES
                    if counts.get(category_id, 0)
                ],
                "evidence_counts": dict(sorted(evidence_counts.items())),
                "videos": sorted(records, key=lambda record: (record["title"], record["source_id"])),
            }
        )
    return {
        "schema_version": "private-coach-video-catalog/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "publication_boundary": "private catalogue only; no media, frames, ASR, episode paths, or model outputs are included",
        "technical_categories": [{"id": category_id, "name": name} for category_id, name in CATEGORIES],
        "total_video_count": sum(item["video_count"] for item in coach_payloads),
        "coaches": coach_payloads,
    }


def _render_html(catalog: dict[str, Any]) -> str:
    payload = json.dumps(catalog, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang=\"zh-CN\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>BadmintonCoachSkill · 私有视频技术目录</title>
<style>
body{{margin:0;background:#f1f6f2;color:#17382b;font:14px/1.55 Inter,\"Noto Sans SC\",system-ui,sans-serif}}main{{max-width:1260px;margin:auto;padding:34px 24px 60px}}h1{{margin:0;font-size:34px}}p{{color:#557064}}.notice{{padding:12px 14px;border-left:4px solid #d48b25;background:#fff5df}}.filters{{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}}select{{min-width:220px;padding:10px;border:1px solid #c9dacf;border-radius:6px;background:#fff;color:#17382b}}.stats{{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}}.stat{{padding:10px 12px;background:#fff;border:1px solid #d7e4dc;border-radius:6px}}#categories{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin:18px 0 24px}}button{{padding:10px;text-align:left;border:1px solid #c9dacf;background:#fff;border-radius:6px;cursor:pointer;color:#17382b}}button.active{{border-color:#16754c;background:#e7f5ec}}#results{{display:grid;gap:9px}}article{{padding:15px;background:#fff;border:1px solid #d7e4dc;border-radius:7px}}article h2{{margin:0;font-size:16px}}a{{color:#126a43}}.tags{{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}}.tags span{{padding:3px 7px;background:#edf5ef;color:#315e48;border-radius:99px;font-size:12px}}small{{color:#6e8579}}.empty{{padding:30px;background:#fff;border:1px dashed #a7c3b3;text-align:center}}@media(max-width:600px){{main{{padding:22px 14px}}h1{{font-size:27px}}select{{width:100%}}}}
</style>
<main><h1>三位教练 · 视频技术目录</h1><p>共 <b id=\"total\"></b> 条已解析来源视频。一个视频可以出现在多个技术类型；分类来源和证据状态会明确显示。</p><p class=\"notice\">仅限本机私有查看。此目录不含视频、关键帧、ASR、动作片段或模型原始输出，也不得直接部署到 GitHub Pages。</p><div class=\"filters\"><select id=\"coach\"></select><select id=\"category\"></select></div><div id=\"stats\" class=\"stats\"></div><div id=\"categories\"></div><div id=\"results\"></div></main>
<script id=\"catalog-data\" type=\"application/json\">{payload}</script>
<script>
const data=JSON.parse(document.getElementById('catalog-data').textContent),coach=document.getElementById('coach'),category=document.getElementById('category'),stats=document.getElementById('stats'),categories=document.getElementById('categories'),results=document.getElementById('results');document.getElementById('total').textContent=data.total_video_count;
for(const item of data.coaches){{const o=document.createElement('option');o.value=item.coach_id;o.textContent=`${{item.coach_name}}（${{item.video_count}}）`;coach.append(o)}}
function selected(){{return data.coaches.find(item=>item.coach_id===coach.value)}}
function tag(text){{const e=document.createElement('span');e.textContent=text;return e}}
function render(){{const current=selected(),categoryId=category.value||'all';category.replaceChildren();for(const item of [{{id:'all',name:'全部技术类型',video_count:current.video_count}},...current.category_counts]){{const o=document.createElement('option');o.value=item.id;o.textContent=`${{item.name}}（${{item.video_count}}）`;if(item.id===categoryId)o.selected=true;category.append(o)}}const chosen=category.value;const rows=current.videos.filter(video=>chosen==='all'||video.categories.some(item=>item.id===chosen));stats.replaceChildren();for(const [name,count] of Object.entries(current.evidence_counts)){{const e=document.createElement('div');e.className='stat';e.textContent=`${{name}}：${{count}}`;stats.append(e)}}const total=document.createElement('div');total.className='stat';total.textContent=`当前显示：${{rows.length}} / ${{current.video_count}}`;stats.append(total);categories.replaceChildren();for(const item of current.category_counts){{const b=document.createElement('button');b.type='button';b.className=item.id===chosen?'active':'';b.textContent=`${{item.name}} · ${{item.video_count}}`;b.onclick=()=>{{category.value=item.id;render()}};categories.append(b)}}results.replaceChildren();if(!rows.length){{const e=document.createElement('div');e.className='empty';e.textContent='这个技术类型暂时没有视频。';results.append(e);return}}for(const video of rows){{const card=document.createElement('article'),title=document.createElement(video.url?'a':'h2');title.textContent=video.title;if(video.url){{title.href=video.url;title.target='_blank';title.rel='noreferrer'}}card.append(title);const meta=document.createElement('small');meta.textContent=`${{video.source_id}} · ${{video.duration_seconds??'未知'}} 秒 · ${{video.evidence_status}}`;card.append(meta);const tags=document.createElement('div');tags.className='tags';for(const item of video.categories)tags.append(tag(item.name));for(const item of video.techniques)if(item.label_zh)tags.append(tag(item.label_zh));card.append(tags);results.append(card)}}}}
coach.onchange=()=>render();category.onchange=()=>render();render();
</script>"""


def write_catalog(catalog: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "index.html").write_text(_render_html(catalog), encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=Path("."), help="project root")
    result.add_argument(
        "--output",
        type=Path,
        default=Path(".runtime/full-corpus-processing-v1/coach-video-catalog"),
        help="private output directory relative to --root",
    )
    return result


def main() -> None:
    args = parser().parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    catalog = build_catalog(root)
    write_catalog(catalog, output)
    print(f"built private catalogue: {catalog['total_video_count']} videos -> {output}")
    for coach in catalog["coaches"]:
        print(f"{coach['coach_name']}: {coach['video_count']} videos; {len(coach['category_counts'])} categories")


if __name__ == "__main__":
    main()
