from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


KEYWORD_TOPICS = [
    ("student_fit", ["适合", "不适合", "新手", "小白", "业余", "学习顺序", "框架", "身体", "条件"]),
    ("diagnosis_flow", ["看一看", "先看", "问题", "原因", "为什么", "先不要", "到底"]),
    ("high_clear", ["高远", "后场", "到底线", "打不远"]),
    ("smash", ["杀球", "重杀", "点杀", "跳杀", "压不下去", "尖", "球速"]),
    ("racket_preparation", ["架拍", "引拍", "框架", "立腕", "拍头", "拍面"]),
    ("top_elbow", ["顶肘", "肘", "掉肘", "大臂", "小臂"]),
    ("hip_rotation", ["转髋", "顶髋", "蹬转", "腰腹", "胯", "髋", "蹬"]),
    ("internal_rotation", ["内旋", "旋转", "鞭打", "鞭甩", "小臂"]),
    ("wrist", ["手腕", "手指", "抓握", "握拍", "食指"]),
    ("contact_point", ["击球点", "点位", "高点", "身前", "身后", "靠前", "靠后"]),
    ("footwork", ["步伐", "步法", "启动", "回位", "被动", "马来步", "中国跳"]),
    ("drop", ["吊球", "劈吊", "滑板", "滑拍", "慢吊", "快吊"]),
    ("drive", ["平抽", "挡", "推球", "接杀", "中前场"]),
    ("serve_receive", ["发球", "接发", "接发球"]),
    ("doubles", ["双打", "轮转", "搭档", "封网"]),
    ("match_transfer", ["实战", "比赛", "多球", "连贯", "稳定", "熟练"]),
    ("training_plan", ["训练", "练", "组", "节奏", "慢动作", "分解"]),
    ("safety", ["疼", "伤", "肩", "腰", "膝", "脚踝"]),
    (
        "equipment",
        [
            "平衡点",
            "抗扭",
            "克重",
            "底胶",
            "中杆",
            "挥重",
            "磅数",
        ],
    ),
]

PROMOTION_TARGET_BY_TOPIC = [
    ("student_profiles", {"student_fit"}),
    ("diagnosis_flow", {"diagnosis_flow"}),
    ("footwork_rubric", {"footwork", "hip_rotation"}),
    ("drop_rubric", {"drop"}),
    ("smash_variant_rubric", {"smash"}),
    ("serve_receive_rubric", {"serve_receive"}),
    ("drive_rubric", {"drive"}),
    ("match_transfer_rubric", {"match_transfer"}),
    ("training_plans", {"training_plan"}),
    ("equipment_rubric", {"equipment"}),
    ("overhead_rubric", {"high_clear", "top_elbow", "contact_point"}),
    ("swing_rubric", {"internal_rotation", "wrist", "racket_preparation"}),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create public-safe timestamp candidate teaching windows from private ASR JSON. "
            "The output stores original summaries and topic tags, not raw transcript text."
        )
    )
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument(
        "--output",
        default="data/corpus/video-asr-teaching-windows-full.yaml",
    )
    parser.add_argument("--window-seconds", type=int, default=45)
    parser.add_argument("--min-score", type=int, default=2)
    parser.add_argument("--max-windows-per-video", type=int, default=8)
    parser.add_argument("--coach-name", default="Liu Hui")
    return parser.parse_args()


def load_jobs(paths: list[str]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    seen_job_ids: set[str] = set()
    for raw in paths:
        manifest = load_yaml(ROOT / raw)
        for job in manifest.get("jobs", []):
            if job["job_id"] in seen_job_ids:
                continue
            seen_job_ids.add(job["job_id"])
            jobs.append(job)
    return jobs


def topic_hits(text: str) -> Counter[str]:
    hits: Counter[str] = Counter()
    for topic, keywords in KEYWORD_TOPICS:
        for keyword in keywords:
            if keyword in text:
                hits[topic] += 1
    return hits


def merge_segments(segments: list[dict[str, Any]], window_seconds: int) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_start: float | None = None
    for segment in segments:
        start = float(segment.get("start", 0))
        if current_start is None:
            current_start = start
        if current and start - current_start >= window_seconds:
            windows.append({"start": current_start, "end": float(current[-1]["end"]), "segments": current})
            current = []
            current_start = start
        current.append(segment)
    if current and current_start is not None:
        windows.append({"start": current_start, "end": float(current[-1]["end"]), "segments": current})
    return windows


def clean_title(title: str) -> str:
    return re.sub(r"[！!。?？~～]+", "", title).strip()


def summarize_window(job: dict[str, Any], topics: list[str], start: int, end: int) -> dict[str, Any]:
    title = clean_title(job.get("title", "this public teaching video"))
    primary = topics[0] if topics else "badminton_teaching"
    focus = {
        "student_fit": "student-fit framework selection",
        "diagnosis_flow": "goal-first diagnosis and immediate retest",
        "high_clear": "overhead high-clear structure",
        "smash": "smash power or angle development",
        "racket_preparation": "racket-preparation frame control",
        "top_elbow": "top-elbow and upper-arm frame behavior",
        "hip_rotation": "foot-ground and hip-drive sequencing",
        "internal_rotation": "arm-chain release and internal-rotation proxy cues",
        "wrist": "wrist, grip, and hand-force transfer",
        "contact_point": "contact-window placement",
        "footwork": "movement-to-contact and recovery",
        "drop": "drop, slice, or slide-shot variation",
        "drive": "compact fast-exchange preparation",
        "serve_receive": "serve/receive first-two-shot preparation",
        "doubles": "doubles positioning and continuity",
        "match_transfer": "rally-pressure transfer",
        "training_plan": "staged practice progression",
        "safety": "load and injury-risk filtering",
        "equipment": "racket specification and player-fit selection",
    }.get(primary, "badminton technique diagnosis")
    return {
        "summary": (
            f"Between {start}s and {end}s, this public source segment is a candidate "
            f"for {focus} within the video topic '{title}'. The candidate is based on "
            "ASR topic signals and must be reviewed against timestamped video before promotion."
        ),
        "teaching_point_candidate": {
            "problem": (
                f"The learner or demonstration may be addressing {focus}, but the exact "
                "visible mechanism still needs timestamp review."
            ),
            "diagnosis_rule": (
                f"Use this window as a review target for {focus}; do not turn it into "
                "a firm coaching rule until the timestamped content is checked."
            ),
            "correction": (
                "Promote only an original, evidence-grounded correction after reviewing "
                "the matching ASR segment, keyframes, and visible action."
            ),
            "promotion_target": promotion_target(topics[0] if topics else ""),
        },
    }


def promotion_target(primary_topic: str) -> str:
    for target, target_topics in PROMOTION_TARGET_BY_TOPIC:
        if primary_topic in target_topics:
            return target
    return "review_queue"


def build_windows_for_job(job: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    asr_path = ROOT / job["private_paths"]["asr_json"]
    if not asr_path.exists():
        return []
    try:
        asr = json.loads(asr_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if asr.get("status") != "ok":
        return []
    merged = merge_segments(asr.get("segments", []), args.window_seconds)
    scored: list[tuple[int, dict[str, Any], list[str]]] = []
    title_hits = topic_hits(job.get("title", ""))
    for window in merged:
        text = " ".join(str(segment.get("text", "")) for segment in window["segments"])
        hits = topic_hits(text)
        title_score = min(sum(title_hits.values()), 2)
        score = sum(hits.values()) + title_score
        if score < args.min_score:
            continue
        ordered_topics = [topic for topic, _ in hits.most_common()]
        for topic, _ in title_hits.most_common():
            if topic not in ordered_topics:
                ordered_topics.append(topic)
        topics = ordered_topics or [topic for topic, _ in title_hits.most_common()]
        scored.append((score, window, topics))
    scored.sort(key=lambda item: (-item[0], item[1]["start"]))

    selected: list[dict[str, Any]] = []
    for index, (_, window, topics) in enumerate(scored[: args.max_windows_per_video], start=1):
        start = int(round(float(window["start"])))
        end = int(round(float(window["end"])))
        summary = summarize_window(job, topics, start, end)
        selected.append(
            {
                "window_id": f"{job['job_id']}-w{index:03d}",
                "source_id": job["source_id"],
                "evidence_id": f"{job['job_id']}-seg-001",
                "start_seconds": start,
                "end_seconds": end,
                "topic_tags": topics[:6],
                "evidence_level": "content_model_candidate",
                "review_status": "pending_human_review",
                **summary,
            }
        )
    selected.sort(key=lambda item: (item["source_id"], item["start_seconds"]))
    return selected


def coach_scope(coach_name: str) -> list[str]:
    return [
        (
            "Machine-generated public-safe ASR teaching-window candidates for "
            f"indexed public {coach_name} videos."
        ),
        "Raw ASR segments stay private; this file contains original summaries only.",
        "Every candidate requires human timestamp review before skill promotion.",
    ]


def main() -> None:
    args = parse_args()
    jobs = load_jobs(args.manifest)
    windows: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    for job in jobs:
        job_windows = build_windows_for_job(job, args)
        windows.extend(job_windows)
        if job_windows:
            source_counts[job["source_id"]] += len(job_windows)
    report = {
        "review_run": {
            "run_id": f"video_asr_teaching_windows_full_{date.today().strftime('%Y%m%d')}",
            "created_at": date.today().isoformat(),
            "scope": coach_scope(args.coach_name),
            "generation_method": {
                "type": "deterministic_topic_windowing",
                "window_seconds": args.window_seconds,
                "min_score": args.min_score,
                "max_windows_per_video": args.max_windows_per_video,
            },
            "summary": {
                "manifests": args.manifest,
                "jobs_scanned": len(jobs),
                "sources_with_windows": len(source_counts),
                "windows": len(windows),
            },
        },
        "windows": windows,
    }
    write_yaml(ROOT / args.output, report)
    print(f"wrote {args.output}")
    print(f"jobs_scanned {len(jobs)}")
    print(f"sources_with_windows {len(source_counts)}")
    print(f"windows {len(windows)}")


if __name__ == "__main__":
    main()
