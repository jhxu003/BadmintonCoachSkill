from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

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
) -> CoachReference:
    source_id = str(source["source_id"])
    return CoachReference(
        reference_id=f"{source_id.lower()}-{suffix}-{round(timestamp_seconds * 1000)}",
        coach_id=coach_id,
        source_id=source_id,
        phase=phase,
        timestamp_ms=round(timestamp_seconds * 1000),
        source_url=source_row["url"],
        confidence="high" if source.get("visual_observation_refs") else "medium",
        actions=tuple(source.get("topic_tags", [])),
        framework_ids=tuple(source.get("framework_ids", [])),
        availability="indexed",
        title=source_row["title"],
        window_start_ms=None,
        window_end_ms=None,
        visible_facts=visible_facts,
        limitations=limitations,
    )


def build_source_catalog(coach_id: str, root: str | Path) -> list[CoachReference]:
    """Build public-safe reference metadata without reading or writing media files."""
    project_root = Path(root)
    rows = _source_rows(project_root, coach_id)
    evidence = load_coach_knowledge(coach_id, project_root).get("multimodal_evidence", {})
    references: list[CoachReference] = []
    for source in evidence.get("sources", []):
        source_id = str(source.get("source_id", ""))
        source_row = rows.get(source_id)
        if source_row is None or source_row.get("source_type") != "video":
            continue
        observations = source.get("visual_observation_refs", [])
        for index, observation in enumerate(observations):
            timestamp = float(observation.get("timestamp_seconds", 0))
            body = tuple(str(item) for item in observation.get("body_configuration", []))
            limitations = tuple(str(item) for item in observation.get("visibility_limits", []))
            references.append(
                _reference(
                    coach_id,
                    source,
                    source_row,
                    timestamp,
                    _phase_for_observation(observation),
                    f"visual-{index}",
                    visible_facts=body,
                    limitations=limitations,
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
                )
            )
    return sorted(
        references,
        key=lambda reference: (reference.source_id, reference.timestamp_ms, reference.reference_id),
    )
