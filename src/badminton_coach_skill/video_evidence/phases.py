from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .contracts import ActionPackageSegment, Phase


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
ACTION_PACKAGE_SEGMENT_DURATION_MS = 800
ACTION_PACKAGE_ANCHOR_TOLERANCE_MS = 180
ACTION_PACKAGE_STAGE_OFFSETS_MS: tuple[tuple[Phase, int], ...] = (
    ("preparation", -2200),
    ("start", -1600),
    ("arrival", -1000),
    ("top_elbow", -400),
    ("contact_window", 0),
    ("follow_through", 500),
    ("recovery", 1100),
)
ACTION_PACKAGE_CAPTIONS: dict[Phase, str] = {
    "preparation": "启动与后退：连续观察起动方向、步频与身体是否先移动。",
    "start": "最后两步与制动：连续观察节奏、制动和重心是否进入击球点。",
    "arrival": "引拍、侧身与起跳准备：连续观察转体、架拍和蓄力顺序。",
    "top_elbow": "架拍与起跳前准备：连续观察持拍侧手臂与躯干的准备关系。",
    "contact_window": "腾空、挥拍与击球附近：这是可见动作窗口，不等同于精确击球点。",
    "follow_through": "随挥与落地：连续观察挥拍延续、落地缓冲与身体控制。",
    "recovery": "回位：连续观察落地后是否恢复到下一拍可移动的位置。",
}
ACTION_PACKAGE_LIMITATIONS = (
    "action_package_context_proxy",
    "exact_shuttle_contact_not_visible",
    "calibrated_3d_biomechanics_not_available",
)


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


def select_action_package(
    samples: list[PoseSample], action: str
) -> list[ActionPackageSegment]:
    """Select ordered continuous-clip anchors around one conservative motion peak.

    The labels identify where the clip falls in the selected action context; they do
    not assert an exact biomechanical event.  A stage with no local pose support is
    omitted rather than borrowing a nearby action or repeating another stage.
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
    half_duration = ACTION_PACKAGE_SEGMENT_DURATION_MS // 2
    package: list[ActionPackageSegment] = []
    for phase, offset_ms in ACTION_PACKAGE_STAGE_OFFSETS_MS:
        target_ms = motion_peak.timestamp_ms + offset_ms
        local_candidates = [
            sample
            for sample in visible
            if abs(sample.timestamp_ms - target_ms) <= ACTION_PACKAGE_ANCHOR_TOLERANCE_MS
        ]
        if not local_candidates:
            continue
        anchor = min(
            local_candidates,
            key=lambda sample: (abs(sample.timestamp_ms - target_ms), sample.timestamp_ms),
        )
        package.append(
            ActionPackageSegment(
                segment_id=f"student-{phase}-{anchor.timestamp_ms}",
                phase=phase,
                anchor_ms=anchor.timestamp_ms,
                start_ms=max(0, anchor.timestamp_ms - half_duration),
                end_ms=anchor.timestamp_ms + half_duration,
                confidence=_confidence([anchor]),
                caption=ACTION_PACKAGE_CAPTIONS[phase],
                limitations=ACTION_PACKAGE_LIMITATIONS,
            )
        )
    return package
