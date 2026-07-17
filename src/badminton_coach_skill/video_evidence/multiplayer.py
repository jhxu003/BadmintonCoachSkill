from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any


COURT_CORNER_NAMES = ("far_left", "far_right", "near_right", "near_left")


@dataclass(frozen=True)
class NormalizedPoint:
    x: float
    y: float

    def __post_init__(self) -> None:
        if not isfinite(self.x) or not isfinite(self.y):
            raise ValueError("court corner coordinates must be finite")
        if not 0.0 <= self.x <= 1.0 or not 0.0 <= self.y <= 1.0:
            raise ValueError("court corner coordinates must be normalized to [0, 1]")

    @classmethod
    def from_payload(cls, payload: Any) -> NormalizedPoint:
        if not isinstance(payload, dict):
            raise ValueError("each court corner must be an object with x and y")
        try:
            return cls(x=float(payload["x"]), y=float(payload["y"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("each court corner must contain numeric x and y") from error

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y}


def _cross(origin: NormalizedPoint, first: NormalizedPoint, second: NormalizedPoint) -> float:
    return (first.x - origin.x) * (second.y - origin.y) - (
        first.y - origin.y
    ) * (second.x - origin.x)


@dataclass(frozen=True)
class CourtCalibration:
    far_left: NormalizedPoint
    far_right: NormalizedPoint
    near_right: NormalizedPoint
    near_left: NormalizedPoint

    def __post_init__(self) -> None:
        points = self.points
        if len({(point.x, point.y) for point in points}) != 4:
            raise ValueError("court corners must be four distinct points")
        crosses = [
            _cross(points[index], points[(index + 1) % 4], points[(index + 2) % 4])
            for index in range(4)
        ]
        if any(abs(value) < 1e-6 for value in crosses) or not (
            all(value > 0 for value in crosses) or all(value < 0 for value in crosses)
        ):
            raise ValueError("court corners must form one convex quadrilateral")
        if self.area < 0.02:
            raise ValueError("court corner area is too small for calibration")

    @property
    def points(self) -> tuple[NormalizedPoint, ...]:
        return (self.far_left, self.far_right, self.near_right, self.near_left)

    @property
    def area(self) -> float:
        points = self.points
        signed_twice_area = sum(
            points[index].x * points[(index + 1) % 4].y
            - points[(index + 1) % 4].x * points[index].y
            for index in range(4)
        )
        return abs(signed_twice_area) / 2.0

    @classmethod
    def from_payload(cls, payload: Any) -> CourtCalibration:
        if not isinstance(payload, dict) or set(payload) != set(COURT_CORNER_NAMES):
            raise ValueError(
                "court_corners must contain far_left, far_right, near_right, and near_left"
            )
        points = {name: NormalizedPoint.from_payload(payload[name]) for name in COURT_CORNER_NAMES}
        return cls(**points)

    def to_dict(self) -> dict[str, dict[str, float]]:
        return {name: getattr(self, name).to_dict() for name in COURT_CORNER_NAMES}


@dataclass(frozen=True)
class ParticipantSelection:
    learner_track_id: str
    partner_track_id: str
    candidate_track_ids: tuple[str, ...]
    court: CourtCalibration

    def __post_init__(self) -> None:
        candidates = tuple(dict.fromkeys(self.candidate_track_ids))
        if len(candidates) != 4 or len(candidates) != len(self.candidate_track_ids):
            raise ValueError("mixed doubles setup requires exactly four distinct candidate tracks")
        if not self.learner_track_id or not self.partner_track_id:
            raise ValueError("learner and partner track ids are required")
        if self.learner_track_id == self.partner_track_id:
            raise ValueError("learner and partner tracks must be distinct")
        if self.learner_track_id not in candidates or self.partner_track_id not in candidates:
            raise ValueError("learner and partner must be selected from the four candidate tracks")

    @classmethod
    def from_payload(
        cls,
        *,
        learner_track_id: str,
        partner_track_id: str,
        candidate_track_ids: list[str] | tuple[str, ...],
        court_corners: Any,
    ) -> ParticipantSelection:
        return cls(
            learner_track_id=str(learner_track_id),
            partner_track_id=str(partner_track_id),
            candidate_track_ids=tuple(str(item) for item in candidate_track_ids),
            court=CourtCalibration.from_payload(court_corners),
        )

    @property
    def opponent_track_ids(self) -> tuple[str, str]:
        opponents = tuple(
            track_id
            for track_id in self.candidate_track_ids
            if track_id not in {self.learner_track_id, self.partner_track_id}
        )
        return opponents  # type: ignore[return-value]

    def to_dict(self) -> dict[str, object]:
        return {
            "learner_track_id": self.learner_track_id,
            "partner_track_id": self.partner_track_id,
            "opponent_track_ids": list(self.opponent_track_ids),
            "candidate_track_ids": list(self.candidate_track_ids),
            "court_corners": self.court.to_dict(),
            "court_area": self.court.area,
        }
