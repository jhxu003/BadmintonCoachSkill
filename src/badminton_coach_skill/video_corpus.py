from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from badminton_coach_skill.source_index import read_source_index


CORE_TOPIC_QUERIES = [
    ("smash", ["smash", "杀球", "重杀", "点杀", "跳杀"]),
    ("high_clear", ["high_clear", "高远球", "正手发"]),
    ("rear_footwork", ["rear_footwork", "footwork", "后场", "启动", "步伐"]),
    ("top_elbow", ["top_elbow", "顶肘", "架拍", "框架"]),
    ("hip_rotation", ["hip", "转髋", "蹬转", "身体带动"]),
    ("internal_rotation", ["internal_rotation", "内旋", "鞭打", "小臂"]),
    ("power_framework", ["power_framework", "发力", "框架", "挥速"]),
    ("student_fit", ["learning_order", "顺序", "新手", "小白", "业余", "适合"]),
    ("match_transfer", ["match_transfer", "实战", "熟练", "打不出来"]),
]


PUBLIC_EVIDENCE_HEADER = [
    "evidence_id",
    "source_id",
    "start_seconds",
    "end_seconds",
    "topic_tags",
    "evidence_level",
    "review_status",
    "promotion_target",
]


@dataclass(frozen=True)
class SelectedSource:
    source: dict[str, str]
    priority_topics: list[str]
    score: int


def split_tags(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _haystack(row: dict[str, str]) -> str:
    parts = [
        row.get("source_id", ""),
        row.get("title", ""),
        row.get("topic_tags", ""),
        row.get("stroke_tags", ""),
        row.get("notes", ""),
    ]
    return " ".join(parts).lower()


def matched_priority_topics(row: dict[str, str]) -> list[str]:
    haystack = _haystack(row)
    matched: list[str] = []
    for topic, needles in CORE_TOPIC_QUERIES:
        if any(needle.lower() in haystack for needle in needles):
            matched.append(topic)
    return matched


def score_source(row: dict[str, str]) -> SelectedSource | None:
    if row.get("source_type") != "video":
        return None
    if row.get("access_type") != "public":
        return None
    if row.get("platform") != "Bilibili":
        return None
    if row.get("usability") not in {"usable", "candidate"}:
        return None

    topics = matched_priority_topics(row)
    if not topics:
        return None

    score = len(topics) * 10
    if row.get("authorization_status") == "authorized":
        score += 8
    elif row.get("authorization_status") == "public":
        score += 3
    if row.get("usability") == "usable":
        score += 4
    if "season_id=" in row.get("notes", ""):
        score += 2
    if row.get("published_at") and row.get("published_at") != "unknown":
        score += 1
    return SelectedSource(source=row, priority_topics=topics, score=score)


def select_pilot_sources(source_index_path: Path, limit: int = 30) -> list[SelectedSource]:
    rows = read_source_index(source_index_path)
    selected: list[SelectedSource] = []
    seen_urls: set[str] = set()
    topic_counts: dict[str, int] = {topic: 0 for topic, _ in CORE_TOPIC_QUERIES}

    candidates = [item for row in rows if (item := score_source(row))]
    candidates.sort(
        key=lambda item: (
            -item.score,
            item.source.get("published_at", ""),
            item.source["source_id"],
        )
    )

    # First pass favors broad Liu Hui system coverage.
    for candidate in candidates:
        url = candidate.source["url"]
        if url in seen_urls:
            continue
        if any(topic_counts[topic] < 3 for topic in candidate.priority_topics):
            selected.append(candidate)
            seen_urls.add(url)
            for topic in candidate.priority_topics:
                topic_counts[topic] += 1
        if len(selected) >= limit:
            return selected

    # Second pass fills remaining slots by score.
    for candidate in candidates:
        url = candidate.source["url"]
        if url in seen_urls:
            continue
        selected.append(candidate)
        seen_urls.add(url)
        if len(selected) >= limit:
            break
    return selected


def build_processing_job(
    selected: SelectedSource,
    index: int,
    private_root: str = "data/raw-private/video-corpus",
) -> dict[str, Any]:
    row = selected.source
    job_id = f"pilot-{index:03d}-{row['source_id'].lower()}"
    private_dir = f"{private_root}/{job_id}"
    public_evidence_path = f"data/corpus/video-evidence/{job_id}.yaml"
    return {
        "job_id": job_id,
        "source_id": row["source_id"],
        "title": row["title"],
        "platform": row["platform"],
        "url": row["url"],
        "published_at": row["published_at"],
        "access_type": row["access_type"],
        "authorization_status": row["authorization_status"],
        "source_type": row["source_type"],
        "priority_topics": selected.priority_topics,
        "topic_tags": split_tags(row["topic_tags"]),
        "stroke_tags": split_tags(row["stroke_tags"]),
        "selection_score": selected.score,
        "processing_status": "pending",
        "review_status": "not_started",
        "private_paths": {
            "job_dir": private_dir,
            "metadata_json": f"{private_dir}/metadata.json",
            "video_file": f"{private_dir}/source_video",
            "audio_file": f"{private_dir}/audio.m4a",
            "keyframes_dir": f"{private_dir}/keyframes",
            "asr_json": f"{private_dir}/asr.json",
            "ocr_json": f"{private_dir}/ocr.json",
            "vlm_json": f"{private_dir}/vlm.json",
            "pose_json": f"{private_dir}/pose.json",
            "run_log": f"{private_dir}/run.log",
        },
        "public_outputs": {
            "timestamp_evidence": public_evidence_path,
        },
        "model_plan": {
            "asr": "faster-whisper:large-v3-turbo-or-large-v3",
            "ocr": "PaddleOCR",
            "vlm": "Qwen2.5-VL-or-Qwen3-VL",
            "pose": "MMPose/RTMPose",
        },
        "promotion_policy": (
            "Only reviewed timestamp evidence may become source_backed skill rules. "
            "Title-only fallback evidence remains needs_content_model_review."
        ),
    }


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_evidence_index(path: Path, evidence_files: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            delimiter="\t",
            fieldnames=PUBLIC_EVIDENCE_HEADER,
            lineterminator="\n",
        )
        writer.writeheader()
        for evidence_file in evidence_files:
            data = load_yaml(evidence_file)
            for segment in data.get("segments", []):
                writer.writerow(
                    {
                        "evidence_id": segment["evidence_id"],
                        "source_id": data["source_id"],
                        "start_seconds": segment.get("start_seconds", ""),
                        "end_seconds": segment.get("end_seconds", ""),
                        "topic_tags": ",".join(segment.get("topic_tags", [])),
                        "evidence_level": segment.get("evidence_level", ""),
                        "review_status": segment.get("review_status", ""),
                        "promotion_target": segment.get("promotion_target", ""),
                    }
                )
