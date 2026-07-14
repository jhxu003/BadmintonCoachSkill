from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .contracts import Phase


SUPPORTED_ACTIONS = frozenset(
    {
        "high_clear",
        "smash",
        "drop",
        "drive",
        "net",
        "rear_footwork",
        "front_footwork",
        "backhand",
        "serve_receive",
        "doubles",
        "match_transfer",
        "unknown",
    }
)
MIN_POSE_CONFIDENCE = 0.5
ACTION_CONTEXT_MS = 1200
MIN_PHASE_SEPARATION_MS = 200
ACTIVE_PRE_CONTACT_WINDOW_MS = 500
ACTIVE_PRE_CONTACT_REASON = "highest_visible_elbow_in_active_pre_contact_window"


@dataclass(frozen=True)
class PoseSample:
    """Minimal public-safe pose summary for selecting frame candidates."""

    timestamp_ms: int
    left_shoulder_y: float | None
    right_shoulder_y: float | None
    racket_elbow_y: float | None
    racket_wrist_y: float | None
    motion_score: float
    confidence: float

    def has_visible_elbow(self) -> bool:
        return self.racket_elbow_y is not None and self.confidence >= MIN_POSE_CONFIDENCE


@dataclass(frozen=True)
class PhaseCandidate:
    phase: Phase
    timestamp_ms: int
    confidence: Literal["low", "medium", "high"]
    reason: str


def _confidence(samples: list[PoseSample]) -> Literal["low", "medium", "high"]:
    if not samples:
        return "low"
    average = sum(sample.confidence for sample in samples) / len(samples)
    if average >= 0.8:
        return "high"
    if average >= MIN_POSE_CONFIDENCE:
        return "medium"
    return "low"


def _candidate(
    phase: Phase, sample: PoseSample, reason: str, support: list[PoseSample]
) -> PhaseCandidate:
    return PhaseCandidate(
        phase=phase,
        timestamp_ms=sample.timestamp_ms,
        confidence=_confidence(support),
        reason=reason,
    )


def select_phase_candidates(
    samples: list[PoseSample], action: str
) -> list[PhaseCandidate]:
    """Return conservative phase candidates from a single learner pose sequence.

    The caller must attach camera/view limitations separately. This function only
    ranks visible 2D temporal proxies and never claims exact shuttle contact.
    """
    if action not in SUPPORTED_ACTIONS:
        action = "unknown"
    visible = sorted(
        (sample for sample in samples if sample.confidence >= MIN_POSE_CONFIDENCE),
        key=lambda sample: sample.timestamp_ms,
    )
    if not visible:
        return []

    motion_peak = max(
        visible, key=lambda sample: (sample.motion_score, -sample.timestamp_ms)
    )
    action_window = [
        sample
        for sample in visible
        if abs(sample.timestamp_ms - motion_peak.timestamp_ms) <= ACTION_CONTEXT_MS
    ]
    before_peak = [
        sample for sample in action_window if sample.timestamp_ms <= motion_peak.timestamp_ms
    ]
    after_peak = [
        sample for sample in action_window if sample.timestamp_ms > motion_peak.timestamp_ms
    ]
    elbow_candidates = [sample for sample in before_peak if sample.has_visible_elbow()]
    candidates: list[PhaseCandidate] = []

    if elbow_candidates:
        distinct_pre_hit = [
            sample
            for sample in elbow_candidates
            if sample.timestamp_ms <= motion_peak.timestamp_ms - MIN_PHASE_SEPARATION_MS
        ]
        active_pre_contact = [
            sample
            for sample in distinct_pre_hit
            if sample.timestamp_ms
            >= motion_peak.timestamp_ms - ACTIVE_PRE_CONTACT_WINDOW_MS
        ]
        if active_pre_contact:
            top_elbow = max(
                active_pre_contact,
                key=lambda sample: (-float(sample.racket_elbow_y), sample.timestamp_ms),
            )
            candidates.append(
                _candidate(
                    "top_elbow",
                    top_elbow,
                    ACTIVE_PRE_CONTACT_REASON,
                    [top_elbow],
                )
            )
    candidates.append(
        _candidate(
            "contact_window",
            motion_peak,
            "maximum_visible_motion_proxy_not_exact_shuttle_contact",
            [motion_peak],
        )
    )

    distinct_follow_through = [
        sample
        for sample in after_peak
        if sample.timestamp_ms >= motion_peak.timestamp_ms + MIN_PHASE_SEPARATION_MS
    ]
    if distinct_follow_through:
        follow = distinct_follow_through[0]
        candidates.append(
            _candidate(
                "follow_through",
                follow,
                "post_motion_peak_visible_travel_proxy",
                [follow],
            )
        )
    phase_order = {
        "preparation": 0,
        "start": 1,
        "arrival": 2,
        "top_elbow": 3,
        "contact_window": 4,
        "follow_through": 5,
        "recovery": 6,
    }
    return sorted(candidates, key=lambda item: (phase_order[item.phase], item.timestamp_ms))
