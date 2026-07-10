from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402
from build_asr_teaching_windows import promotion_target, topic_hits  # noqa: E402


VISUAL_REQUIRED_TOPICS = {
    "high_clear",
    "smash",
    "racket_preparation",
    "top_elbow",
    "hip_rotation",
    "internal_rotation",
    "wrist",
    "contact_point",
    "footwork",
    "drop",
    "drive",
    "serve_receive",
    "doubles",
}

TOPIC_FOCUS = {
    "student_fit": "student-fit framework selection",
    "diagnosis_flow": "diagnosis order and retest logic",
    "high_clear": "high-clear structure and power transfer",
    "smash": "smash framework, power, or angle",
    "racket_preparation": "racket preparation and frame organization",
    "top_elbow": "upper-arm and elbow sequencing",
    "hip_rotation": "foot-ground, hip, and trunk contribution",
    "internal_rotation": "arm-chain release and internal-rotation proxy cues",
    "wrist": "grip, finger, and wrist force transfer",
    "contact_point": "contact-window placement",
    "footwork": "movement-to-contact and recovery",
    "drop": "drop, slice, and slide-shot variation",
    "drive": "compact drive and fast-exchange preparation",
    "serve_receive": "serve/receive and first-two-shot preparation",
    "doubles": "doubles positioning and continuity",
    "match_transfer": "transfer from drill form to rally pressure",
    "training_plan": "staged training progression",
    "safety": "load, pain, and injury-risk filtering",
}

DIAGNOSTIC_USE = {
    "student_fit": "Use to select a learner path before choosing isolated technical cues.",
    "diagnosis_flow": "Use to order observations, identify the first failed layer, and define a retest.",
    "high_clear": "Use to review arrival, contact, racket-side frame, release, and clear outcome.",
    "smash": "Use to distinguish smash intent, prerequisites, contact, release, and recovery cost.",
    "racket_preparation": "Use to request visible racket preparation and pre-contact frame evidence.",
    "top_elbow": "Use only as an elbow-sequence review target; visible frames are required for diagnosis.",
    "hip_rotation": "Use only as a hip/trunk timing review target; visible full-body frames are required.",
    "internal_rotation": "Use only for proxy review; true shoulder rotation cannot be established by ASR.",
    "wrist": "Use to separate hand-force transfer from early wrist-dominant compensation.",
    "contact_point": "Use to request side-view or diagonal evidence of the playable contact window.",
    "footwork": "Use to review start, first step, arrival, hit, exit, and next-shot recovery.",
    "drop": "Use to identify the intended drop variant before evaluating geometry or disguise.",
    "drive": "Use to review spacing, preparation size, face stability, and second-shot readiness.",
    "serve_receive": "Use to review ready position, first movement, contact choice, and second-shot recovery.",
    "doubles": "Use only with rally and partner context; an isolated stroke is insufficient.",
    "match_transfer": "Use to define a pressure retest instead of adding technique from drill-only evidence.",
    "training_plan": "Use to choose one priority, one drill progression, and one measurable retest.",
    "safety": "Use to reduce load or stop progression when pain or movement risk is present.",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Review private ASR segments behind public timestamp candidates and emit "
            "public-safe original summaries without transcript text."
        )
    )
    parser.add_argument(
        "--windows",
        default="data/corpus/video-asr-teaching-windows-full.yaml",
    )
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument(
        "--output",
        default="data/corpus/video-asr-timestamp-review.yaml",
    )
    return parser.parse_args()


def load_jobs(paths: list[str]) -> dict[str, dict[str, Any]]:
    jobs: dict[str, dict[str, Any]] = {}
    for raw_path in paths:
        manifest = load_yaml(ROOT / raw_path)
        for job in manifest.get("jobs", []):
            jobs[job["job_id"]] = job
    return jobs


def job_id_from_window(window_id: str) -> str:
    return window_id.rsplit("-w", 1)[0]


def load_private_asr(job: dict[str, Any]) -> dict[str, Any] | None:
    path = ROOT / job["private_paths"]["asr_json"]
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if data.get("status") == "ok" else None


def overlapping_segments(
    segments: list[dict[str, Any]], start_seconds: float, end_seconds: float
) -> list[dict[str, Any]]:
    return [
        segment
        for segment in segments
        if float(segment.get("end", 0)) >= start_seconds
        and float(segment.get("start", 0)) <= end_seconds
    ]


def ordered_topics(
    hits: Counter[str], candidate_topics: list[str]
) -> list[str]:
    topics = [topic for topic, _ in hits.most_common()]
    for topic in candidate_topics:
        if topic not in topics:
            topics.append(topic)
    return topics


def review_window(
    window: dict[str, Any], job: dict[str, Any], asr: dict[str, Any]
) -> dict[str, Any]:
    start_seconds = float(window.get("start_seconds") or 0)
    end_seconds = float(window.get("end_seconds") or start_seconds)
    segments = overlapping_segments(asr.get("segments", []), start_seconds, end_seconds)
    text = " ".join(str(segment.get("text", "")) for segment in segments)
    hits = topic_hits(text)
    topics = ordered_topics(hits, list(window.get("topic_tags", [])))
    primary_topic = topics[0] if topics else "diagnosis_flow"
    focus = TOPIC_FOCUS.get(primary_topic, "badminton coaching diagnosis")
    visual_required = bool(set(topics) & VISUAL_REQUIRED_TOPICS)
    matched_topics = [topic for topic, count in hits.most_common() if count > 0]
    signal_status = (
        "asr_topic_signal_confirmed"
        if matched_topics
        else "timestamp_has_asr_but_topic_depends_on_public_title"
    )
    return {
        "window_id": window["window_id"],
        "job_id": job["job_id"],
        "source_id": job["source_id"],
        "platform": job["platform"],
        "source_title": job["title"],
        "start_seconds": int(round(start_seconds)),
        "end_seconds": int(round(end_seconds)),
        "reviewed_asr_segment_count": len(segments),
        "topic_tags": topics[:8],
        "asr_matched_topics": matched_topics[:8],
        "topic_signal_counts": {topic: hits[topic] for topic in matched_topics[:8]},
        "signal_status": signal_status,
        "evidence_level": "asr_timestamp_reviewed_public_safe",
        "review_status": "agent_asr_timestamp_reviewed",
        "human_review_status": "not_human_reviewed",
        "summary": (
            f"The private ASR interval at {int(round(start_seconds))}-"
            f"{int(round(end_seconds))}s was reviewed for topic signals. It supports "
            f"using this timestamp as a public-safe index for {focus}, without exposing "
            "or reconstructing transcript text."
        ),
        "diagnostic_use": DIAGNOSTIC_USE.get(
            primary_topic,
            "Use as a timestamped review target and keep the final diagnosis tied to visible evidence.",
        ),
        "promotion_target": window.get("teaching_point_candidate", {}).get(
            "promotion_target", promotion_target(primary_topic)
        ),
        "visual_review_required": visual_required,
        "boundary": (
            "This is an agent-reviewed ASR timestamp summary, not a human coach review, "
            "not a quote, and not visual proof of biomechanics."
        ),
    }


def main() -> None:
    args = parse_args()
    candidates = load_yaml(ROOT / args.windows).get("windows", [])
    jobs = load_jobs(args.manifest)
    asr_cache: dict[str, dict[str, Any] | None] = {}
    reviewed: list[dict[str, Any]] = []
    missing_job_ids: set[str] = set()
    missing_asr_job_ids: set[str] = set()
    topic_counts: Counter[str] = Counter()
    platform_counts: Counter[str] = Counter()
    signal_status_counts: Counter[str] = Counter()
    source_ids: set[str] = set()
    visual_required_count = 0

    for window in candidates:
        job_id = job_id_from_window(window["window_id"])
        job = jobs.get(job_id)
        if not job:
            missing_job_ids.add(job_id)
            continue
        if job_id not in asr_cache:
            asr_cache[job_id] = load_private_asr(job)
        asr = asr_cache[job_id]
        if not asr:
            missing_asr_job_ids.add(job_id)
            continue
        item = review_window(window, job, asr)
        reviewed.append(item)
        source_ids.add(item["source_id"])
        platform_counts[item["platform"]] += 1
        signal_status_counts[item["signal_status"]] += 1
        topic_counts.update(item["topic_tags"])
        if item["visual_review_required"]:
            visual_required_count += 1

    output = {
        "review_run": {
            "run_id": f"video_asr_timestamp_review_{date.today().strftime('%Y%m%d')}",
            "created_at": date.today().isoformat(),
            "scope": [
                "All public-safe ASR candidate windows in the indexed non-YouTube Bilibili corpus.",
                "Private ASR text is used only in memory and is never written to this output.",
                "The review confirms timestamp/topic indexing, not visible biomechanics or Liu Hui's exact wording.",
            ],
            "inputs": {
                "candidate_windows": args.windows,
                "manifests": args.manifest,
            },
            "summary": {
                "candidate_windows": len(candidates),
                "reviewed_windows": len(reviewed),
                "reviewed_sources": len(source_ids),
                "visual_review_required_windows": visual_required_count,
                "missing_manifest_jobs": len(missing_job_ids),
                "missing_or_failed_asr_jobs": len(missing_asr_job_ids),
                "platform_window_counts": dict(platform_counts),
                "signal_status_counts": dict(signal_status_counts),
                "topic_window_counts": dict(topic_counts.most_common()),
            },
            "evidence_contract": {
                "evidence_level": "asr_timestamp_reviewed_public_safe",
                "review_status": "agent_asr_timestamp_reviewed",
                "allowed_use": "Framework routing, timestamp lookup, diagnostic question selection, and review prioritization.",
                "blocked_use": "Quotes, close paraphrases, human-reviewed claims, or visual biomechanical conclusions.",
            },
        },
        "windows": reviewed,
    }
    write_yaml(ROOT / args.output, output)
    print(f"wrote {args.output}")
    print(f"candidate_windows {len(candidates)}")
    print(f"reviewed_windows {len(reviewed)}")
    print(f"reviewed_sources {len(source_ids)}")
    print(f"missing_manifest_jobs {len(missing_job_ids)}")
    print(f"missing_or_failed_asr_jobs {len(missing_asr_job_ids)}")


if __name__ == "__main__":
    main()
