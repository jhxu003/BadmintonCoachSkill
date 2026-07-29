#!/usr/bin/env python3
"""Build technical catalogues from the three coach corpora.

The default catalogue is private and retains richer routing provenance.  An
explicit --public-metadata-output produces a much smaller safe subset: public
title, original source link, duration, technical categories, and a visible
classification status.  Neither path downloads, transcodes, copies, or emits
video, frames, ASR, episodes, model output, or private runtime paths.
"""

from __future__ import annotations

import argparse
import html
import json
import re
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


@dataclass(frozen=True)
class CoachSystemRoute:
    system_id: str
    system_name: str
    topic_label: str
    pattern: str
    priority: int


COACH_SYSTEM_ROUTES: dict[str, tuple[CoachSystemRoute, ...]] = {
    "liu-hui": (
        # Only title evidence is used here.  A specific named stroke wins over
        # a generic word such as "发力"; the latter is a Liu Hui framework,
        # not a reason to relabel every smash or high-clear lesson as power.
        CoachSystemRoute("safety_equipment_and_load_selection", "安全、装备与负荷选择", "装备适配、伤痛或训练负荷", r"球拍.*(评测|测评|真假|对比|怎么选|选择|重量|平衡点|挥重|拉线|磅数|中杆|球线|型号|差价|品牌|打感|抗扭)|(?:平衡点|拉线|磅数|中杆|球线|3u|4u|5u|轻拍|重拍|护具|伤痛|伤病|疼痛|受伤|球鞋)", 320),
        CoachSystemRoute("backhand_and_rear_corner_choice", "反手与后场角落选择", "反手与被动后场处理", r"反手|反拍", 310),
        CoachSystemRoute("drop_slice_slide_variation", "吊球、劈吊与后场变化", "吊球、劈吊或滑板变化", r"轻吊|轻放|重劈|重切|劈吊|滑板|切吊|吊球|放网|勾球|劈杀|light drop|slice drop", 300),
        CoachSystemRoute("drive_receive_and_front_exchange", "平抽挡、接杀与前场交换", "平抽挡、发接发或接杀防守", r"平抽|抽挡|抽球|推球|挡球|接杀|接发|接发球|发球|发小球|发高远球|正手过渡|被动过渡|drive|receive", 290),
        CoachSystemRoute("footwork_arrival_recovery", "步法、到位与回收", "启动、步法、到位或回收", r"步法|步伐|启动步|并步|交叉步|蹬跨|上网步|后退步|移动|回位|中国跳|起跳步|懒腿|leg[ -]?lazy|footwork", 280),
        CoachSystemRoute("overhead_power_chain", "头顶发力链与拍侧结构", "跨高远与杀球的发力链", r"(?:高远球.*杀球|杀球.*高远球).*(?:发力|动作|技巧|原理)", 314),
        CoachSystemRoute("smash_variant_system", "杀球变体与进攻选择", "杀球、跳杀或突击", r"霸王杀|跳杀|重杀|点杀|杀球|扣杀|突击|smash", 270),
        CoachSystemRoute("rear_court_base_and_high_clear", "后场基础与高远球", "高远球、击球点或头顶基础", r"拉高远|高远球|后场高球|甜区|击球点|头顶|侧身击球|侧身总侧|高球|high[ -]?clear|overhead", 260),
        CoachSystemRoute("overhead_power_chain", "头顶发力链与拍侧结构", "框架、握拍与发力链", r"(?:左手|非持拍手).*(?:发力|作用|核心)", 315),
        CoachSystemRoute("overhead_power_chain", "头顶发力链与拍侧结构", "框架、握拍与发力链", r"框架|架拍|拍面|发力|内旋|鞭打|挥速|球速|握拍|手指|手腕|顶髋|转髋|核心|大臂|小臂|卸力|放松|掉肘|后仰|立腕|挥拍僵硬|动作僵硬|苍蝇拍|power|whip|rotation", 250),
        CoachSystemRoute("doubles_singles_tactics_and_match_transfer", "单双打战术与实战迁移", "单双打、球路与实战迁移", r"双打|单打|轮转|补位|战术|实战|连贯|球路|上场|match use", 240),
        CoachSystemRoute("student_fit_and_diagnosis", "学员匹配、诊断与训练路径", "学习路径、训练或综合答疑", r"直播|问答|q&a|新手|初学|入门|训练计划|训练方法|球感|学习顺序|learning order|live teaching|怎么练|打不到球|稳定性|动作太丑", 230),
    ),
    "li-yuxuan": (
        CoachSystemRoute("learner_fit", "学习路径与综合答疑", "直播、课程与学习路径", r"直播|问答|q&a", 330),
        CoachSystemRoute("equipment_safety", "装备成熟度与负荷安全", "装备适配、热身或训练负荷", r"(?:球拍|拍子).*(评测|测评|怎么选|选择|磅数|平衡点|挥重|拉线|中杆|型号|碳素|旗舰)|(?:选|选择).*(?:球拍|拍子)|(?:球拍磅数|平衡点|挥重|拉线|中杆|球线|球鞋|开箱测评|准备活动|拉伸|受伤|伤痛|疼痛|减肥|保持水平|碳素|旗舰)", 320),
        CoachSystemRoute("backhand_time_budget", "反手与时间预算", "反手处理与到位时间", r"反手|反拍", 310),
        CoachSystemRoute("serve_receive", "发接发与双打前两拍", "发球、接发或开局衔接", r"接发|接发球|发球|短球|前三拍", 300),
        CoachSystemRoute("match_transfer", "练习到实战的迁移", "对抗、防守、球路与实战迁移", r"杀球.*防守|防守.*杀球|接住.*进攻|被动过渡", 295),
        CoachSystemRoute("drop_drive", "吊球、平抽挡与快速交换", "吊球、网前控制或平抽挡", r"吊球|劈吊|滑板|切吊|切球|勾球|放网|搓球|平抽|平高球|抽球|抽挡|挡球|推球|封网|扑球|快球|挑球|假动作|切推|网前技术", 290),
        CoachSystemRoute("smash", "杀球与跳杀进阶", "杀球、跳杀或进攻", r"跳杀|起跳杀球|腾空杀球|杀球|扣杀|点杀|重杀|霸王杀|劈杀|杀得.*尖|杀的.*尖", 280),
        CoachSystemRoute("high_clear", "高远球与头顶击球", "高远球、头顶与后场击球", r"高远球|后场高球|高远发力|头顶.*(球|击球)|high[ -]?clear", 270),
        CoachSystemRoute("footwork", "启动、到位、落地与回收", "启动、步伐、到位或回收", r"步法|步伐|启动|后场步|上网步|前场步|弓箭步|蹬跨|后退步|移动|到位|回位|来不及|接不了球|半步|落地|压后场|后场两点", 260),
        CoachSystemRoute("release", "准备、肘部与释放链", "握拍、架拍、肘部与发力释放", r"非持拍手|握法|握拍|架拍|引拍|掉肘|顶肘|摆肘|手腕|手指|内旋|转髋|发不上力|发力|力量|爆发|鞭打|挥拍", 250),
        CoachSystemRoute("match_transfer", "练习到实战的迁移", "对抗、防守、球路与实战迁移", r"防守|接杀|单打|双打|混双|轮转|补位|战术|实战|比赛|对抗|套路|球路|意识|重复球|站位|压底线|反方向", 240),
        CoachSystemRoute("learner_fit", "学习路径与综合答疑", "直播、课程与学习路径", r"直播|问答|q&a|网课|课程|新手|初学|入门|训练计划|基本功|一致性|问题.*解决|世纪大难题", 230),
    ),
    "zheng-siwei": (
        CoachSystemRoute("defense_transition", "防守过渡与反击", "防守、过渡、卸力与反击", r"卸力.*挡网|挡卸力|卸力反击", 330),
        CoachSystemRoute("defense_transition", "防守过渡与反击", "防守、过渡、卸力与反击", r"正手.*(?:中半场|下手位|后半场)|借力.*对角|泄力.*平快", 329),
        CoachSystemRoute("pair_rotation_two_lanes", "双打轮转与两条通道", "混双轮转、后杀前封与下一拍", r"后杀前封|放网后.*站位", 328),
        # The seven public Zheng Siwei modules are deliberately retained.
        # Intermediate forehand/backhand and pressure-handling titles belong to
        # defense transition rather than being hidden under a generic reset.
        CoachSystemRoute("receive_opening_exchange", "接发与前两拍衔接", "接发、快推与前两拍衔接", r"接发|发接发|接发球|平抽|平快|抽挡|抽球|快推", 320),
        CoachSystemRoute("frontcourt_pressure", "网前压迫与封网", "网前控球、扑抹与封网", r"网前|搓球|勾球|勾对角|扑抹|扑球|反手抹球|抹腰|挡网|放网|封网|贴网", 310),
        CoachSystemRoute("defense_transition", "防守过渡与反击", "防守、过渡、卸力与反击", r"防守|接杀|泄力|卸力|被动球|反击|正手.*(?:中半场|下手位|后半场)|借力.*对角|反手底线|反手.*过渡|平高球|摆脱线路|被推压", 300),
        CoachSystemRoute("pair_rotation_two_lanes", "双打轮转与两条通道", "混双轮转、后杀前封与下一拍", r"混双|双打|轮转|男生.*女生|女生.*男生|后杀前封|下一拍", 290),
        CoachSystemRoute("rear_attack_continuity", "后场进攻与前后衔接", "后场进攻、到位与下一拍衔接", r"防偷后场|后场来不及退|后场突击步伐|后场步法|杀球|高远球|头顶|后场进攻|后场攻击|进攻方式|启动步|步伐|移动", 280),
        CoachSystemRoute("serve_opening", "发球与开局设置", "发球开局设置", r"发球", 270),
        CoachSystemRoute("reset_match_transfer", "重置、体能与比赛复盘", "体能、恢复与比赛复盘", r"体能|康复|热身|腰疼|膝盖|肩部|拉伸|训练日常|球路讲解|比赛|点评|评价|预测|q&a", 260),
    ),
}


COACH_SYSTEM_FALLBACKS: dict[str, CoachSystemRoute] = {
    "liu-hui": CoachSystemRoute("unresolved_title", "体系内待人工细分", "标题未能可靠指向一个刘辉体系模块", "", 0),
    "li-yuxuan": CoachSystemRoute("unresolved_title", "体系内待人工细分", "标题未能可靠指向一个李宇轩体系模块", "", 0),
    "zheng-siwei": CoachSystemRoute("unresolved_title", "体系内待人工细分", "标题未能可靠指向一个郑思维体系模块", "", 0),
}


COACH_SYSTEM_OUTSIDE_SCOPE: dict[str, CoachSystemRoute] = {
    coach_id: CoachSystemRoute(
        "outside_teaching_system",
        "体系外：公告／生活／产品信息",
        "标题不构成可路由的教学内容",
        "",
        0,
    )
    for coach_id in COACH_SYSTEM_ROUTES
}


def _is_outside_teaching_system(coach_id: str, title: str) -> bool:
    """Recognise announcements/lifestyle posts without treating them as drills.

    Product selection, injury prevention and course/stream Q&A remain in the
    coach systems.  This small gate is intentionally conservative: it prevents
    sales announcements and travel posts from contaminating a technical module,
    but never attempts to infer a module from missing evidence.
    """
    normalized = title.lower()
    if re.search(r"authorized.*seed|旅游|vlog|日常.*(?:分享|记录)|衣服.*(?:上架|拿下)|圣诞老人直播送|newest video is live|直播预告", normalized):
        return True
    if coach_id == "li-yuxuan" and re.search(r"(?:送|抽奖).*(?:球拍|礼物|东西)|(?:球拍|礼物|天斧\d+).*(?:怎么参加|抽奖)", normalized):
        teaching_signal = r"教学|技术|战术|步法|步伐|发力|反手|杀球|吊球|抽球|接发|防守|网前|球路"
        return not re.search(teaching_signal, normalized)
    return False


def route_coach_system(coach_id: str, title: str) -> tuple[CoachSystemRoute, str]:
    normalized = title.lower()
    if coach_id not in COACH_SYSTEM_ROUTES:
        raise ValueError(f"unknown coach system: {coach_id}")
    if _is_outside_teaching_system(coach_id, normalized):
        return COACH_SYSTEM_OUTSIDE_SCOPE[coach_id], "title_outside_system"
    for route in sorted(COACH_SYSTEM_ROUTES.get(coach_id, ()), key=lambda item: -item.priority):
        if re.search(route.pattern, normalized, flags=re.IGNORECASE):
            return route, "title_system_route"
    return COACH_SYSTEM_FALLBACKS[coach_id], "title_system_fallback"


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


def public_metadata_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    """Return title-routed coach-system metadata suitable for a static public index.

    Candidate ASR/VLM semantic windows are deliberately excluded from public
    category selection: they can locate a review interval, but they are not a
    reliable video-level syllabus label.  Each source therefore has one primary
    coach-system route based on its public title, or a transparent fallback.
    """
    coaches: list[dict[str, Any]] = []
    for coach in catalog.get("coaches", []):
        if not isinstance(coach, dict):
            raise ValueError("invalid private catalogue coach")
        videos: list[dict[str, Any]] = []
        for video in coach.get("videos", []):
            if not isinstance(video, dict):
                raise ValueError("invalid private catalogue video")
            url = str(video.get("url", "")).strip()
            if not url.startswith(("https://", "http://")):
                raise ValueError(f"public catalogue video has no public URL: {video.get('source_id')}")
            route, classification_status = route_coach_system(
                str(coach.get("coach_id", "")), str(video.get("title", ""))
            )
            videos.append(
                {
                    "source_id": str(video.get("source_id", "")),
                    "title": str(video.get("title", "")),
                    "url": url,
                    "duration_seconds": video.get("duration_seconds"),
                    "classification_status": classification_status,
                    "categories": [{"id": route.system_id, "name": route.system_name}],
                    "techniques": [{"action": route.system_id, "label_zh": route.topic_label}],
                }
            )
        category_names = {
            item["categories"][0]["id"]: item["categories"][0]["name"]
            for item in videos
        }
        category_counts = Counter(item["categories"][0]["id"] for item in videos)
        coaches.append(
            {
                "coach_id": str(coach.get("coach_id", "")),
                "coach_name": str(coach.get("coach_name", "")),
                "video_count": len(videos),
                "category_counts": [
                    {"id": category_id, "name": category_names[category_id], "video_count": count}
                    for category_id, count in sorted(
                        category_counts.items(),
                        key=lambda item: (-item[1], item[0]),
                    )
                ],
                "videos": videos,
            }
        )
    public_catalog = {
        "schema_version": "public-coach-video-catalog/v1",
        "generated_at": catalog.get("generated_at"),
        "publication_boundary": "metadata index only: no video, frames, clips, ASR, episode data, private paths, or model output",
        "total_video_count": sum(item["video_count"] for item in coaches),
        "coaches": coaches,
    }
    if public_catalog["total_video_count"] != catalog.get("total_video_count"):
        raise ValueError("public catalogue count differs from private catalogue")
    return public_catalog


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


def write_public_metadata_catalog(catalog: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(public_metadata_catalog(catalog), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=Path("."), help="project root")
    result.add_argument(
        "--output",
        type=Path,
        default=Path(".runtime/full-corpus-processing-v1/coach-video-catalog"),
        help="private output directory relative to --root",
    )
    result.add_argument(
        "--public-metadata-output",
        type=Path,
        help="owner-approved static JSON output; contains metadata only and no media",
    )
    return result


def main() -> None:
    args = parser().parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    catalog = build_catalog(root)
    write_catalog(catalog, output)
    if args.public_metadata_output:
        public_output = args.public_metadata_output
        if not public_output.is_absolute():
            public_output = root / public_output
        write_public_metadata_catalog(catalog, public_output)
        print(f"built public metadata catalogue -> {public_output}")
    print(f"built private catalogue: {catalog['total_video_count']} videos -> {output}")
    for coach in catalog["coaches"]:
        print(f"{coach['coach_name']}: {coach['video_count']} videos; {len(coach['category_counts'])} categories")


if __name__ == "__main__":
    main()
