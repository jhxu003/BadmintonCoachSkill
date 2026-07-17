from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Literal, Protocol

import numpy as np

from .multiplayer import ParticipantSelection
from .rally import (
    ContactCandidate,
    NormalizedBox,
    PlayerTrackSample,
    RallySegment,
    ShuttleHeatmapCandidate,
)


RallyModule = Literal[
    "serve_opening",
    "receive_opening_exchange",
    "frontcourt_pressure",
    "rear_attack",
    "rotation",
    "defense_transition",
    "reset_match_transfer",
]


@dataclass(frozen=True)
class ImagePlayerTrackSample:
    track_id: str
    timestamp_ms: int
    frame_index: int
    bbox: NormalizedBox
    confidence: float

    def __post_init__(self) -> None:
        if not self.track_id:
            raise ValueError("image track_id is required")
        if self.timestamp_ms < 0 or self.frame_index < 0:
            raise ValueError("track timestamps and frame indices must be non-negative")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("track confidence must be normalized")

    def to_dict(self) -> dict[str, object]:
        return {
            "track_id": self.track_id,
            "timestamp_ms": self.timestamp_ms,
            "frame_index": self.frame_index,
            "bbox": self.bbox.to_dict(),
            "confidence": self.confidence,
        }


class MultiPlayerTracker(Protocol):
    def track(self, video_path: Path) -> tuple[ImagePlayerTrackSample, ...]:
        """Return stable person tracks in normalized image coordinates."""


class UltralyticsMultiPlayerTracker:
    """Lazy ByteTrack adapter for four-player court footage."""

    def __init__(self, model_path: str, inference_stride: int = 1):
        self.model_path = model_path
        self.inference_stride = max(1, inference_stride)

    def track(self, video_path: Path) -> tuple[ImagePlayerTrackSample, ...]:
        try:
            import cv2
            from ultralytics import YOLO
        except ImportError as error:
            raise RuntimeError(
                "Ultralytics tracking dependencies are unavailable in the GPU worker"
            ) from error
        capture = cv2.VideoCapture(str(video_path))
        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        capture.release()
        model = YOLO(self.model_path)
        samples: list[ImagePlayerTrackSample] = []
        results = model.track(
            source=str(video_path),
            stream=True,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            vid_stride=self.inference_stride,
            verbose=False,
        )
        for result_index, result in enumerate(results):
            if result.boxes is None or result.boxes.id is None:
                continue
            height, width = result.orig_shape
            boxes = result.boxes.xyxy.cpu().tolist()
            track_ids = result.boxes.id.int().cpu().tolist()
            confidences = result.boxes.conf.cpu().tolist()
            frame_index = result_index * self.inference_stride
            timestamp_ms = round(frame_index * 1000 / fps)
            for track_id, box, confidence in zip(
                track_ids, boxes, confidences, strict=True
            ):
                left, top, right, bottom = box
                normalized_left = max(0.0, min(1.0, float(left) / max(width, 1)))
                normalized_top = max(0.0, min(1.0, float(top) / max(height, 1)))
                normalized_right = max(
                    normalized_left + 1e-6,
                    min(1.0, float(right) / max(width, 1)),
                )
                normalized_bottom = max(
                    normalized_top + 1e-6,
                    min(1.0, float(bottom) / max(height, 1)),
                )
                samples.append(
                    ImagePlayerTrackSample(
                        track_id=f"track-{int(track_id)}",
                        timestamp_ms=timestamp_ms,
                        frame_index=frame_index,
                        bbox=NormalizedBox(
                            normalized_left,
                            normalized_top,
                            normalized_right - normalized_left,
                            normalized_bottom - normalized_top,
                        ),
                        confidence=float(confidence),
                    )
                )
        return tuple(samples)


@dataclass(frozen=True)
class PlayerCandidate:
    track_id: str
    bbox: NormalizedBox
    confidence: float
    visible_sample_count: int

    def __post_init__(self) -> None:
        if not self.track_id:
            raise ValueError("player candidate track_id is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("player candidate confidence must be normalized")
        if self.visible_sample_count <= 0:
            raise ValueError("player candidate must have a visible sample")

    def to_dict(self) -> dict[str, object]:
        return {
            "track_id": self.track_id,
            "bbox": self.bbox.to_dict(),
            "confidence": self.confidence,
            "visible_sample_count": self.visible_sample_count,
        }


@dataclass(frozen=True)
class PlayerDiscoveryResult:
    frame_media_key: str
    timestamp_ms: int
    width: int
    height: int
    players: tuple[PlayerCandidate, ...]

    def __post_init__(self) -> None:
        if not self.frame_media_key:
            raise ValueError("selection frame media key is required")
        if self.timestamp_ms < 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("selection frame metadata is invalid")
        if len(self.players) != 4 or len({player.track_id for player in self.players}) != 4:
            raise ValueError("player discovery must expose exactly four distinct tracks")


def select_four_player_candidates(
    samples: tuple[ImagePlayerTrackSample, ...] | list[ImagePlayerTrackSample],
) -> tuple[int, int, tuple[PlayerCandidate, ...]]:
    """Choose four persistent tracks and one frame where all are visible."""
    if not samples:
        raise ValueError("No player tracks were detected")
    grouped: dict[str, list[ImagePlayerTrackSample]] = defaultdict(list)
    for sample in samples:
        grouped[sample.track_id].append(sample)
    ranked_tracks = sorted(
        grouped,
        key=lambda track_id: (
            -len(grouped[track_id]),
            -(sum(item.confidence for item in grouped[track_id]) / len(grouped[track_id])),
            track_id,
        ),
    )[:4]
    if len(ranked_tracks) != 4:
        raise ValueError("Four persistent player tracks are required")

    by_frame: dict[tuple[int, int], dict[str, ImagePlayerTrackSample]] = defaultdict(dict)
    for sample in samples:
        if sample.track_id in ranked_tracks:
            key = (sample.timestamp_ms, sample.frame_index)
            existing = by_frame[key].get(sample.track_id)
            if existing is None or sample.confidence > existing.confidence:
                by_frame[key][sample.track_id] = sample
    shared_frames = [
        (key, visible)
        for key, visible in by_frame.items()
        if set(visible) == set(ranked_tracks)
    ]
    if not shared_frames:
        raise ValueError("No frame contains all four persistent player tracks")
    (timestamp_ms, frame_index), visible = min(
        shared_frames,
        key=lambda item: (
            -sum(sample.confidence for sample in item[1].values()),
            item[0][0],
            item[0][1],
        ),
    )
    players = tuple(
        PlayerCandidate(
            track_id=track_id,
            bbox=visible[track_id].bbox,
            confidence=sum(item.confidence for item in grouped[track_id])
            / len(grouped[track_id]),
            visible_sample_count=len(grouped[track_id]),
        )
        for track_id in sorted(ranked_tracks)
    )
    return timestamp_ms, frame_index, players


def _homography(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    rows: list[list[float]] = []
    values: list[float] = []
    for (x, y), (u, v) in zip(source, target, strict=True):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        values.append(u)
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        values.append(v)
    coefficients = np.linalg.solve(np.asarray(rows), np.asarray(values))
    return np.append(coefficients, 1.0).reshape(3, 3)


def project_player_tracks_to_court(
    samples: tuple[ImagePlayerTrackSample, ...] | list[ImagePlayerTrackSample],
    selection: ParticipantSelection,
) -> tuple[PlayerTrackSample, ...]:
    source = np.asarray(
        [(point.x, point.y) for point in selection.court.points], dtype=np.float64
    )
    target = np.asarray(
        [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
        dtype=np.float64,
    )
    matrix = _homography(source, target)
    projected: list[PlayerTrackSample] = []
    for sample in samples:
        if sample.track_id not in selection.candidate_track_ids:
            continue
        foot_x = sample.bbox.x + sample.bbox.width / 2
        foot_y = sample.bbox.y + sample.bbox.height
        homogeneous = matrix @ np.asarray([foot_x, foot_y, 1.0])
        if abs(homogeneous[2]) < 1e-9:
            continue
        court_x = float(homogeneous[0] / homogeneous[2])
        court_y = float(homogeneous[1] / homogeneous[2])
        if not -0.15 <= court_x <= 1.15 or not -0.15 <= court_y <= 1.15:
            continue
        projected.append(
            PlayerTrackSample(
                track_id=sample.track_id,
                timestamp_ms=sample.timestamp_ms,
                bbox=sample.bbox,
                court_x=max(0.0, min(1.0, court_x)),
                court_y=max(0.0, min(1.0, court_y)),
                confidence=sample.confidence,
            )
        )
    return tuple(projected)


@dataclass(frozen=True)
class RallyFrameRef:
    frame_id: str
    module: RallyModule
    timestamp_ms: int
    caption: str
    confidence: Literal["low", "medium", "high"]
    media_key: str
    visible_facts: tuple[str, ...] = ()
    limitations: tuple[str, ...] = (
        "single_view_2d_rally_proxy",
        "exact_shuttle_contact_not_claimed",
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_id": self.frame_id,
            "module": self.module,
            "timestamp_ms": self.timestamp_ms,
            "caption": self.caption,
            "confidence": self.confidence,
            "media_key": self.media_key,
            "visible_facts": list(self.visible_facts),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class MixedDoublesEvidence:
    player_samples: tuple[PlayerTrackSample, ...]
    shuttle_candidates: tuple[ShuttleHeatmapCandidate, ...]
    contact_candidates: tuple[ContactCandidate, ...]
    rallies: tuple[RallySegment, ...]
    rally_frames: tuple[RallyFrameRef, ...]

    def public_payload(self, selection: ParticipantSelection) -> dict[str, object]:
        counts = Counter(sample.track_id for sample in self.player_samples)
        confidence_values: dict[str, list[float]] = defaultdict(list)
        for sample in self.player_samples:
            confidence_values[sample.track_id].append(sample.confidence)
        track_summaries = [
            {
                "track_id": track_id,
                "role": (
                    "learner"
                    if track_id == selection.learner_track_id
                    else "partner"
                    if track_id == selection.partner_track_id
                    else "opponent"
                ),
                "sample_count": counts.get(track_id, 0),
                "mean_confidence": (
                    sum(confidence_values[track_id]) / len(confidence_values[track_id])
                    if confidence_values[track_id]
                    else 0.0
                ),
            }
            for track_id in selection.candidate_track_ids
        ]
        shuttle = list(self.shuttle_candidates)
        if len(shuttle) > 240:
            stride = max(1, len(shuttle) // 240)
            public_shuttle = shuttle[::stride][:240]
        else:
            public_shuttle = shuttle
        return {
            "tracked_player_count": sum(1 for item in track_summaries if item["sample_count"]),
            "player_tracks": track_summaries,
            "shuttle_candidate_count": len(shuttle),
            "shuttle_track_sample": [candidate.to_dict() for candidate in public_shuttle],
            "contact_candidates": [candidate.to_dict() for candidate in self.contact_candidates],
            "rallies": [rally.to_dict() for rally in self.rallies],
            "limitations": [
                "four_player_tracks_are_user_confirmed_identity_hypotheses",
                "shuttle_positions_are_temporal_heatmap_candidates",
                "exact_shuttle_contact_not_claimed",
                "tactical_intent_not_inferred",
            ],
        }


RALLY_MODULE_ORDER: tuple[RallyModule, ...] = (
    "serve_opening",
    "receive_opening_exchange",
    "frontcourt_pressure",
    "rear_attack",
    "rotation",
    "defense_transition",
    "reset_match_transfer",
)
RALLY_MODULE_CAPTIONS: dict[RallyModule, str] = {
    "serve_opening": "发球与开局候选：观察发球后两人的第三拍准备，不把此帧当作完整战术结论。",
    "receive_opening_exchange": "接发与开局交换候选：观察接发线路之后谁准备下一拍。",
    "frontcourt_pressure": "前场压迫候选：观察前场球员是否保持可拦截通道和持拍准备。",
    "rear_attack": "后场进攻候选：观察进攻选择、落地与下一拍可用性。",
    "rotation": "轮转候选：观察两人是否进入同一通道以及下一拍归属是否清楚。",
    "defense_transition": "防守转换候选：观察获得时间后是否重建两条可达通道。",
    "reset_match_transfer": "回位与实战迁移候选：观察本拍结束后是否恢复到下一角色。",
}
RALLY_MODULE_PHASES = {
    "serve_opening": "preparation",
    "receive_opening_exchange": "start",
    "frontcourt_pressure": "arrival",
    "rear_attack": "contact_window",
    "rotation": "follow_through",
    "defense_transition": "arrival",
    "reset_match_transfer": "recovery",
}


def select_rally_module_anchors(
    shuttle_candidates: tuple[ShuttleHeatmapCandidate, ...]
    | list[ShuttleHeatmapCandidate],
) -> tuple[tuple[RallyModule, ShuttleHeatmapCandidate], ...]:
    """Select seven ordered review anchors without asserting seven proven events."""
    ordered = sorted(shuttle_candidates, key=lambda candidate: candidate.timestamp_ms)
    if len(ordered) < len(RALLY_MODULE_ORDER):
        return ()
    last = len(ordered) - 1
    indices = [round(index * last / (len(RALLY_MODULE_ORDER) - 1)) for index in range(7)]
    return tuple(
        (module, ordered[index])
        for module, index in zip(RALLY_MODULE_ORDER, indices, strict=True)
    )
