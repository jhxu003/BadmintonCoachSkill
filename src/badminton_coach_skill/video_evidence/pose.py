from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .phases import PoseSample


MIN_RACKET_JOINT_CONFIDENCE = 0.5


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
        previous_racket_joints: tuple[tuple[float, float], tuple[float, float]] | None = None
        previous_racket_side: int | None = None
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
                    previous_center = None
                    previous_racket_joints = None
                    previous_racket_side = None
                    index += 1
                    continue
                boxes = result.boxes.xyxy.cpu().tolist()
                confidences = result.boxes.conf.cpu().tolist()
                selected = select_player_index(boxes, previous_center)
                keypoints = result.keypoints.xy[selected].cpu().tolist()
                point_confidence = result.keypoints.conf[selected].cpu().tolist()
                left, top, right, bottom = boxes[selected]
                center = ((left + right) / 2, (top + bottom) / 2)
                scale = max(bottom - top, 1.0)
                if previous_center is not None:
                    track_distance = (
                        (center[0] - previous_center[0]) ** 2
                        + (center[1] - previous_center[1]) ** 2
                    ) ** 0.5 / scale
                    if track_distance > 2.0:
                        previous_racket_joints = None
                        previous_racket_side = None
                previous_center = center
                # COCO pose indices: shoulders 5/6, elbows 7/8, wrists 9/10.
                racket_side = previous_racket_side
                if racket_side is None:
                    left_joint_confidence = min(
                        float(point_confidence[7]), float(point_confidence[9])
                    )
                    right_joint_confidence = min(
                        float(point_confidence[8]), float(point_confidence[10])
                    )
                    racket_side = 8 if right_joint_confidence >= left_joint_confidence else 7
                wrist_side = 10 if racket_side == 8 else 9
                elbow_point = (
                    (keypoints[racket_side][0] - left) / scale,
                    (keypoints[racket_side][1] - top) / scale,
                )
                wrist_point = (
                    (keypoints[wrist_side][0] - left) / scale,
                    (keypoints[wrist_side][1] - top) / scale,
                )
                joint_confidence = min(
                    float(point_confidence[racket_side]), float(point_confidence[wrist_side])
                )
                motion = 0.0
                if joint_confidence >= MIN_RACKET_JOINT_CONFIDENCE and previous_racket_joints is not None:
                    motion = max(
                        ((elbow_point[0] - previous_racket_joints[0][0]) ** 2
                         + (elbow_point[1] - previous_racket_joints[0][1]) ** 2) ** 0.5,
                        ((wrist_point[0] - previous_racket_joints[1][0]) ** 2
                         + (wrist_point[1] - previous_racket_joints[1][1]) ** 2) ** 0.5,
                    )
                previous_racket_joints = (
                    (elbow_point, wrist_point)
                    if joint_confidence >= MIN_RACKET_JOINT_CONFIDENCE
                    else None
                )
                if (
                    previous_racket_side is None
                    and joint_confidence >= MIN_RACKET_JOINT_CONFIDENCE
                ):
                    previous_racket_side = racket_side
                samples.append(
                    PoseSample(
                        timestamp_ms=round(index * 1000 / fps),
                        left_shoulder_y=(keypoints[5][1] - top) / scale,
                        right_shoulder_y=(keypoints[6][1] - top) / scale,
                        racket_elbow_y=elbow_point[1],
                        racket_wrist_y=wrist_point[1],
                        motion_score=motion,
                        confidence=min(float(confidences[selected]), joint_confidence),
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
