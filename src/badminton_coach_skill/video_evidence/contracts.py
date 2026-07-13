from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Phase = Literal[
    "preparation",
    "start",
    "arrival",
    "top_elbow",
    "contact_window",
    "follow_through",
    "recovery",
]
Confidence = Literal["low", "medium", "high"]
EvidenceStatus = Literal[
    "matched",
    "insufficient_evidence",
    "coach_reference_unavailable",
]

PHASES: frozenset[str] = frozenset(
    {
        "preparation",
        "start",
        "arrival",
        "top_elbow",
        "contact_window",
        "follow_through",
        "recovery",
    }
)
CONFIDENCES: frozenset[str] = frozenset({"low", "medium", "high"})


@dataclass(frozen=True)
class FrameRef:
    """A selected frame from a student video or private coach media cache."""

    frame_id: str
    owner: Literal["student", "coach"]
    phase: Phase
    timestamp_ms: int
    media_key: str
    confidence: Confidence
    visible_facts: tuple[str, ...]
    limitations: tuple[str, ...]
    camera_view: str = "unknown"

    def __post_init__(self) -> None:
        if not self.frame_id:
            raise ValueError("frame_id is required")
        if self.owner not in {"student", "coach"}:
            raise ValueError(f"Unsupported frame owner: {self.owner}")
        if self.phase not in PHASES:
            raise ValueError(f"Unsupported phase: {self.phase}")
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative")
        if self.confidence not in CONFIDENCES:
            raise ValueError(f"Unsupported confidence: {self.confidence}")

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_id": self.frame_id,
            "owner": self.owner,
            "phase": self.phase,
            "timestamp_ms": self.timestamp_ms,
            "media_key": self.media_key,
            "confidence": self.confidence,
            "visible_facts": list(self.visible_facts),
            "limitations": list(self.limitations),
            "camera_view": self.camera_view,
        }


@dataclass(frozen=True)
class CoachReference:
    """A cached public-source coach frame with its original provenance."""

    reference_id: str
    coach_id: str
    source_id: str
    phase: Phase
    timestamp_ms: int
    source_url: str
    confidence: Confidence
    actions: tuple[str, ...]
    framework_ids: tuple[str, ...]
    availability: Literal["indexed", "cached", "unavailable", "removed"]
    media_key: str = ""
    title: str = ""
    window_start_ms: int | None = None
    window_end_ms: int | None = None
    visible_facts: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.reference_id or not self.source_id or not self.coach_id:
            raise ValueError("reference_id, coach_id, and source_id are required")
        if self.phase not in PHASES:
            raise ValueError(f"Unsupported phase: {self.phase}")
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative")
        if self.confidence not in CONFIDENCES:
            raise ValueError(f"Unsupported confidence: {self.confidence}")
        if self.availability not in {"indexed", "cached", "unavailable", "removed"}:
            raise ValueError(f"Unsupported availability: {self.availability}")

    def to_dict(self) -> dict[str, object]:
        return {
            "reference_id": self.reference_id,
            "coach_id": self.coach_id,
            "source_id": self.source_id,
            "phase": self.phase,
            "timestamp_ms": self.timestamp_ms,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "actions": list(self.actions),
            "framework_ids": list(self.framework_ids),
            "availability": self.availability,
            "media_key": self.media_key,
            "title": self.title,
            "window_start_ms": self.window_start_ms,
            "window_end_ms": self.window_end_ms,
            "visible_facts": list(self.visible_facts),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class IssueEvidence:
    """Frame-level support for one deterministic coaching issue."""

    issue_id: str
    comparison_phase: Phase
    student_frame_ids: tuple[str, ...]
    coach_reference_ids: tuple[str, ...]
    correction_target: str
    confidence_boundary: str
    status: EvidenceStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "issue_id": self.issue_id,
            "comparison_phase": self.comparison_phase,
            "student_frame_ids": list(self.student_frame_ids),
            "coach_reference_ids": list(self.coach_reference_ids),
            "correction_target": self.correction_target,
            "confidence_boundary": self.confidence_boundary,
            "status": self.status,
        }
