from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .contracts import CoachReference, FrameRef, IssueEvidence, Phase


ISSUE_PHASES: tuple[tuple[tuple[str, ...], Phase], ...] = (
    (("late-start", "late_start", "start-"), "start"),
    (("arrival", "turn", "confirmation", "landing"), "arrival"),
    (("elbow", "racket-structure", "racket_structure", "frame", "wrist-first", "wrist_first"), "top_elbow"),
    (("contact", "swing-distance", "swing_distance"), "contact_window"),
    (("follow", "twist", "rotation", "arm-first", "arm_first"), "follow_through"),
    (("recovery", "exit"), "recovery"),
)

DEFAULT_PHASE: Phase = "preparation"
BOUNDARY = (
    "Frame evidence supports only visible conditions in the selected phase. "
    "It does not prove force, exact shuttle contact, racket-face angle, grip pressure, "
    "true internal rotation, or calibrated 3D biomechanics."
)


def phase_for_issue(issue_id: str) -> Phase:
    normalized = issue_id.lower().replace("_", "-")
    for keywords, phase in ISSUE_PHASES:
        if any(keyword in normalized for keyword in keywords):
            return phase
    return DEFAULT_PHASE


def _rank_student_frames(
    frames: Iterable[FrameRef], phase: Phase
) -> list[FrameRef]:
    confidence_score = {"high": 3, "medium": 2, "low": 1}
    return sorted(
        (frame for frame in frames if frame.owner == "student" and frame.phase == phase),
        key=lambda frame: (-confidence_score[frame.confidence], frame.timestamp_ms, frame.frame_id),
    )


def _rank_coach_references(
    references: Iterable[CoachReference],
    phase: Phase,
    coach_id: str,
    action: str,
    framework_id: str,
) -> list[CoachReference]:
    confidence_score = {"high": 3, "medium": 2, "low": 1}
    availability_score = {"cached": 3, "indexed": 2, "unavailable": 0, "removed": 0}
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
            -availability_score[reference.availability],
            -confidence_score[reference.confidence],
            reference.timestamp_ms,
            reference.reference_id,
        ),
    )


def resolve_issue_evidence(
    diagnosis: dict[str, Any],
    observation: dict[str, Any],
    student_frames: Iterable[FrameRef],
    coach_references: Iterable[CoachReference],
    coach_id: str,
    framework_id: str,
) -> list[IssueEvidence]:
    """Attach same-phase student and coach references without substituting frames."""
    student_by_phase = list(student_frames)
    coach_catalog = list(coach_references)
    action = str(observation.get("action", "unknown"))
    resolved: list[IssueEvidence] = []

    for issue in diagnosis.get("issues", []):
        issue_id = str(issue.get("issue_id", "unknown"))
        phase = phase_for_issue(issue_id)
        student = _rank_student_frames(student_by_phase, phase)[:2]
        coach = _rank_coach_references(
            coach_catalog, phase, coach_id, action, framework_id
        )[:2]
        if not student:
            status = "insufficient_evidence"
        elif not coach:
            status = "coach_reference_unavailable"
        else:
            status = "matched"
        resolved.append(
            IssueEvidence(
                issue_id=issue_id,
                comparison_phase=phase,
                student_frame_ids=tuple(frame.frame_id for frame in student),
                coach_reference_ids=tuple(reference.reference_id for reference in coach),
                correction_target=str(issue.get("correction_principle", "")),
                confidence_boundary=BOUNDARY,
                status=status,
            )
        )
    return resolved
