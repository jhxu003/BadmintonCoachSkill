from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .phases import PoseSample


@dataclass(frozen=True)
class PoseTrack:
    samples: tuple[PoseSample, ...]
    camera_view: str
    limitations: tuple[str, ...]


class PoseEstimator(Protocol):
    def estimate(self, video_path: Path) -> PoseTrack:
        """Return selected-player, public-safe pose summaries for one video."""


def select_player_index(
    boxes: list[list[float]], previous_center: tuple[float, float] | None
) -> int:
    """Prefer a stable visible player track; fall back to the largest person at start/loss."""
    if not boxes:
        raise ValueError("At least one person box is required")

    def area(index: int) -> float:
        left, top, right, bottom = boxes[index]
        return max(right - left, 0.0) * max(bottom - top, 0.0)

    largest = max(range(len(boxes)), key=area)
    if previous_center is None:
        return largest

    def normalized_distance(index: int) -> float:
        left, top, right, bottom = boxes[index]
        center_x, center_y = (left + right) / 2, (top + bottom) / 2
        scale = max(((right - left) ** 2 + (bottom - top) ** 2) ** 0.5, 1.0)
        return ((center_x - previous_center[0]) ** 2 + (center_y - previous_center[1]) ** 2) ** 0.5 / scale

    nearest = min(range(len(boxes)), key=lambda index: (normalized_distance(index), -area(index)))
    return nearest if normalized_distance(nearest) <= 2.0 else largest


class UltralyticsPoseEstimator:
    """Lazy YOLO pose adapter; model loading only occurs in a GPU worker."""

    def __init__(self, model_path: str, inference_stride: int = 2):
        self.model_path = model_path
        self.inference_stride = max(inference_stride, 1)

    def estimate(self, video_path: Path) -> PoseTrack:
        try:
            import cv2
            from ultralytics import YOLO
        except ImportError as error:
            raise RuntimeError(
                "Ultralytics pose dependencies are unavailable in the active environment"
            ) from error

        model = YOLO(self.model_path)
        capture = cv2.VideoCapture(str(video_path))
        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        index = 0
        previous_center: tuple[float, float] | None = None
        samples: list[PoseSample] = []
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if index % self.inference_stride:
                    index += 1
                    continue
                result = model(frame, verbose=False)[0]
                if result.keypoints is None or result.boxes is None or len(result.boxes) == 0:
                    index += 1
                    continue
                boxes = result.boxes.xyxy.cpu().tolist()
                confidences = result.boxes.conf.cpu().tolist()
                selected = select_player_index(boxes, previous_center)
                keypoints = result.keypoints.xy[selected].cpu().tolist()
                point_confidence = result.keypoints.conf[selected].cpu().tolist()
                center = ((boxes[selected][0] + boxes[selected][2]) / 2, (boxes[selected][1] + boxes[selected][3]) / 2)
                motion = 0.0 if previous_center is None else ((center[0] - previous_center[0]) ** 2 + (center[1] - previous_center[1]) ** 2) ** 0.5
                previous_center = center
                scale = max(boxes[selected][3] - boxes[selected][1], 1.0)
                # COCO pose indices: shoulders 5/6, elbows 7/8, wrists 9/10.
                racket_side = 8 if point_confidence[8] >= point_confidence[7] else 7
                wrist_side = 10 if racket_side == 8 else 9
                samples.append(
                    PoseSample(
                        timestamp_ms=round(index * 1000 / fps),
                        left_shoulder_y=keypoints[5][1] / scale,
                        right_shoulder_y=keypoints[6][1] / scale,
                        racket_elbow_y=keypoints[racket_side][1] / scale,
                        racket_wrist_y=keypoints[wrist_side][1] / scale,
                        motion_score=motion / scale,
                        confidence=min(float(confidences[selected]), float(point_confidence[racket_side])),
                    )
                )
                index += 1
        finally:
            capture.release()
        return PoseTrack(
            samples=tuple(samples),
            camera_view="unknown",
            limitations=(
                "single_view_2d_pose_proxy",
                "racket_and_shuttle_visibility_not_guaranteed",
            ),
        )
