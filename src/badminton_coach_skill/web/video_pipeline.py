from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Callable

import yaml

from ..video_evidence.contracts import FrameRef
from ..video_evidence.ffmpeg import extract_frame, normalize_video
from ..video_evidence.multiplayer import ParticipantSelection
from ..video_evidence.multiplayer_pipeline import (
    ImagePlayerTrackSample,
    MixedDoublesEvidence,
    MultiPlayerTracker,
    PlayerDiscoveryResult,
    RALLY_MODULE_CAPTIONS,
    RALLY_MODULE_PHASES,
    RallyFrameRef,
    UltralyticsMultiPlayerTracker,
    project_player_tracks_to_court,
    select_four_player_candidates,
    select_rally_module_anchors,
)
from ..video_evidence.pose import PoseEstimator, UltralyticsPoseEstimator
from ..video_evidence.rally import (
    NormalizedBox,
    build_contact_candidates,
    build_mixed_doubles_observation,
    segment_rallies,
)
from ..video_evidence.shuttle import (
    ShuttleDetector,
    TemporalHeatmapShuttleDetector,
)
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
    visual_review_max_new_tokens: int
    multiplayer_pose_model_path: str = "yolo11n-pose.pt"
    multiplayer_inference_stride: int = 2
    multiplayer_inference_size: int = 640
    shuttle_model_path: str = ""
    shuttle_input_width: int = 512
    shuttle_input_height: int = 288
    shuttle_temporal_frames: int = 3
    shuttle_background_mode: str = ""
    shuttle_confidence_threshold: float = 0.35


def load_video_pipeline_config(path: Path) -> VideoPipelineConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    analysis = payload.get("analysis", {})
    pose = payload.get("pose", {})
    multiplayer = payload.get("multiplayer", {})
    shuttle = payload.get("shuttle", {})
    visual_review = payload.get("visual_review", {})
    if (
        not isinstance(analysis, dict)
        or not isinstance(pose, dict)
        or not isinstance(multiplayer, dict)
        or not isinstance(shuttle, dict)
        or not isinstance(visual_review, dict)
    ):
        raise ValueError("Video analysis configuration sections must be mappings")
    return VideoPipelineConfig(
        normalized_fps=max(1, int(analysis.get("normalized_fps", 30))),
        max_width=max(320, int(analysis.get("max_width", 1280))),
        pose_model_path=str(pose.get("model_path", "yolo11n-pose.pt")),
        pose_inference_stride=max(1, int(pose.get("inference_stride", 2))),
        visual_review_provider=str(visual_review.get("provider", "disabled")),
        visual_review_model_path=str(visual_review.get("model_path", "")),
        visual_review_max_new_tokens=max(96, int(visual_review.get("max_new_tokens", 256))),
        multiplayer_pose_model_path=str(
            multiplayer.get("pose_model_path", pose.get("model_path", "yolo11n-pose.pt"))
        ),
        multiplayer_inference_stride=max(
            1, int(multiplayer.get("inference_stride", pose.get("inference_stride", 2)))
        ),
        multiplayer_inference_size=max(320, int(multiplayer.get("inference_size", 640))),
        shuttle_model_path=str(shuttle.get("model_path", "")),
        shuttle_input_width=max(64, int(shuttle.get("input_width", 512))),
        shuttle_input_height=max(64, int(shuttle.get("input_height", 288))),
        shuttle_temporal_frames=max(3, int(shuttle.get("temporal_frames", 3))),
        shuttle_background_mode=str(shuttle.get("background_mode", "")),
        shuttle_confidence_threshold=max(
            0.0, min(1.0, float(shuttle.get("confidence_threshold", 0.35)))
        ),
    )


class ConfiguredVideoPipeline:
    """GPU-worker pipeline that normalizes uploads before extracting phase evidence."""

    def __init__(
        self,
        *,
        config: VideoPipelineConfig,
        pose_estimator: PoseEstimator,
        multiplayer_tracker: MultiPlayerTracker | None = None,
        shuttle_detector: ShuttleDetector | None = None,
        reviewer: VisualReviewer | None = None,
        normalizer: Callable[[Path, Path, int, int], object] = normalize_video,
        frame_extractor: Callable[[Path, int, Path], None] | None = None,
    ):
        self.config = config
        self.pose_estimator = pose_estimator
        self.multiplayer_tracker = multiplayer_tracker
        self.shuttle_detector = shuttle_detector
        self.reviewer = reviewer or DisabledVisualReviewer()
        self.normalizer = normalizer
        self.frame_extractor = frame_extractor or extract_frame

    def _normalized_video(self, video_path: Path, output_dir: Path) -> tuple[Path, object | None]:
        normalized = output_dir / "normalized.mp4"
        if normalized.is_file():
            return normalized, None
        metadata = self.normalizer(
            video_path,
            normalized,
            self.config.normalized_fps,
            self.config.max_width,
        )
        return normalized, metadata

    @staticmethod
    def _track_cache(output_dir: Path) -> Path:
        return output_dir / "private" / "player-tracks.json"

    def _save_track_cache(
        self, output_dir: Path, samples: tuple[ImagePlayerTrackSample, ...]
    ) -> None:
        cache = self._track_cache(output_dir)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps([sample.to_dict() for sample in samples], ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_track_cache(self, output_dir: Path) -> tuple[ImagePlayerTrackSample, ...]:
        cache = self._track_cache(output_dir)
        if not cache.is_file():
            raise FileNotFoundError("Private four-player track cache is unavailable")
        payload = json.loads(cache.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Private player track cache is invalid")
        return tuple(
            ImagePlayerTrackSample(
                track_id=str(item["track_id"]),
                timestamp_ms=int(item["timestamp_ms"]),
                frame_index=int(item["frame_index"]),
                bbox=NormalizedBox(**item["bbox"]),
                confidence=float(item["confidence"]),
            )
            for item in payload
        )

    def discover_players(
        self, video_path: Path, output_dir: Path
    ) -> PlayerDiscoveryResult:
        if self.multiplayer_tracker is None:
            raise RuntimeError("Four-player tracker is not configured")
        normalized, metadata = self._normalized_video(video_path, output_dir)
        samples = self.multiplayer_tracker.track(normalized)
        self._save_track_cache(output_dir, samples)
        timestamp_ms, _, players = select_four_player_candidates(samples)
        relative_key = str(Path("selection") / f"players-{timestamp_ms}.jpg")
        self.frame_extractor(normalized, timestamp_ms, output_dir / relative_key)
        width = int(getattr(metadata, "width", self.config.max_width))
        height = int(getattr(metadata, "height", round(width * 9 / 16)))
        return PlayerDiscoveryResult(
            frame_media_key=relative_key,
            timestamp_ms=timestamp_ms,
            width=width,
            height=height,
            players=players,
        )

    def analyze_mixed_doubles(
        self,
        video_path: Path,
        output_dir: Path,
        selection: ParticipantSelection,
    ) -> VideoEvidenceResult:
        if self.shuttle_detector is None:
            raise RuntimeError("TrackNet-style shuttle detector is not configured")
        normalized, _ = self._normalized_video(video_path, output_dir)
        image_tracks = self._load_track_cache(output_dir)
        player_samples = project_player_tracks_to_court(image_tracks, selection)
        shuttle_candidates = self.shuttle_detector.detect(normalized)
        contacts = tuple(build_contact_candidates(shuttle_candidates, player_samples))
        rallies = tuple(segment_rallies(shuttle_candidates, minimum_candidates=3))
        observation = build_mixed_doubles_observation(
            selection=selection,
            player_samples=player_samples,
            contacts=contacts,
        )
        rally_frames: list[RallyFrameRef] = []
        student_frames: list[FrameRef] = []
        keyframes: list[dict[str, object]] = []
        for module, anchor in select_rally_module_anchors(shuttle_candidates):
            relative_key = str(
                Path("rally-frames") / f"{module}-{anchor.timestamp_ms}.jpg"
            )
            self.frame_extractor(normalized, anchor.timestamp_ms, output_dir / relative_key)
            confidence = (
                "high" if anchor.confidence >= 0.8 else "medium" if anchor.confidence >= 0.55 else "low"
            )
            frame_id = f"student-rally-{module}-{anchor.timestamp_ms}"
            visible_facts = (
                f"module_review_candidate:{module}",
                "four_player_tracks_available",
                "shuttle_temporal_heatmap_candidate_available",
            )
            rally_frame = RallyFrameRef(
                frame_id=frame_id,
                module=module,
                timestamp_ms=anchor.timestamp_ms,
                caption=RALLY_MODULE_CAPTIONS[module],
                confidence=confidence,
                media_key=relative_key,
                visible_facts=visible_facts,
            )
            rally_frames.append(rally_frame)
            student_frames.append(
                FrameRef(
                    frame_id=frame_id,
                    owner="student",
                    phase=RALLY_MODULE_PHASES[module],  # type: ignore[arg-type]
                    timestamp_ms=anchor.timestamp_ms,
                    media_key=relative_key,
                    confidence=confidence,
                    visible_facts=visible_facts,
                    limitations=rally_frame.limitations,
                    camera_view="full_court_or_rear_diagonal",
                )
            )
            keyframes.append(
                {
                    "label": module,
                    "time_ms": anchor.timestamp_ms,
                    "frame_id": frame_id,
                    "caption": rally_frame.caption,
                    "confidence": confidence,
                    "limitations": list(rally_frame.limitations),
                }
            )
        observation["keyframes"] = keyframes
        return VideoEvidenceResult(
            observation=observation,
            frames=tuple(student_frames),
            candidates=(),
            action_package=(),
            multiplayer=MixedDoublesEvidence(
                player_samples=player_samples,
                shuttle_candidates=tuple(shuttle_candidates),
                contact_candidates=contacts,
                rallies=rallies,
                rally_frames=tuple(rally_frames),
            ),
        )

    def __call__(self, video_path: Path, output_dir: Path, action: str) -> VideoEvidenceResult:
        normalized, _ = self._normalized_video(video_path, output_dir)
        kwargs: dict[str, object] = {
            "video_path": normalized,
            "output_dir": output_dir,
            "action": action,
            "pose_estimator": self.pose_estimator,
            "reviewer": self.reviewer,
        }
        kwargs["frame_extractor"] = self.frame_extractor
        return analyze_video(**kwargs)  # type: ignore[arg-type]


def create_default_video_pipeline(project_root: Path) -> ConfiguredVideoPipeline:
    config = load_video_pipeline_config(project_root / "configs" / "video-analysis.yaml")
    pose_estimator = UltralyticsPoseEstimator(
        os.environ.get("BADMINTON_POSE_MODEL_PATH", config.pose_model_path),
        inference_stride=config.pose_inference_stride,
    )
    reviewer: VisualReviewer
    if config.visual_review_provider == "qwen_local":
        reviewer = QwenLocalVisualReviewer(
            os.environ.get("BADMINTON_VLM_MODEL_PATH", config.visual_review_model_path),
            max_new_tokens=config.visual_review_max_new_tokens,
        )
    else:
        reviewer = DisabledVisualReviewer()
    multiplayer_tracker = UltralyticsMultiPlayerTracker(
        os.environ.get(
            "BADMINTON_MULTIPLAYER_POSE_MODEL_PATH",
            config.multiplayer_pose_model_path,
        ),
        inference_stride=config.multiplayer_inference_stride,
        inference_size=config.multiplayer_inference_size,
    )
    shuttle_detector = TemporalHeatmapShuttleDetector(
        os.environ.get("BADMINTON_SHUTTLE_MODEL_PATH", config.shuttle_model_path),
        input_width=config.shuttle_input_width,
        input_height=config.shuttle_input_height,
        temporal_frames=config.shuttle_temporal_frames,
        background_mode=config.shuttle_background_mode,
        confidence_threshold=config.shuttle_confidence_threshold,
    )
    return ConfiguredVideoPipeline(
        config=config,
        pose_estimator=pose_estimator,
        multiplayer_tracker=multiplayer_tracker,
        shuttle_detector=shuttle_detector,
        reviewer=reviewer,
    )
