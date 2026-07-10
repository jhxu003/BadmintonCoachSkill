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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create public-safe visual evidence summaries from private VLM artifacts."
    )
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument(
        "--output",
        default="data/corpus/video-visual-evidence-summary.yaml",
    )
    return parser.parse_args()


def load_jobs(paths: list[str]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_path in paths:
        manifest = load_yaml(ROOT / raw_path)
        for job in manifest.get("jobs", []):
            if job["job_id"] in seen:
                continue
            seen.add(job["job_id"])
            jobs.append(job)
    return jobs


def count_visible_lines(summary: str, label: str) -> int:
    count = 0
    for line in summary.splitlines():
        if label.lower() not in line.lower():
            continue
        if "not visible" in line.lower() or "no stroke action" in line.lower():
            continue
        count += 1
    return count


def parse_structured_summary(summary: str) -> dict[str, Any] | None:
    text = summary.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def visible_value(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized not in {"", "null", "none", "not visible", "unknown"}
    return True


def load_vlm(job: dict[str, Any]) -> dict[str, Any] | None:
    path = ROOT / job["private_paths"]["vlm_json"]
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return (
        data
        if data.get("status") == "ok" and data.get("artifact_version") == 4
        else None
    )


def public_model_name(raw_name: Any) -> str:
    name = str(raw_name or "unknown")
    lowered = name.lower()
    if "qwen3-vl-8b" in lowered or "qwen3vl8b" in lowered:
        return "Qwen3-VL-8B-Instruct"
    if "qwen25vl3b" in lowered or "qwen2.5-vl-3b" in lowered:
        return "Qwen2.5-VL-3B-compatible"
    if "/" in name:
        return Path(name).name
    return name


def public_visible_observation(frame: dict[str, Any]) -> dict[str, Any]:
    return {
        "frame_id": str(frame.get("frame_id") or ""),
        "timestamp_seconds": int(round(float(frame.get("timestamp_seconds") or 0))),
        "person_visible": frame.get("person_visible") is True,
        "racket_visibility": str(frame.get("racket_visibility") or "unknown"),
        "racket_position": str(frame.get("racket_position") or "unknown"),
        "primary_subject_view": str(frame.get("primary_subject_view") or "unknown"),
        "body_configuration": [
            str(item) for item in frame.get("body_configuration", [])
        ],
        "on_screen_text_present": frame.get("on_screen_text_present") is True,
        "visibility_limits": [str(item) for item in frame.get("visibility_limits", [])],
        "confidence": str(frame.get("confidence") or "unknown"),
    }


def summarize(job: dict[str, Any], vlm: dict[str, Any]) -> dict[str, Any]:
    raw_summary = str(vlm.get("summary", ""))
    timestamps = [int(round(float(value))) for value in vlm.get("timestamps_seconds", [])]
    artifact_frames = vlm.get("frames", [])
    structured = parse_structured_summary(raw_summary)
    structured_frames = artifact_frames if isinstance(artifact_frames, list) else []
    if not structured_frames:
        structured_frames = structured.get("frames", []) if structured else []
    if not isinstance(structured_frames, list):
        structured_frames = []
    if structured_frames and int(vlm.get("artifact_version") or 0) >= 3:
        body_counts: Counter[str] = Counter()
        for frame in structured_frames:
            body = frame.get("body_configuration", [])
            if isinstance(body, list):
                body_counts.update(str(item) for item in body)
        visible_signals = {
            "person_visible_frames": sum(
                frame.get("person_visible") is True for frame in structured_frames
            ),
            "racket_visible_frames": sum(
                frame.get("racket_visibility") == "visible" for frame in structured_frames
            ),
            "racket_above_shoulder_frames": sum(
                frame.get("racket_position") == "above_shoulder"
                for frame in structured_frames
            ),
            "lunge_frames": body_counts["lunge"],
            "single_leg_support_frames": body_counts["single_leg_support"],
            "airborne_frames": body_counts["airborne"],
            "torso_turned_frames": body_counts["torso_turned"],
            "arm_raised_frames": body_counts["arm_raised"],
            "arm_extended_frames": body_counts["arm_extended"],
            "frames_with_on_screen_text_detected": sum(
                frame.get("on_screen_text_present") is True for frame in structured_frames
            ),
            "frames_with_visibility_limits": sum(
                bool(frame.get("visibility_limits")) for frame in structured_frames
            ),
            "low_confidence_frames": sum(
                frame.get("confidence") == "low" for frame in structured_frames
            ),
        }
    elif structured_frames:
        visible_signals = {
            "player_position_descriptions": sum(
                visible_value(frame.get("player_position")) for frame in structured_frames
            ),
            "racket_preparation_descriptions": sum(
                visible_value(frame.get("racket_preparation")) for frame in structured_frames
            ),
            "contact_or_precontact_descriptions": sum(
                visible_value(frame.get("contact_phase")) for frame in structured_frames
            ),
            "lower_body_descriptions": sum(
                visible_value(frame.get("lower_body_orientation"))
                for frame in structured_frames
            ),
            "recovery_descriptions": sum(
                visible_value(frame.get("recovery_state")) for frame in structured_frames
            ),
            "frames_with_on_screen_text_detected": sum(
                frame.get("on_screen_text_present") is True for frame in structured_frames
            ),
            "explicit_no_stroke_action_mentions": len(
                re.findall(r"no stroke action is visible", raw_summary, flags=re.IGNORECASE)
            ),
        }
    else:
        visible_signals = {
            "player_position_descriptions": count_visible_lines(raw_summary, "Player Position"),
            "racket_preparation_descriptions": count_visible_lines(raw_summary, "Racket Preparation"),
            "contact_or_precontact_descriptions": count_visible_lines(
                raw_summary, "Contact or Pre-Contact Frame"
            ),
            "lower_body_descriptions": count_visible_lines(raw_summary, "Lower-Body Orientation"),
            "recovery_descriptions": count_visible_lines(raw_summary, "Recovery State"),
            "frames_with_on_screen_text_detected": sum(
                1
                for line in raw_summary.splitlines()
                if "On-Screen Teaching Text" in line and "not visible" not in line.lower()
            ),
            "explicit_no_stroke_action_mentions": len(
                re.findall(r"no stroke action is visible", raw_summary, flags=re.IGNORECASE)
            ),
        }
    return {
        "job_id": job["job_id"],
        "source_id": job["source_id"],
        "title": job["title"],
        "platform": job["platform"],
        "topic_tags": job.get("priority_topics", []),
        "model": public_model_name(vlm.get("model")),
        "reviewed_frame_count": int(vlm.get("frame_count") or len(timestamps)),
        "timestamps_seconds": timestamps,
        "structured_output_parsed": bool(structured_frames),
        "structured_frame_count": len(structured_frames),
        "sequence_observation_count": 0,
        "visible_signal_counts": visible_signals,
        "visible_observation_refs": [
            public_visible_observation(frame) for frame in structured_frames
        ],
        "evidence_level": "visual_model_structured_candidate_public_safe",
        "review_status": "schema_validated_model_output",
        "human_review_status": "not_human_reviewed",
        "summary": (
            "Private VLM keyframe output was reduced to public-safe timestamped visibility fields "
            "and aggregate counts. Raw model text, on-screen text, frames, and media remain private."
        ),
        "allowed_use": (
            "Use to identify timestamps where visible stance, arm, torso, racket-position, or visibility "
            "conditions should receive human frame review."
        ),
        "blocked_use": (
            "Do not treat sparse still-frame counts as proof of stroke phase, contact, motion direction, "
            "top elbow, hip timing, internal rotation, racket face, force, or coaching intent."
        ),
    }


def main() -> None:
    args = parse_args()
    jobs = load_jobs(args.manifest)
    sources: list[dict[str, Any]] = []
    topic_counts: Counter[str] = Counter()
    visible_signal_totals: Counter[str] = Counter()
    total_frames = 0
    for job in jobs:
        vlm = load_vlm(job)
        if not vlm:
            continue
        item = summarize(job, vlm)
        sources.append(item)
        total_frames += item["reviewed_frame_count"]
        topic_counts.update(item["topic_tags"])
        visible_signal_totals.update(item["visible_signal_counts"])

    output = {
        "visual_summary_run": {
            "run_id": f"visual_evidence_summary_{date.today().strftime('%Y%m%d')}",
            "created_at": date.today().isoformat(),
            "scope": [
                "Validated private VLM v4 still-frame outputs for indexed non-YouTube sources.",
                "Only public-safe counts, timestamps, and original evidence limits are emitted.",
                "Raw frames, model text, and detected on-screen text remain private.",
            ],
            "summary": {
                "manifest_jobs_scanned": len(jobs),
                "sources_with_ok_vlm": len(sources),
                "reviewed_keyframes": total_frames,
                "topic_source_counts": dict(topic_counts.most_common()),
                "visible_signal_totals": dict(visible_signal_totals),
            },
            "evidence_contract": {
                "evidence_level": "visual_model_structured_candidate_public_safe",
                "review_status": "schema_validated_model_output",
                "human_review_required_for_rule_promotion": True,
            },
        },
        "sources": sources,
    }
    write_yaml(ROOT / args.output, output)
    print(f"wrote {args.output}")
    print(f"sources_with_ok_vlm {len(sources)}")
    print(f"reviewed_keyframes {total_frames}")


if __name__ == "__main__":
    main()
