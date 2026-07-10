from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat
import yaml


ROOT = Path(__file__).resolve().parents[1]

ACTION_STATES = {
    "airborne": 20,
    "arm_extended": 18,
    "arm_raised": 18,
    "lunge": 18,
    "torso_turned": 15,
    "single_leg_support": 12,
    "staggered_stance": 10,
    "wide_base": 8,
}
OVERHEAD_TOPICS = {
    "contact_point",
    "high_clear",
    "hip_rotation",
    "internal_rotation",
    "racket_preparation",
    "smash",
    "top_elbow",
    "wrist",
}
FOOTWORK_TOPICS = {"footwork"}
FAST_EXCHANGE_TOPICS = {"drive", "serve_receive", "doubles"}
PREVIEW_TOPICS = [
    "high_clear",
    "smash",
    "top_elbow",
    "hip_rotation",
    "internal_rotation",
    "footwork",
    "drop",
    "drive",
    "serve_receive",
    "doubles",
]
TOPIC_DISPLAY_NAMES = {
    "high_clear": "高远球 / High clear",
    "smash": "杀球 / Smash",
    "top_elbow": "顶肘 / Top elbow",
    "hip_rotation": "转髋 / Hip rotation",
    "internal_rotation": "内旋发力 / Internal rotation",
    "footwork": "步法 / Footwork",
    "drop": "吊球与变化 / Drop and variation",
    "drive": "平抽挡 / Drive",
    "serve_receive": "发接发 / Serve and receive",
    "doubles": "双打 / Doubles",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review ASR-guided keyframes and render private contact sheets."
    )
    parser.add_argument(
        "--manifest",
        default="data/corpus/video-visual-pipeline-manifest.yaml",
    )
    parser.add_argument(
        "--artifact-root",
        default="data/raw-private/video-corpus",
    )
    parser.add_argument(
        "--frame-root",
        action="append",
        help="Optional node-local root containing <job-id>/keyframes/*.jpg.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw-private/keyframe-review",
    )
    parser.add_argument("--max-per-window", type=int, default=3)
    parser.add_argument("--min-select-score", type=float, default=54.0)
    parser.add_argument("--duplicate-distance", type=int, default=5)
    parser.add_argument("--overview-per-decision", type=int, default=24)
    parser.add_argument("--selected-preview-count", type=int, default=60)
    parser.add_argument("--topic-preview-count", type=int, default=36)
    return parser.parse_args()


def resolve_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def image_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        width, height = image.size
        gray = image.convert("L").resize((256, 256))
        gray_stat = ImageStat.Stat(gray)
        edge_stat = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES))
        sharpness = float(edge_stat.var[0])
        luminance = float(gray_stat.mean[0])
        contrast = float(gray_stat.stddev[0])
        return {
            "image_width": width,
            "image_height": height,
            "sharpness": round(sharpness, 3),
            "luminance": round(luminance, 3),
            "contrast": round(contrast, 3),
            "perceptual_hash": difference_hash(image),
        }


def difference_hash(image: Image.Image, size: int = 8) -> str:
    gray = image.convert("L").resize((size + 1, size))
    pixels = list(gray.getdata())
    value = 0
    for row in range(size):
        offset = row * (size + 1)
        for column in range(size):
            left = pixels[offset + column]
            right = pixels[offset + column + 1]
            value = (value << 1) | int(right > left)
    return f"{value:0{size * size // 4}x}"


def hash_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def largest_person(pose: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    people = list(pose.get("people") or [])
    if not people:
        return None, 0

    def area(person: dict[str, Any]) -> float:
        box = person.get("bbox_xyxy") or [0, 0, 0, 0]
        if len(box) != 4:
            return 0.0
        return max(float(box[2]) - float(box[0]), 0.0) * max(
            float(box[3]) - float(box[1]), 0.0
        )

    return max(people, key=area), len(people)


def subject_metrics(
    pose_frame: dict[str, Any], image_width: int, image_height: int
) -> dict[str, Any]:
    person, count = largest_person(pose_frame)
    if person is None or image_width <= 0 or image_height <= 0:
        return {
            "pose_person_count": count,
            "subject_area_ratio": 0.0,
            "pose_mean_confidence": 0.0,
            "pose_keypoint_count": 0,
        }
    box = person.get("bbox_xyxy") or [0, 0, 0, 0]
    box_area = max(float(box[2]) - float(box[0]), 0.0) * max(
        float(box[3]) - float(box[1]), 0.0
    )
    return {
        "pose_person_count": count,
        "subject_area_ratio": round(box_area / (image_width * image_height), 5),
        "pose_mean_confidence": round(float(person.get("mean_confidence") or 0), 5),
        "pose_keypoint_count": int(person.get("keypoint_count") or 0),
    }


def score_frame(record: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    hard_rejections: list[str] = []
    score = 0.0

    luminance = float(record["luminance"])
    contrast = float(record["contrast"])
    sharpness = float(record["sharpness"])
    if luminance < 8 or luminance > 247 or contrast < 4:
        hard_rejections.append("blank_or_unusable_exposure")
    if 25 <= luminance <= 230:
        score += 5
        reasons.append("usable_exposure")
    if contrast >= 25:
        score += 6
        reasons.append("usable_contrast")
    elif contrast < 10:
        score -= 8
        reasons.append("low_contrast")
    sharpness_score = min(max((math.log1p(sharpness) - 2.5) * 3.0, 0.0), 10.0)
    score += sharpness_score
    if sharpness_score >= 6:
        reasons.append("clear_image")
    elif sharpness_score < 2:
        reasons.append("soft_image")

    if not record.get("person_visible"):
        hard_rejections.append("person_not_visible")
    else:
        score += 10
        reasons.append("person_visible")

    subject_ratio = float(record.get("subject_area_ratio") or 0)
    if subject_ratio >= 0.08:
        score += 12
        reasons.append("subject_large_enough")
    elif subject_ratio >= 0.03:
        score += 7
        reasons.append("subject_usable_scale")
    elif subject_ratio > 0:
        score -= 5
        reasons.append("subject_small")
    else:
        score -= 8
        reasons.append("pose_subject_missing")

    racket_visibility = record.get("racket_visibility")
    racket_position = record.get("racket_position")
    if racket_visibility == "visible":
        score += 10
        reasons.append("racket_visible")
        if racket_position == "above_shoulder":
            score += 8
            reasons.append("racket_above_shoulder")
        elif racket_position == "waist_to_shoulder":
            score += 4
        elif racket_position == "below_waist":
            score += 1
    else:
        score -= 8
        reasons.append("racket_not_visible")

    states = set(record.get("body_configuration") or [])
    action_values = [ACTION_STATES[state] for state in states if state in ACTION_STATES]
    if action_values:
        score += max(action_values)
        reasons.append("action_state:" + sorted(states & ACTION_STATES.keys())[0])
    elif "neutral_standing" in states:
        score -= 14
        reasons.append("neutral_standing")
    elif "unclear" in states or not states:
        score -= 8
        reasons.append("body_state_unclear")

    topics = set(record.get("topic_tags") or [])
    if topics & OVERHEAD_TOPICS and (
        racket_position == "above_shoulder"
        or bool(states & {"arm_raised", "arm_extended", "torso_turned", "airborne"})
    ):
        score += 9
        reasons.append("overhead_topic_visual_fit")
    if topics & FOOTWORK_TOPICS and bool(
        states & {"lunge", "single_leg_support", "staggered_stance", "wide_base", "airborne"}
    ):
        score += 9
        reasons.append("footwork_topic_visual_fit")
    if topics & FAST_EXCHANGE_TOPICS and racket_visibility == "visible":
        score += 4
        reasons.append("exchange_topic_visual_fit")
    if "doubles" in topics and int(record.get("pose_person_count") or 0) >= 2:
        score += 3
        reasons.append("multiple_players_for_doubles")

    if record.get("confidence") == "high":
        score += 4
    elif record.get("confidence") == "low":
        score -= 5
        reasons.append("low_vlm_confidence")

    limits = set(record.get("visibility_limits") or [])
    if "camera_crop" in limits:
        score -= 5
        reasons.append("camera_crop")
    if "racket_blurred" in limits:
        score -= 4
        reasons.append("racket_blurred")
    if "unclear" in limits:
        score -= 2

    return round(score, 3), reasons, sorted(set(hard_rejections))


def resolve_frame_path(
    frame: dict[str, Any], frame_roots: list[Path], job_id: str
) -> Path | None:
    candidates: list[Path] = []
    raw_path = frame.get("path")
    if raw_path:
        candidates.append(Path(raw_path))
    if raw_path:
        candidates.extend(
            frame_root / job_id / "keyframes" / Path(raw_path).name
            for frame_root in frame_roots
        )
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def frame_lookup(items: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("frame_id")): item
        for item in items
        if item.get("frame_id") is not None
    }


def build_inventory(
    manifest: dict[str, Any], artifact_root: Path, frame_roots: list[Path]
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for job in manifest.get("jobs", []):
        job_id = job["job_id"]
        job_dir = artifact_root / job_id
        keyframes = read_json(job_dir / "keyframes" / "manifest.json")
        vlm = read_json(job_dir / "vlm.json")
        pose = read_json(job_dir / "pose.json")
        vlm_by_id = frame_lookup(vlm.get("frames", []))
        pose_by_id = frame_lookup(pose.get("frames", []))
        planned_by_timestamp = {
            round(float(frame.get("timestamp_seconds") or 0), 3): frame
            for frame in job.get("planned_frames", [])
        }
        for frame in keyframes.get("frames", []):
            frame_id = str(frame.get("frame_id") or "")
            timestamp = round(float(frame.get("timestamp_seconds") or 0), 3)
            plan = planned_by_timestamp.get(timestamp, {})
            vlm_frame = vlm_by_id.get(frame_id, {})
            pose_frame = pose_by_id.get(frame_id, {})
            path = resolve_frame_path(frame, frame_roots, job_id)
            base = {
                "job_id": job_id,
                "source_id": job.get("source_id"),
                "title": job.get("title"),
                "frame_id": frame_id,
                "timestamp_seconds": timestamp,
                "source_window_id": frame.get("source_window_id")
                or plan.get("source_window_id"),
                "phase_sample": frame.get("phase_sample")
                or plan.get("phase_sample"),
                "topic_tags": frame.get("source_window_topic_tags")
                or plan.get("topic_tags", []),
                "frame_path": str(path) if path else None,
                "person_visible": bool(vlm_frame.get("person_visible")),
                "racket_visibility": vlm_frame.get("racket_visibility"),
                "racket_position": vlm_frame.get("racket_position"),
                "body_configuration": vlm_frame.get("body_configuration", []),
                "primary_subject_view": vlm_frame.get("primary_subject_view"),
                "visibility_limits": vlm_frame.get("visibility_limits", []),
                "confidence": vlm_frame.get("confidence"),
                "on_screen_text_present": vlm_frame.get("on_screen_text_present"),
                "decision": "unavailable",
                "selection_rank": None,
            }
            if path is None:
                base.update(
                    {
                        "score": None,
                        "reasons": ["frame_file_unavailable"],
                        "hard_rejections": ["frame_file_unavailable"],
                    }
                )
                records.append(base)
                continue
            try:
                metrics = image_metrics(path)
            except (OSError, ValueError):
                base.update(
                    {
                        "score": None,
                        "reasons": ["frame_decode_failed"],
                        "hard_rejections": ["frame_decode_failed"],
                    }
                )
                records.append(base)
                continue
            base.update(metrics)
            base["decision"] = "pending"
            base.update(
                subject_metrics(
                    pose_frame,
                    int(metrics["image_width"]),
                    int(metrics["image_height"]),
                )
            )
            score, reasons, hard_rejections = score_frame(base)
            base.update(
                {
                    "score": score,
                    "reasons": reasons,
                    "hard_rejections": hard_rejections,
                }
            )
            records.append(base)
    return records


def select_frames(
    records: list[dict[str, Any]],
    max_per_window: int,
    min_score: float,
    duplicate_distance: int,
) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("source_window_id") or record["job_id"])].append(record)

    for window_records in grouped.values():
        candidates = [
            record
            for record in window_records
            if record.get("score") is not None and not record.get("hard_rejections")
        ]
        candidates.sort(
            key=lambda item: (
                -float(item["score"]),
                float(item["timestamp_seconds"]),
            )
        )
        selected: list[dict[str, Any]] = []
        for record in candidates:
            if float(record["score"]) < min_score:
                record["decision"] = "rejected"
                record["reasons"].append("below_selection_threshold")
                continue
            duplicate_of = next(
                (
                    kept
                    for kept in selected
                    if hash_distance(
                        str(record["perceptual_hash"]),
                        str(kept["perceptual_hash"]),
                    )
                    <= duplicate_distance
                ),
                None,
            )
            if duplicate_of is not None:
                record["decision"] = "rejected"
                record["duplicate_of"] = duplicate_of["frame_id"]
                record["reasons"].append("near_duplicate_in_window")
                continue
            if len(selected) >= max(max_per_window, 0):
                record["decision"] = "rejected"
                record["reasons"].append("window_selection_limit")
                continue
            selected.append(record)
            record["decision"] = "selected"
            record["selection_rank"] = len(selected)
            record["reasons"].append("selected_distinct_teaching_frame")

        for record in window_records:
            if record["decision"] == "unavailable":
                continue
            if record.get("hard_rejections"):
                record["decision"] = "rejected"
                record["reasons"].extend(record["hard_rejections"])
            elif record["decision"] not in {"selected", "rejected"}:
                record["decision"] = "rejected"
                record["reasons"].append("not_selected")


def balanced_sample(
    records: list[dict[str, Any]], count: int, topics: list[str] | None = None
) -> list[dict[str, Any]]:
    candidates = records
    if topics:
        topic_set = set(topics)
        candidates = [
            record
            for record in records
            if topic_set & set(record.get("topic_tags") or [])
        ]
    candidates = sorted(
        candidates,
        key=lambda item: (
            -float(item.get("score") or -999),
            str(item.get("source_id")),
            float(item.get("timestamp_seconds") or 0),
        ),
    )
    chosen: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for record in candidates:
        source = str(record.get("source_id"))
        if source in seen_sources:
            continue
        chosen.append(record)
        seen_sources.add(source)
        if len(chosen) >= count:
            return chosen
    for record in candidates:
        if record in chosen:
            continue
        chosen.append(record)
        if len(chosen) >= count:
            break
    return chosen


def topic_preview_score(record: dict[str, Any], topic: str) -> float:
    score = float(record.get("score") or 0)
    states = set(record.get("body_configuration") or [])
    racket_position = record.get("racket_position")
    person_count = int(record.get("pose_person_count") or 0)
    overhead_states = {"arm_raised", "arm_extended", "torso_turned", "airborne"}
    movement_states = {
        "lunge",
        "single_leg_support",
        "staggered_stance",
        "wide_base",
        "airborne",
    }
    if topic in {"high_clear", "smash", "top_elbow", "hip_rotation", "internal_rotation", "drop"}:
        if states & overhead_states:
            score += 30
        if racket_position == "above_shoulder":
            score += 18
    elif topic == "footwork":
        if states & movement_states:
            score += 35
        if states == {"arm_raised"}:
            score -= 18
    elif topic == "drive":
        if racket_position == "waist_to_shoulder":
            score += 30
        if states & {"arm_extended", "lunge", "staggered_stance", "wide_base"}:
            score += 25
        if racket_position == "above_shoulder":
            score -= 28
    elif topic == "serve_receive":
        if racket_position in {"waist_to_shoulder", "below_waist"}:
            score += 28
        if states & {"lunge", "staggered_stance", "single_leg_support", "wide_base"}:
            score += 22
        if racket_position == "above_shoulder":
            score -= 25
    elif topic == "doubles":
        if person_count >= 2:
            score += 45
        if states & {"lunge", "staggered_stance", "wide_base", "arm_extended"}:
            score += 18
        if racket_position == "above_shoulder" and person_count < 2:
            score -= 15
    return score


def topic_visual_relevant(record: dict[str, Any], topic: str) -> bool:
    states = set(record.get("body_configuration") or [])
    racket_position = record.get("racket_position")
    person_count = int(record.get("pose_person_count") or 0)
    overhead_states = {"arm_raised", "arm_extended", "torso_turned", "airborne"}
    movement_states = {
        "lunge",
        "single_leg_support",
        "staggered_stance",
        "wide_base",
        "airborne",
    }
    if topic in {
        "high_clear",
        "smash",
        "top_elbow",
        "hip_rotation",
        "internal_rotation",
        "drop",
    }:
        return bool(states & overhead_states) or racket_position == "above_shoulder"
    if topic == "footwork":
        return bool(states & movement_states)
    if topic == "drive":
        return racket_position == "waist_to_shoulder" and bool(
            states & {"arm_extended", "lunge", "staggered_stance", "wide_base"}
        )
    if topic == "serve_receive":
        return racket_position in {"waist_to_shoulder", "below_waist"} and bool(
            states
            & {"lunge", "staggered_stance", "single_leg_support", "wide_base", "neutral_standing"}
        )
    if topic == "doubles":
        return person_count >= 2 or bool(
            states & {"lunge", "staggered_stance", "wide_base", "arm_extended"}
        )
    return True


def topic_sample(
    records: list[dict[str, Any]], topic: str, count: int
) -> list[dict[str, Any]]:
    candidates = [
        record
        for record in records
        if topic in set(record.get("topic_tags") or [])
        and topic_visual_relevant(record, topic)
    ]
    candidates.sort(
        key=lambda item: (
            -topic_preview_score(item, topic),
            -float(item.get("score") or 0),
            str(item.get("source_id")),
        )
    )
    chosen: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for record in candidates:
        source = str(record.get("source_id"))
        if source in seen_sources:
            continue
        chosen.append(record)
        seen_sources.add(source)
        if len(chosen) >= count:
            return chosen
    for record in candidates:
        if record in chosen:
            continue
        chosen.append(record)
        if len(chosen) >= count:
            break
    return chosen


def stratified_selected_sample(
    selected: list[dict[str, Any]], count: int
) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    chosen_ids: set[str] = set()
    per_topic = max(math.ceil(count / len(PREVIEW_TOPICS)), 1)
    for topic in PREVIEW_TOPICS:
        for record in topic_sample(selected, topic, per_topic):
            frame_id = str(record.get("frame_id"))
            if frame_id in chosen_ids:
                continue
            chosen.append(record)
            chosen_ids.add(frame_id)
            if len(chosen) >= count:
                return chosen
    for record in balanced_sample(selected, count):
        frame_id = str(record.get("frame_id"))
        if frame_id in chosen_ids:
            continue
        chosen.append(record)
        chosen_ids.add(frame_id)
        if len(chosen) >= count:
            break
    return chosen


def rejection_sample(records: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        reasons = record.get("reasons") or []
        category = next(
            (
                reason
                for reason in [
                    "neutral_standing",
                    "racket_not_visible",
                    "near_duplicate_in_window",
                    "camera_crop",
                    "below_selection_threshold",
                    "person_not_visible",
                ]
                if reason in reasons
            ),
            "other_rejection",
        )
        buckets[category].append(record)
    chosen: list[dict[str, Any]] = []
    bucket_names = sorted(buckets)
    while len(chosen) < count and bucket_names:
        remaining = []
        for name in bucket_names:
            bucket = buckets[name]
            if bucket:
                chosen.append(bucket.pop(0))
                if len(chosen) >= count:
                    break
            if bucket:
                remaining.append(name)
        bucket_names = remaining
    return chosen


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def concise_reasons(record: dict[str, Any]) -> str:
    preferred = [
        reason
        for reason in record.get("reasons", [])
        if reason
        not in {
            "usable_exposure",
            "usable_contrast",
            "person_visible",
            "clear_image",
            "racket_visible",
        }
    ]
    return ", ".join(preferred[-3:]) or "usable visible frame"


def render_contact_sheet(
    records: list[dict[str, Any]], output: Path, title: str, columns: int = 4
) -> None:
    if not records:
        return
    thumb_width = 320
    image_height = 200
    text_height = 104
    cell_height = image_height + text_height
    margin = 16
    header_height = 62
    rows = math.ceil(len(records) / columns)
    canvas = Image.new(
        "RGB",
        (columns * thumb_width + (columns + 1) * margin, header_height + rows * cell_height + margin),
        "#f4f5f7",
    )
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(26)
    text_font = load_font(15)
    small_font = load_font(13)
    draw.text((margin, 16), title, fill="#111827", font=title_font)
    for index, record in enumerate(records):
        row, column = divmod(index, columns)
        x = margin + column * (thumb_width + margin)
        y = header_height + row * cell_height
        path = Path(str(record["frame_path"]))
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            fitted = ImageOps.contain(image, (thumb_width, image_height))
        frame = Image.new("RGB", (thumb_width, image_height), "#111827")
        frame.paste(
            fitted,
            ((thumb_width - fitted.width) // 2, (image_height - fitted.height) // 2),
        )
        canvas.paste(frame, (x, y))
        decision = str(record["decision"])
        color = "#15803d" if decision == "selected" else "#b91c1c"
        draw.rectangle((x, y, x + thumb_width - 1, y + image_height - 1), outline=color, width=5)
        score = record.get("score")
        score_label = "NA" if score is None else f"{float(score):.1f}"
        source_label = str(record.get("source_id") or "")[-24:]
        topics = ",".join((record.get("topic_tags") or [])[:3])
        draw.text(
            (x + 4, y + image_height + 5),
            f"{decision.upper()} score={score_label} t={record['timestamp_seconds']}s",
            fill=color,
            font=text_font,
        )
        draw.text(
            (x + 4, y + image_height + 29),
            source_label,
            fill="#111827",
            font=small_font,
        )
        draw.text(
            (x + 4, y + image_height + 49),
            topics[:44],
            fill="#374151",
            font=small_font,
        )
        draw.text(
            (x + 4, y + image_height + 69),
            concise_reasons(record)[:54],
            fill="#4b5563",
            font=small_font,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=92, subsampling=0)


def render_final_topic_overview(
    selected: list[dict[str, Any]], output: Path, reviewed_count: int
) -> None:
    columns = 3
    thumb_width = 380
    image_height = 224
    text_height = 70
    topic_header_height = 46
    margin = 18
    page_header_height = 112
    cell_height = image_height + text_height
    rows = len(PREVIEW_TOPICS)
    width = columns * thumb_width + (columns + 1) * margin
    height = page_header_height + rows * (topic_header_height + cell_height) + margin
    canvas = Image.new("RGB", (width, height), "#f7f8fa")
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30)
    subtitle_font = load_font(17)
    topic_font = load_font(22)
    text_font = load_font(14)
    draw.text((margin, 14), "刘辉教学关键帧筛选预览", fill="#111827", font=title_font)
    draw.text(
        (margin, 61),
        f"Reviewed {reviewed_count} frames | Selected {len(selected)} | "
        f"Rejected {reviewed_count - len(selected)} | Green = retained teaching evidence",
        fill="#4b5563",
        font=subtitle_font,
    )
    y = page_header_height
    for topic in PREVIEW_TOPICS:
        draw.rectangle((0, y, width, y + topic_header_height), fill="#e5e7eb")
        draw.text(
            (margin, y + 8),
            TOPIC_DISPLAY_NAMES[topic],
            fill="#111827",
            font=topic_font,
        )
        topic_records = topic_sample(selected, topic, columns)
        for column, record in enumerate(topic_records):
            x = margin + column * (thumb_width + margin)
            image_y = y + topic_header_height
            path = Path(str(record["frame_path"]))
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                fitted = ImageOps.contain(image, (thumb_width, image_height))
            frame = Image.new("RGB", (thumb_width, image_height), "#111827")
            frame.paste(
                fitted,
                ((thumb_width - fitted.width) // 2, (image_height - fitted.height) // 2),
            )
            canvas.paste(frame, (x, image_y))
            draw.rectangle(
                (x, image_y, x + thumb_width - 1, image_y + image_height - 1),
                outline="#15803d",
                width=5,
            )
            source_label = str(record.get("source_id") or "")[-28:]
            draw.text(
                (x + 4, image_y + image_height + 5),
                f"score={float(record['score']):.1f}  t={record['timestamp_seconds']}s",
                fill="#15803d",
                font=text_font,
            )
            draw.text(
                (x + 4, image_y + image_height + 29),
                source_label,
                fill="#374151",
                font=text_font,
            )
        y += topic_header_height + cell_height
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=94, subsampling=0)


def copy_representative_frames(
    selected: list[dict[str, Any]], output_dir: Path
) -> None:
    target_dir = output_dir / "selected-frames"
    target_dir.mkdir(parents=True, exist_ok=True)
    copied_ids: set[str] = set()
    for topic in PREVIEW_TOPICS:
        for index, record in enumerate(topic_sample(selected, topic, 3), start=1):
            frame_id = str(record.get("frame_id"))
            if frame_id in copied_ids:
                continue
            source = Path(str(record["frame_path"]))
            timestamp = str(record["timestamp_seconds"]).replace(".", "p")
            target = target_dir / f"{topic}-{index:02d}-{frame_id}-{timestamp}s.jpg"
            shutil.copy2(source, target)
            copied_ids.add(frame_id)


def write_outputs(records: list[dict[str, Any]], output_dir: Path, args: argparse.Namespace) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = output_dir / "frame-inventory.jsonl"
    with inventory_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    fieldnames = [
        "source_id",
        "job_id",
        "frame_id",
        "timestamp_seconds",
        "source_window_id",
        "decision",
        "selection_rank",
        "score",
        "topic_tags",
        "body_configuration",
        "racket_visibility",
        "racket_position",
        "subject_area_ratio",
        "sharpness",
        "reasons",
    ]
    with (output_dir / "frame-inventory.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            for key in ["topic_tags", "body_configuration", "reasons"]:
                row[key] = "|".join(str(item) for item in row.get(key, []))
            writer.writerow(row)

    decision_counts = Counter(str(record["decision"]) for record in records)
    reason_counts = Counter(
        str(reason) for record in records for reason in record.get("reasons", [])
    )
    selected = [record for record in records if record["decision"] == "selected"]
    rejected = [
        record
        for record in records
        if record["decision"] == "rejected" and record.get("frame_path")
    ]
    summary = {
        "keyframe_review": {
            "planned_or_extracted_records": len(records),
            "decision_counts": dict(decision_counts),
            "selection_rate": round(len(selected) / max(len(records), 1), 5),
            "sources_with_selected_frames": len(
                {record["source_id"] for record in selected}
            ),
            "teaching_windows_with_selected_frames": len(
                {record["source_window_id"] for record in selected}
            ),
            "thresholds": {
                "max_per_window": args.max_per_window,
                "min_select_score": args.min_select_score,
                "duplicate_distance": args.duplicate_distance,
            },
            "top_reasons": dict(reason_counts.most_common(30)),
        }
    }
    with (output_dir / "selection-summary.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(summary, handle, sort_keys=False, allow_unicode=True)

    previews = output_dir / "previews"
    accepted_preview = stratified_selected_sample(
        selected, args.selected_preview_count
    )
    rejected_preview = rejection_sample(rejected, args.overview_per_decision)
    overview_selected = stratified_selected_sample(
        selected, args.overview_per_decision
    )
    render_contact_sheet(
        overview_selected + rejected_preview,
        previews / "keyframe-review-overview.jpg",
        "Keyframe review: selected (green) and rejected (red)",
    )
    render_contact_sheet(
        accepted_preview,
        previews / "keyframe-review-selected.jpg",
        "Representative selected teaching frames",
    )
    render_final_topic_overview(
        selected,
        previews / "keyframe-review-final.jpg",
        reviewed_count=len(records),
    )
    copy_representative_frames(selected, output_dir)
    for topic in PREVIEW_TOPICS:
        topic_records = topic_sample(selected, topic, args.topic_preview_count)
        render_contact_sheet(
            topic_records,
            previews / "topics" / f"{topic}.jpg",
            f"Selected teaching frames: {topic}",
        )


def main() -> None:
    args = parse_args()
    manifest = read_yaml(resolve_path(args.manifest))
    artifact_root = resolve_path(args.artifact_root)
    output_dir = resolve_path(args.output_dir)
    frame_roots = [Path(path) for path in (args.frame_root or [])]
    records = build_inventory(manifest, artifact_root, frame_roots)
    select_frames(
        records,
        max_per_window=args.max_per_window,
        min_score=args.min_select_score,
        duplicate_distance=args.duplicate_distance,
    )
    write_outputs(records, output_dir, args)
    counts = Counter(record["decision"] for record in records)
    print(f"records {len(records)}")
    for decision in ["selected", "rejected", "unavailable"]:
        print(f"{decision} {counts.get(decision, 0)}")
    print(f"output_dir {output_dir}")


if __name__ == "__main__":
    main()
