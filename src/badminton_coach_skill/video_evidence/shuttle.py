from __future__ import annotations

from collections.abc import Iterable
from collections import deque
from pathlib import Path
from typing import Protocol

import numpy as np

from .rally import ShuttleHeatmapCandidate


class ShuttleDetector(Protocol):
    def detect(self, video_path: Path) -> tuple[ShuttleHeatmapCandidate, ...]:
        """Return temporal heatmap candidates in normalized image coordinates."""


def decode_heatmap_peaks(
    heatmap: np.ndarray,
    *,
    threshold: float = 0.35,
    max_peaks: int = 3,
    suppression_radius: int = 1,
) -> tuple[
    tuple[float, float, float] | None,
    tuple[tuple[float, float, float], ...],
]:
    """Decode one TrackNet-style heatmap into a primary point and alternatives."""
    values = np.asarray(heatmap, dtype=np.float32)
    if values.ndim != 2 or values.size == 0:
        raise ValueError("heatmap must be a non-empty 2D array")
    height, width = values.shape
    ranked = sorted(
        (
            (float(values[y, x]), x, y)
            for y, x in np.argwhere(values >= threshold)
        ),
        key=lambda item: (-item[0], item[2], item[1]),
    )
    selected: list[tuple[float, int, int]] = []
    for confidence, x, y in ranked:
        if any(
            abs(x - selected_x) <= suppression_radius
            and abs(y - selected_y) <= suppression_radius
            for _, selected_x, selected_y in selected
        ):
            continue
        selected.append((confidence, x, y))
        if len(selected) >= max(1, max_peaks):
            break
    if not selected:
        return None, ()

    def normalized(item: tuple[float, int, int]) -> tuple[float, float, float]:
        confidence, x, y = item
        return (
            x / max(width - 1, 1),
            y / max(height - 1, 1),
            confidence,
        )

    return normalized(selected[0]), tuple(normalized(item) for item in selected[1:])


def interpolate_short_shuttle_gaps(
    candidates: Iterable[ShuttleHeatmapCandidate],
    *,
    frame_interval_ms: int,
    maximum_missing_frames: int = 2,
) -> list[ShuttleHeatmapCandidate]:
    """Fill only short internal gaps and label every synthetic point as occluded."""
    if frame_interval_ms <= 0:
        raise ValueError("frame_interval_ms must be positive")
    ordered = sorted(candidates, key=lambda candidate: candidate.timestamp_ms)
    if len(ordered) < 2:
        return ordered
    filled: list[ShuttleHeatmapCandidate] = [ordered[0]]
    for previous, following in zip(ordered, ordered[1:], strict=False):
        missing = round((following.timestamp_ms - previous.timestamp_ms) / frame_interval_ms) - 1
        if 0 < missing <= maximum_missing_frames:
            for index in range(1, missing + 1):
                fraction = index / (missing + 1)
                timestamp_ms = previous.timestamp_ms + frame_interval_ms * index
                filled.append(
                    ShuttleHeatmapCandidate(
                        candidate_id=f"shuttle-interpolated-{timestamp_ms}",
                        timestamp_ms=timestamp_ms,
                        x=previous.x + (following.x - previous.x) * fraction,
                        y=previous.y + (following.y - previous.y) * fraction,
                        confidence=min(previous.confidence, following.confidence) * 0.5,
                        occluded=True,
                        interpolated=True,
                    )
                )
        filled.append(following)
    return filled


class TemporalHeatmapShuttleDetector:
    """Lazy TorchScript adapter for TrackNet-style temporal heatmaps.

    The private model must accept `[B, 3*T, H, W]` RGB frame stacks and return
    `[B, H, W]` or `[B, C, H, W]` heatmaps. Model weights remain outside Git.
    """

    def __init__(
        self,
        model_path: str,
        *,
        input_width: int = 512,
        input_height: int = 288,
        temporal_frames: int = 3,
        confidence_threshold: float = 0.35,
        batch_size: int = 32,
        maximum_missing_frames: int = 2,
    ):
        self.model_path = model_path
        self.input_width = max(64, input_width)
        self.input_height = max(64, input_height)
        self.temporal_frames = max(3, temporal_frames)
        self.confidence_threshold = max(0.0, min(1.0, confidence_threshold))
        self.batch_size = max(1, batch_size)
        self.maximum_missing_frames = max(0, maximum_missing_frames)

    @staticmethod
    def _heatmaps(output: object, torch_module: object) -> object:
        torch = torch_module
        if isinstance(output, dict):
            output = output.get("heatmap", next(iter(output.values())))
        if isinstance(output, (tuple, list)):
            output = output[0]
        if not torch.is_tensor(output):
            raise ValueError("TrackNet-style model output must be a tensor")
        if output.ndim == 4:
            output = output[:, output.shape[1] // 2]
        elif output.ndim != 3:
            raise ValueError("TrackNet-style model output must have 3 or 4 dimensions")
        if float(output.min()) < 0.0 or float(output.max()) > 1.0:
            output = output.sigmoid()
        return output

    def detect(self, video_path: Path) -> tuple[ShuttleHeatmapCandidate, ...]:
        if not self.model_path or not Path(self.model_path).is_file():
            raise RuntimeError("BADMINTON_SHUTTLE_MODEL_PATH must point to a private TorchScript model")
        try:
            import cv2
            import torch
        except ImportError as error:
            raise RuntimeError(
                "OpenCV and PyTorch are required in the GPU worker for shuttle detection"
            ) from error
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = torch.jit.load(self.model_path, map_location=device).eval()
        capture = cv2.VideoCapture(str(video_path))
        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        frame_interval_ms = max(1, round(1000 / fps))
        window: deque[np.ndarray] = deque(maxlen=self.temporal_frames)
        pending_tensors: list[np.ndarray] = []
        pending_timestamps: list[int] = []
        candidates: list[ShuttleHeatmapCandidate] = []
        frame_index = 0

        def infer_batch() -> None:
            if not pending_tensors:
                return
            tensor = torch.from_numpy(np.stack(pending_tensors)).to(device=device, dtype=torch.float32)
            with torch.inference_mode():
                output = self._heatmaps(model(tensor), torch)
            for timestamp_ms, heatmap in zip(
                pending_timestamps, output.detach().cpu().numpy(), strict=True
            ):
                primary, alternatives = decode_heatmap_peaks(
                    heatmap,
                    threshold=self.confidence_threshold,
                    max_peaks=3,
                )
                if primary is None:
                    continue
                x, y, confidence = primary
                candidates.append(
                    ShuttleHeatmapCandidate(
                        candidate_id=f"shuttle-{timestamp_ms}",
                        timestamp_ms=timestamp_ms,
                        x=x,
                        y=y,
                        confidence=confidence,
                        alternatives=alternatives,
                    )
                )
            pending_tensors.clear()
            pending_timestamps.clear()

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                rgb = cv2.cvtColor(
                    cv2.resize(frame, (self.input_width, self.input_height)),
                    cv2.COLOR_BGR2RGB,
                )
                window.append(np.transpose(rgb, (2, 0, 1)).astype(np.float32) / 255.0)
                if len(window) == self.temporal_frames:
                    pending_tensors.append(np.concatenate(tuple(window), axis=0))
                    pending_timestamps.append(round(frame_index * 1000 / fps))
                    if len(pending_tensors) >= self.batch_size:
                        infer_batch()
                frame_index += 1
            infer_batch()
        finally:
            capture.release()
        return tuple(
            interpolate_short_shuttle_gaps(
                candidates,
                frame_interval_ms=frame_interval_ms,
                maximum_missing_frames=self.maximum_missing_frames,
            )
        )
