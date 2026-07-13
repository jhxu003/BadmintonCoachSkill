from __future__ import annotations

from collections.abc import Iterable

from ..video_evidence.contracts import CoachReference, Phase


def match_coach_references(
    issue_id: str,
    phase: Phase,
    coach_id: str,
    action: str,
    framework_id: str,
    references: Iterable[CoachReference],
    limit: int = 2,
) -> list[CoachReference]:
    """Select only same-coach, same-phase, provenance-compatible references."""
    availability_rank = {"cached": 2, "indexed": 1, "unavailable": 0, "removed": 0}
    confidence_rank = {"high": 3, "medium": 2, "low": 1}
    candidates = [
        reference
        for reference in references
        if reference.coach_id == coach_id
        and reference.phase == phase
        and reference.availability in {"cached", "indexed"}
        and (not reference.actions or action in reference.actions)
        and (not reference.framework_ids or framework_id in reference.framework_ids)
    ]
    return sorted(
        candidates,
        key=lambda reference: (
            -availability_rank[reference.availability],
            -confidence_rank[reference.confidence],
            reference.timestamp_ms,
            reference.reference_id,
        ),
    )[: max(limit, 0)]
