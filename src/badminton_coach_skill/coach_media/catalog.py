from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from ..coach_registry import load_coach_config, load_coach_knowledge
from ..source_index import read_source_index
from ..video_evidence.contracts import CoachReference, Phase


def _phase_for_observation(observation: dict[str, Any]) -> Phase:
    racket_position = str(observation.get("racket_position", ""))
    body = set(observation.get("body_configuration", []))
    if racket_position == "above_shoulder" or "arm_raised" in body:
        return "top_elbow"
    if {"lunge", "single_leg_support", "staggered_stance"} & body:
        return "arrival"
    if "arm_extended" in body:
        return "follow_through"
    return "preparation"


def _source_rows(root: Path, coach_id: str) -> dict[str, dict[str, str]]:
    config = load_coach_config(coach_id, root)
    source_index = root / str(config["source_index"])
    return {row["source_id"]: row for row in read_source_index(source_index)}


def _reference(
    coach_id: str,
    source: dict[str, Any],
    source_row: dict[str, str],
    timestamp_seconds: float,
    phase: Phase,
    suffix: str,
    visible_facts: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
    confidence: str = "medium",
    review_status: str = "model_candidate",
    teaching_use: str = "",
    actions: tuple[str, ...] | None = None,
) -> CoachReference:
    source_id = str(source["source_id"])
    return CoachReference(
        reference_id=f"{source_id.lower()}-{suffix}-{round(timestamp_seconds * 1000)}",
        coach_id=coach_id,
        source_id=source_id,
        phase=phase,
        timestamp_ms=round(timestamp_seconds * 1000),
        source_url=source_row["url"],
        confidence=confidence,  # type: ignore[arg-type]
        actions=actions if actions is not None else tuple(source.get("topic_tags", [])),
        framework_ids=tuple(source.get("framework_ids", [])),
        availability="indexed",
        title=source_row["title"],
        window_start_ms=None,
        window_end_ms=None,
        visible_facts=visible_facts,
        limitations=limitations,
        review_status=review_status,  # type: ignore[arg-type]
        teaching_use=teaching_use,
    )


def _reviewed_demonstrations(
    root: Path, coach_id: str
) -> dict[tuple[str, int], dict[str, Any]]:
    config = load_coach_config(coach_id, root)
    path = root / str(config["reference_path"]) / "reviewed-demonstrations.yaml"
    if not path.is_file():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = payload.get("references", []) if isinstance(payload, dict) else []
    return {
        (str(row["source_id"]), round(float(row["timestamp_seconds"]) * 1000)): row
        for row in rows
        if isinstance(row, dict)
        and row.get("source_id")
        and row.get("timestamp_seconds") is not None
    }


def build_source_catalog(
    coach_id: str,
    root: str | Path,
    knowledge: dict[str, Any] | None = None,
) -> list[CoachReference]:
    """Build public-safe reference metadata without reading or writing media files."""
    project_root = Path(root)
    rows = _source_rows(project_root, coach_id)
    reviewed = _reviewed_demonstrations(project_root, coach_id)
    evidence = (knowledge or load_coach_knowledge(coach_id, project_root)).get(
        "multimodal_evidence", {}
    )
    references: list[CoachReference] = []
    for source in evidence.get("sources", []):
        source_id = str(source.get("source_id", ""))
        source_row = rows.get(source_id)
        if source_row is None or source_row.get("source_type") != "video":
            continue
        observations = source.get("visual_observation_refs", [])
        for index, observation in enumerate(observations):
            timestamp = float(observation.get("timestamp_seconds", 0))
            body = [str(item) for item in observation.get("body_configuration", [])]
            if observation.get("person_visible"):
                body.append("person_visible")
            racket_position = str(observation.get("racket_position", ""))
            if racket_position not in {"", "not_visible", "unclear"}:
                body.extend(("racket_visible", f"racket_{racket_position}"))
            view = str(observation.get("primary_subject_view", ""))
            if view not in {"", "not_visible", "unclear"}:
                body.append(f"view_{view}")
            body.append(
                "on_screen_text_present"
                if observation.get("on_screen_text_present")
                else "on_screen_text_absent"
            )
            limitations = tuple(str(item) for item in observation.get("visibility_limits", []))
            review = reviewed.get((source_id, round(timestamp * 1000)), {})
            reviewed_facts = [str(item) for item in review.get("visible_facts", [])]
            reviewed_limits = [str(item) for item in review.get("limitations", [])]
            reviewed_action = str(review.get("action", "")).strip()
            references.append(
                _reference(
                    coach_id,
                    source,
                    source_row,
                    timestamp,
                    str(review.get("phase", _phase_for_observation(observation))),  # type: ignore[arg-type]
                    f"visual-{index}",
                    visible_facts=tuple(dict.fromkeys((*body, *reviewed_facts))),
                    limitations=tuple(dict.fromkeys((*limitations, *reviewed_limits))),
                    confidence=(
                        "high"
                        if review.get("review_status") == "agent_reviewed"
                        else str(observation.get("confidence", "medium"))
                    ),
                    review_status=str(review.get("review_status", "model_candidate")),
                    teaching_use=str(review.get("teaching_use", "")),
                    actions=(reviewed_action,) if reviewed_action else None,
                )
            )
        if observations:
            continue
        for index, timestamp in enumerate(source.get("visual_timestamp_refs", [])):
            references.append(
                _reference(
                    coach_id,
                    source,
                    source_row,
                    float(timestamp),
                    "preparation",
                    f"timestamp-{index}",
                    limitations=("visual_details_not_available_in_public_safe_catalog",),
                    review_status="timestamp_only",
                )
            )
    return sorted(
        references,
        key=lambda reference: (reference.source_id, reference.timestamp_ms, reference.reference_id),
    )
