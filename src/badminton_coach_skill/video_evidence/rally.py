from __future__ import annotations

from dataclasses import dataclass
from math import acos, isfinite
from typing import Iterable, Literal

from .multiplayer import ParticipantSelection


Confidence = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class NormalizedBox:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if not all(isfinite(value) for value in values):
            raise ValueError("player boxes must contain finite coordinates")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("player box dimensions must be positive")
        if self.x < 0 or self.y < 0 or self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("player boxes must be normalized inside the frame")

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    def contains(self, x: float, y: float, margin: float = 0.0) -> bool:
        return (
            self.x - margin <= x <= self.x + self.width + margin
            and self.y - margin <= y <= self.y + self.height + margin
        )

    def distance_to(self, x: float, y: float) -> float:
        center_x, center_y = self.center
        return ((center_x - x) ** 2 + (center_y - y) ** 2) ** 0.5

    def to_dict(self) -> dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class PlayerTrackSample:
    track_id: str
    timestamp_ms: int
    bbox: NormalizedBox
    court_x: float
    court_y: float
    confidence: float

    def __post_init__(self) -> None:
        if not self.track_id:
            raise ValueError("track_id is required")
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative")
        if not 0.0 <= self.court_x <= 1.0 or not 0.0 <= self.court_y <= 1.0:
            raise ValueError("court coordinates must be normalized")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("track confidence must be normalized")

    def to_dict(self) -> dict[str, object]:
        return {
            "track_id": self.track_id,
            "timestamp_ms": self.timestamp_ms,
            "bbox": self.bbox.to_dict(),
            "court_x": self.court_x,
            "court_y": self.court_y,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class ShuttleHeatmapCandidate:
    candidate_id: str
    timestamp_ms: int
    x: float
    y: float
    confidence: float
    alternatives: tuple[tuple[float, float, float], ...] = ()
    occluded: bool = False
    interpolated: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("shuttle candidate id is required")
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative")
        if not 0.0 <= self.x <= 1.0 or not 0.0 <= self.y <= 1.0:
            raise ValueError("shuttle coordinates must be normalized")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("shuttle confidence must be normalized")

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "timestamp_ms": self.timestamp_ms,
            "x": self.x,
            "y": self.y,
            "confidence": self.confidence,
            "alternatives": [
                {"x": x, "y": y, "confidence": confidence}
                for x, y, confidence in self.alternatives
            ],
            "occluded": self.occluded,
            "interpolated": self.interpolated,
        }


@dataclass(frozen=True)
class ContactCandidate:
    candidate_id: str
    start_ms: int
    end_ms: int
    anchor_ms: int
    shuttle_candidate_ids: tuple[str, ...]
    possible_track_ids: tuple[str, ...]
    confidence: Confidence
    limitations: tuple[str, ...] = (
        "exact_shuttle_contact_not_claimed",
        "racket_contact_not_directly_observed",
        "monocular_temporal_heatmap_proxy",
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "anchor_ms": self.anchor_ms,
            "contact_time_ms": None,
            "shuttle_candidate_ids": list(self.shuttle_candidate_ids),
            "possible_track_ids": list(self.possible_track_ids),
            "confidence": self.confidence,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class RallySegment:
    rally_id: str
    start_ms: int
    end_ms: int
    shuttle_candidate_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "rally_id": self.rally_id,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "shuttle_candidate_ids": list(self.shuttle_candidate_ids),
        }


def _direction_change(
    previous: ShuttleHeatmapCandidate,
    anchor: ShuttleHeatmapCandidate,
    following: ShuttleHeatmapCandidate,
) -> float:
    first = (anchor.x - previous.x, anchor.y - previous.y)
    second = (following.x - anchor.x, following.y - anchor.y)
    first_norm = max((first[0] ** 2 + first[1] ** 2) ** 0.5, 1e-9)
    second_norm = max((second[0] ** 2 + second[1] ** 2) ** 0.5, 1e-9)
    cosine = max(-1.0, min(1.0, (first[0] * second[0] + first[1] * second[1]) / (first_norm * second_norm)))
    return acos(cosine)


def build_contact_candidates(
    shuttle_candidates: Iterable[ShuttleHeatmapCandidate],
    player_samples: Iterable[PlayerTrackSample],
    *,
    direction_change_radians: float = 1.15,
    player_time_tolerance_ms: int = 120,
) -> list[ContactCandidate]:
    """Return bounded direction-change windows near a visible player.

    These windows are candidate interactions only. They intentionally expose no
    exact contact timestamp and remain valid when the shuttle is briefly occluded.
    """
    shuttle = sorted(shuttle_candidates, key=lambda candidate: candidate.timestamp_ms)
    players = list(player_samples)
    contacts: list[ContactCandidate] = []
    for index in range(1, len(shuttle) - 1):
        previous, anchor, following = shuttle[index - 1 : index + 2]
        if _direction_change(previous, anchor, following) < direction_change_radians:
            continue
        nearby = [
            sample
            for sample in players
            if abs(sample.timestamp_ms - anchor.timestamp_ms) <= player_time_tolerance_ms
            and sample.bbox.contains(anchor.x, anchor.y, margin=0.035)
        ]
        if not nearby:
            continue
        best_by_track: dict[str, PlayerTrackSample] = {}
        for sample in sorted(
            nearby,
            key=lambda item: (
                item.bbox.distance_to(anchor.x, anchor.y),
                -item.confidence,
                item.track_id,
            ),
        ):
            best_by_track.setdefault(sample.track_id, sample)
        ranked_tracks = sorted(
            best_by_track,
            key=lambda track_id: (
                best_by_track[track_id].bbox.distance_to(anchor.x, anchor.y),
                -best_by_track[track_id].confidence,
                track_id,
            ),
        )
        confidence: Confidence = (
            "high"
            if len(ranked_tracks) == 1 and anchor.confidence >= 0.85 and not anchor.interpolated
            else "medium"
            if anchor.confidence >= 0.65
            else "low"
        )
        start_ms = (previous.timestamp_ms + anchor.timestamp_ms) // 2
        end_ms = (anchor.timestamp_ms + following.timestamp_ms) // 2
        contacts.append(
            ContactCandidate(
                candidate_id=f"contact-{anchor.timestamp_ms}-{len(contacts) + 1}",
                start_ms=start_ms,
                end_ms=end_ms,
                anchor_ms=anchor.timestamp_ms,
                shuttle_candidate_ids=(
                    previous.candidate_id,
                    anchor.candidate_id,
                    following.candidate_id,
                ),
                possible_track_ids=tuple(ranked_tracks),
                confidence=confidence,
            )
        )
    return contacts


def segment_rallies(
    shuttle_candidates: Iterable[ShuttleHeatmapCandidate],
    *,
    gap_ms: int = 900,
    minimum_candidates: int = 4,
) -> list[RallySegment]:
    shuttle = sorted(shuttle_candidates, key=lambda candidate: candidate.timestamp_ms)
    if not shuttle:
        return []
    groups: list[list[ShuttleHeatmapCandidate]] = [[shuttle[0]]]
    for candidate in shuttle[1:]:
        if candidate.timestamp_ms - groups[-1][-1].timestamp_ms > gap_ms:
            groups.append([candidate])
        else:
            groups[-1].append(candidate)
    return [
        RallySegment(
            rally_id=f"rally-{index}",
            start_ms=group[0].timestamp_ms,
            end_ms=group[-1].timestamp_ms,
            shuttle_candidate_ids=tuple(candidate.candidate_id for candidate in group),
        )
        for index, group in enumerate(
            (group for group in groups if len(group) >= minimum_candidates), start=1
        )
    ]


def _same_lane_conflict_ratio(
    learner_samples: dict[int, PlayerTrackSample],
    partner_samples: dict[int, PlayerTrackSample],
) -> tuple[float | None, int]:
    shared = sorted(set(learner_samples) & set(partner_samples))
    if not shared:
        return None, 0
    conflicts = 0
    longest_conflict_ms = 0
    current_start_ms: int | None = None
    previous_conflict_ms: int | None = None
    for timestamp in shared:
        learner = learner_samples[timestamp]
        partner = partner_samples[timestamp]
        same_half = (learner.court_x < 0.5) == (partner.court_x < 0.5)
        narrow_lateral_gap = abs(learner.court_x - partner.court_x) <= 0.18
        overlapping_depth = abs(learner.court_y - partner.court_y) <= 0.38
        if same_half and narrow_lateral_gap and overlapping_depth:
            conflicts += 1
            if previous_conflict_ms is None or timestamp - previous_conflict_ms > 250:
                current_start_ms = timestamp
            if current_start_ms is not None:
                longest_conflict_ms = max(longest_conflict_ms, timestamp - current_start_ms)
            previous_conflict_ms = timestamp
        else:
            current_start_ms = None
            previous_conflict_ms = None
    return conflicts / len(shared), longest_conflict_ms


def build_mixed_doubles_observation(
    *,
    selection: ParticipantSelection,
    player_samples: Iterable[PlayerTrackSample],
    contacts: Iterable[ContactCandidate],
) -> dict[str, object]:
    samples = list(player_samples)
    tracks: dict[str, dict[int, PlayerTrackSample]] = {
        track_id: {} for track_id in selection.candidate_track_ids
    }
    for sample in samples:
        if sample.track_id in tracks:
            tracks[sample.track_id][sample.timestamp_ms] = sample

    pair_ratio, longest_conflict_ms = _same_lane_conflict_ratio(
        tracks[selection.learner_track_id], tracks[selection.partner_track_id]
    )
    if pair_ratio is None:
        pair_rotation = "unknown"
    elif pair_ratio >= 0.4 or longest_conflict_ms >= 500:
        pair_rotation = "same_lane_conflict"
    else:
        pair_rotation = "two_lanes_available"

    pair_ids = {selection.learner_track_id, selection.partner_track_id}
    pair_contacts = [
        contact for contact in contacts if pair_ids & set(contact.possible_track_ids)
    ]
    if pair_rotation == "same_lane_conflict":
        next_shot_role = "unclear"
    elif not pair_contacts:
        next_shot_role = "unknown"
    elif any(pair_ids <= set(contact.possible_track_ids) for contact in pair_contacts):
        next_shot_role = "unclear"
    else:
        next_shot_role = "assigned"

    missing = [
        "phase_observations.third_shot_role",
        "phase_observations.receive_result",
        "phase_observations.flick_response",
        "phase_observations.front_player_state",
        "phase_observations.rear_attack_next_shot",
        "phase_observations.defense_spacing",
        "phase_observations.transition_after_lift",
        "phase_observations.drill_form_ok_rally_breaks",
        "footwork_observations.recovery",
    ]
    if pair_rotation == "unknown":
        missing.append("phase_observations.pair_rotation")
    if next_shot_role == "unknown":
        missing.append("phase_observations.next_shot_role")

    return {
        "action": "mixed_doubles",
        "camera_view": "full_court_or_rear_diagonal",
        "participants": {
            "learner_track_id": selection.learner_track_id,
            "partner_track_id": selection.partner_track_id,
            "opponent_track_ids": list(selection.opponent_track_ids),
            "all_track_ids": list(selection.candidate_track_ids),
        },
        "court_calibration": {
            "corners": selection.court.to_dict(),
            "normalized_area": selection.court.area,
        },
        "phase_observations": {
            "pair_rotation": pair_rotation,
            "next_shot_role": next_shot_role,
        },
        "footwork_observations": {"recovery": "unknown"},
        "contact_candidates": [contact.to_dict() for contact in pair_contacts],
        "missing_observations": sorted(set(missing)),
        "keyframes": [],
    }
