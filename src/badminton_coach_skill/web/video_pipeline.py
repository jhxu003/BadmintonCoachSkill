from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from ..video_evidence.ffmpeg import normalize_video
from ..video_evidence.pose import PoseEstimator, UltralyticsPoseEstimator
from ..video_evidence.vlm_review import (
    DisabledVisualReviewer,
    QwenLocalVisualReviewer,
    VisualReviewer,
)
from ..video_evidence.worker import VideoEvidenceResult, analyze_video


@dataclass(frozen=True)
class VideoPipelineConfig:
    normalized_fps: int
    max_width: int
    pose_model_path: str
    pose_inference_stride: int
    visual_review_provider: str
    visual_review_model_path: str


def load_video_pipeline_config(path: Path) -> VideoPipelineConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    analysis = payload.get("analysis", {})
    pose = payload.get("pose", {})
    visual_review = payload.get("visual_review", {})
    if not isinstance(analysis, dict) or not isinstance(pose, dict) or not isinstance(visual_review, dict):
        raise ValueError("Video analysis configuration sections must be mappings")
    return VideoPipelineConfig(
        normalized_fps=max(1, int(analysis.get("normalized_fps", 30))),
        max_width=max(320, int(analysis.get("max_width", 1280))),
        pose_model_path=str(pose.get("model_path", "yolo11n-pose.pt")),
        pose_inference_stride=max(1, int(pose.get("inference_stride", 2))),
        visual_review_provider=str(visual_review.get("provider", "disabled")),
        visual_review_model_path=str(visual_review.get("model_path", "")),
    )


class ConfiguredVideoPipeline:
    """GPU-worker pipeline that normalizes uploads before extracting phase evidence."""

    def __init__(
        self,
        *,
        config: VideoPipelineConfig,
        pose_estimator: PoseEstimator,
        reviewer: VisualReviewer | None = None,
        normalizer: Callable[[Path, Path, int, int], object] = normalize_video,
        frame_extractor: Callable[[Path, int, Path], None] | None = None,
    ):
        self.config = config
        self.pose_estimator = pose_estimator
        self.reviewer = reviewer or DisabledVisualReviewer()
        self.normalizer = normalizer
        self.frame_extractor = frame_extractor

    def __call__(self, video_path: Path, output_dir: Path, action: str) -> VideoEvidenceResult:
        normalized = output_dir / "normalized.mp4"
        self.normalizer(
            video_path,
            normalized,
            self.config.normalized_fps,
            self.config.max_width,
        )
        kwargs: dict[str, object] = {
            "video_path": normalized,
            "output_dir": output_dir,
            "action": action,
            "pose_estimator": self.pose_estimator,
            "reviewer": self.reviewer,
        }
        if self.frame_extractor is not None:
            kwargs["frame_extractor"] = self.frame_extractor
        return analyze_video(**kwargs)  # type: ignore[arg-type]


def create_default_video_pipeline(project_root: Path) -> ConfiguredVideoPipeline:
    config = load_video_pipeline_config(project_root / "configs" / "video-analysis.yaml")
    pose_estimator = UltralyticsPoseEstimator(
        config.pose_model_path,
        inference_stride=config.pose_inference_stride,
    )
    reviewer: VisualReviewer
    if config.visual_review_provider == "qwen_local":
        reviewer = QwenLocalVisualReviewer(config.visual_review_model_path)
    else:
        reviewer = DisabledVisualReviewer()
    return ConfiguredVideoPipeline(
        config=config,
        pose_estimator=pose_estimator,
        reviewer=reviewer,
    )
