from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


POWER_TOPICS = {
    "top_elbow",
    "internal_rotation",
    "hip_rotation",
    "contact_point",
    "racket_preparation",
    "wrist",
}

TOPIC_KEYWORDS = {
    "top_elbow": {"elbow", "overhead", "frame"},
    "internal_rotation": {"internal-rotation", "whip", "release"},
    "hip_rotation": {"hip", "trunk", "kinetic-chain"},
    "contact_point": {"contact", "overhead"},
    "racket_preparation": {"racket", "preparation", "frame"},
    "wrist": {"wrist", "grip", "finger", "whip"},
    "footwork": {"footwork", "arrival", "recovery", "rear-court", "front-court"},
    "smash": {"smash"},
    "high_clear": {"clear", "overhead"},
    "drop": {"drop", "slice", "cut-shot"},
    "drive": {"drive", "exchange", "jammed"},
    "serve_receive": {"serve", "receive"},
    "doubles": {"doubles", "partner"},
    "match_transfer": {"match", "transfer", "pressure"},
    "safety": {"safety", "load", "mobility"},
    "student_fit": {"learner-fit", "profile", "selector"},
    "equipment": {"equipment", "racket", "fit", "load"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the public-safe source-to-framework multimodal explainability map."
    )
    parser.add_argument("--coach-config")
    parser.add_argument("--visual-manifest")
    parser.add_argument(
        "--source-manifest",
        action="append",
        default=[],
        help="Source manifest used to include ASR-only accessible videos in the evidence map.",
    )
    parser.add_argument("--asr-review")
    parser.add_argument("--visual-summary")
    parser.add_argument("--temporal-summary")
    parser.add_argument("--frameworks")
    parser.add_argument("--visual-contract")
    parser.add_argument("--output")
    return parser.parse_args()


def coach_artifact_defaults(config_path: str) -> dict[str, str]:
    config = load_yaml(ROOT / config_path)
    corpus_path = Path(str(config["corpus_path"]))
    reference_path = Path(str(config["reference_path"]))
    return {
        "coach_id": str(config["coach_id"]),
        "coach_name": str(config["display_name"]),
        "source_manifest": str(corpus_path / "video-corpus-manifest.yaml"),
        "asr_review": str(corpus_path / "video-asr-timestamp-review.yaml"),
        "visual_manifest": str(corpus_path / "video-visual-pipeline-manifest.yaml"),
        "visual_summary": str(corpus_path / "video-visual-evidence-summary.yaml"),
        "temporal_summary": str(corpus_path / "video-temporal-pose-summary.yaml"),
        "frameworks": str(reference_path / "frameworks.yaml"),
        "visual_contract": str(reference_path / "visual-evidence-contract.yaml"),
        "output": str(reference_path / "multimodal-evidence-map.yaml"),
    }


def artifact_defaults(args: argparse.Namespace) -> dict[str, str]:
    if args.coach_config:
        return coach_artifact_defaults(args.coach_config)
    return {
        "coach_id": "liu-hui",
        "coach_name": "Liu Hui",
        "source_manifest": "data/corpus/video-corpus-manifest.yaml",
        "asr_review": "data/corpus/video-asr-timestamp-review.yaml",
        "visual_manifest": "data/corpus/video-visual-pipeline-manifest.yaml",
        "visual_summary": "data/corpus/video-visual-evidence-summary.yaml",
        "temporal_summary": "data/corpus/video-temporal-pose-summary.yaml",
        "frameworks": "skills/liu-hui-badminton-coach/references/frameworks.yaml",
        "visual_contract": "skills/liu-hui-badminton-coach/references/visual-evidence-contract.yaml",
        "output": "skills/liu-hui-badminton-coach/references/multimodal-evidence-map.yaml",
    }


def expanded_actions(topics: set[str]) -> set[str]:
    actions = set(topics)
    if topics & POWER_TOPICS:
        actions.update({"high_clear", "smash"})
    if "footwork" in topics:
        actions.update({"rear_footwork", "front_footwork"})
    if "doubles" in topics:
        actions.add("serve_receive")
    return actions


def rank_frameworks(
    source_id: str,
    topics: set[str],
    frameworks: list[dict[str, Any]],
    limit: int = 8,
) -> list[str]:
    actions = expanded_actions(topics)
    scored: list[tuple[int, str]] = []
    for framework in frameworks:
        framework_id = str(framework.get("framework_id") or "")
        if not framework_id:
            continue
        score = 0
        if source_id in framework.get("source_ids", []):
            score += 100
        applicable = set(framework.get("applicable_actions", []))
        score += 10 * len(actions & applicable)
        normalized_id = framework_id.lower()
        for topic in topics:
            if any(keyword in normalized_id for keyword in TOPIC_KEYWORDS.get(topic, set())):
                score += 4
        if score > 0:
            scored.append((score, framework_id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    ranked = [framework_id for _, framework_id in scored[: max(limit, 0)]]
    if not ranked:
        catalog_ids = sorted(
            str(framework.get("framework_id"))
            for framework in frameworks
            if framework.get("framework_id")
        )
        ranked = catalog_ids[:1]
    return ranked


def load_optional(path: Path) -> dict[str, Any]:
    return load_yaml(path) if path.exists() else {}


def load_source_jobs(
    manifest_paths: list[Path], valid_source_ids: set[str]
) -> list[dict[str, Any]]:
    jobs_by_source: dict[str, dict[str, Any]] = {}
    for path in manifest_paths:
        manifest = load_yaml(path)
        for job in manifest.get("jobs", []):
            source_id = str(job["source_id"])
            if source_id in valid_source_ids and source_id not in jobs_by_source:
                jobs_by_source[source_id] = job
    return list(jobs_by_source.values())


def valid_visual_item(item: dict[str, Any]) -> bool:
    return (
        item.get("evidence_level") == "visual_model_structured_candidate_public_safe"
        and item.get("review_status") == "schema_validated_model_output"
    )


def contract_ids(topics: set[str], contracts: list[dict[str, Any]]) -> list[str]:
    actions = expanded_actions(topics)
    return [
        str(item["diagnosis_id"])
        for item in contracts
        if actions & set(item.get("applies_to", []))
    ]


def confidence_boundary(has_visual: bool, has_temporal: bool) -> str:
    if has_temporal:
        return (
            "ASR routes the teaching topic; validated VLM stills report visible conditions; dense Pose "
            "reports coarse 2D geometry change. None proves shuttle contact, racket face, grip pressure, "
            "force, causality, or true shoulder internal rotation."
        )
    if has_visual:
        return (
            "ASR routes the teaching topic and validated VLM stills report visible conditions. Sparse "
            "stills do not establish motion sequence, contact, racket face, force, causality, or true "
            "joint rotation."
        )
    return (
        "ASR supports topic routing and timestamp lookup only. Visible mechanics require the pending "
        "VLM/Pose evidence or direct human video review."
    )


def main() -> None:
    args = parse_args()
    defaults = artifact_defaults(args)
    manifest = load_yaml(ROOT / (args.visual_manifest or defaults["visual_manifest"]))
    asr = load_yaml(ROOT / (args.asr_review or defaults["asr_review"]))
    visual = load_optional(ROOT / (args.visual_summary or defaults["visual_summary"]))
    temporal = load_optional(ROOT / (args.temporal_summary or defaults["temporal_summary"]))
    frameworks = load_yaml(ROOT / (args.frameworks or defaults["frameworks"]))
    contracts = load_yaml(ROOT / (args.visual_contract or defaults["visual_contract"]))

    asr_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for window in asr.get("windows", []):
        asr_by_source[str(window["source_id"])].append(window)
    visual_by_source = {
        str(item["source_id"]): item
        for item in visual.get("sources", [])
        if valid_visual_item(item)
    }
    temporal_by_source = {
        str(item["source_id"]): item for item in temporal.get("sources", [])
    }
    visual_scope_ids = {
        str(job["source_id"]) for job in manifest.get("jobs", [])
    }
    source_jobs = load_source_jobs(
        [ROOT / path for path in (args.source_manifest or [defaults["source_manifest"]])],
        set(asr_by_source),
    )

    sources: list[dict[str, Any]] = []
    level_counts: Counter[str] = Counter()
    framework_counts: Counter[str] = Counter()
    for job in source_jobs:
        source_id = str(job["source_id"])
        windows = sorted(
            asr_by_source.get(source_id, []),
            key=lambda item: (item.get("start_seconds", 0), item["window_id"]),
        )
        visual_item = visual_by_source.get(source_id)
        temporal_item = temporal_by_source.get(source_id)
        topics = {
            str(topic)
            for window in windows
            for topic in window.get("topic_tags", [])
        }
        topics.update(str(topic) for topic in job.get("priority_topics", []))
        framework_ids = rank_frameworks(source_id, topics, frameworks)
        framework_counts.update(framework_ids)
        levels = []
        if windows:
            levels.append("asr_timestamp_reviewed_public_safe")
        if visual_item:
            levels.append("visual_model_structured_candidate_public_safe")
        if temporal_item:
            levels.append("temporal_pose_proxy_public_safe")
        if source_id not in visual_scope_ids:
            levels.append("asr_only_conceptual_public_safe")
        level_counts.update(levels)
        sources.append(
            {
                "job_id": job["job_id"],
                "source_id": source_id,
                "title": job["title"],
                "platform": job["platform"],
                "topic_tags": sorted(topics),
                "framework_ids": framework_ids,
                "diagnostic_contract_ids": contract_ids(topics, contracts),
                "asr_timestamp_refs": [
                    {
                        "window_id": window["window_id"],
                        "start_seconds": window["start_seconds"],
                        "end_seconds": window["end_seconds"],
                        "topic_tags": window.get("topic_tags", []),
                    }
                    for window in windows
                ],
                "visual_timestamp_refs": (
                    visual_item.get("timestamps_seconds", []) if visual_item else []
                ),
                "visual_signal_counts": (
                    visual_item.get("visible_signal_counts", {}) if visual_item else {}
                ),
                "visual_observation_refs": (
                    visual_item.get("visible_observation_refs", []) if visual_item else []
                ),
                "temporal_sequence_refs": (
                    [
                        {
                            "sequence_id": sequence["sequence_id"],
                            "start_seconds": sequence["start_seconds"],
                            "end_seconds": sequence["end_seconds"],
                            "topic_tags": sequence.get("topic_tags", []),
                            "geometry_valid_frame_count": sequence.get(
                                "geometry_valid_frame_count", 0
                            ),
                        }
                        for sequence in temporal_item.get("sequences", [])
                    ]
                    if temporal_item
                    else []
                ),
                "evidence_levels": levels,
                "confidence_boundary": confidence_boundary(
                    visual_item is not None, temporal_item is not None
                ),
                "human_review_status": "not_human_reviewed",
                "visual_scope": (
                    "action_or_visible_demonstration"
                    if source_id in visual_scope_ids
                    else "asr_only_conceptual_or_equipment"
                ),
            }
        )
    output = {
        "multimodal_evidence_run": {
            "run_id": f"multimodal_evidence_{date.today().strftime('%Y%m%d')}",
            "created_at": date.today().isoformat(),
            "scope": f"Accessible non-YouTube {defaults['coach_name']} public corpus only.",
            "summary": {
                "source_count": len(sources),
                "sources_with_asr": sum(bool(item["asr_timestamp_refs"]) for item in sources),
                "sources_with_visual": sum(bool(item["visual_timestamp_refs"]) for item in sources),
                "sources_with_temporal": sum(bool(item["temporal_sequence_refs"]) for item in sources),
                "evidence_level_counts": dict(level_counts),
                "framework_source_counts": dict(framework_counts.most_common()),
            },
            "evidence_policy": {
                "routing": "ASR timestamps select topics, questions, and candidate frameworks.",
                "still_visibility": "VLM v4 reports schema-validated visible conditions in sparse stills.",
                "temporal_proxy": "Dense Pose reports coarse 2D body-geometry change for critical sources.",
                "promotion_boundary": "No model-only evidence is labeled human review or biomechanical proof.",
            },
        },
        "sources": sources,
    }
    output_path = args.output or defaults["output"]
    write_yaml(ROOT / output_path, output)
    print(f"wrote {output_path}")
    print(f"source_count {len(sources)}")
    print(f"sources_with_visual {sum(bool(item['visual_timestamp_refs']) for item in sources)}")
    print(f"sources_with_temporal {sum(bool(item['temporal_sequence_refs']) for item in sources)}")


if __name__ == "__main__":
    main()
