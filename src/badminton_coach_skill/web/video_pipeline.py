from __future__ import annotations

from dataclasses import dataclass
import gc
import json
import os
from pathlib import Path
from typing import Callable

import yaml

from ..video_evidence.contracts import FrameRef
from ..video_evidence.agent import (
    ActionRoute,
    ActionRouter,
    DisabledActionRouter,
    DisabledSegmentObserver,
    SegmentObserver,
    prefix_evidence,
)
from ..video_evidence.ffmpeg import extract_clip, extract_frame, normalize_video
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
    QwenLocalActionRouter,
    QwenLocalSegmentObserver,
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
    agent_router_provider: str = "disabled"
    agent_router_model_path: str = ""
    agent_observer_provider: str = "disabled"
    agent_observer_model_path: str = ""
    agent_route_confidence_threshold: float = 0.8
    agent_max_units: int = 5
    agent_router_max_samples: int = 12
    agent_observer_frames_per_phase: int = 1
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
    agent = payload.get("agent", {})
    if (
        not isinstance(analysis, dict)
        or not isinstance(pose, dict)
        or not isinstance(multiplayer, dict)
        or not isinstance(shuttle, dict)
        or not isinstance(visual_review, dict)
        or not isinstance(agent, dict)
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
        agent_router_provider=str(agent.get("router_provider", "disabled")),
        agent_router_model_path=str(agent.get("router_model_path", "")),
        agent_observer_provider=str(agent.get("observer_provider", "disabled")),
        agent_observer_model_path=str(agent.get("observer_model_path", "")),
        agent_route_confidence_threshold=max(
            0.0, min(1.0, float(agent.get("route_confidence_threshold", 0.8)))
        ),
        agent_max_units=max(1, min(5, int(agent.get("max_units", 5)))),
        agent_router_max_samples=max(4, min(16, int(agent.get("router_max_samples", 12)))),
        agent_observer_frames_per_phase=max(
            1, min(3, int(agent.get("observer_frames_per_phase", 1)))
        ),
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
        agent_router: ActionRouter | None = None,
        agent_observer: SegmentObserver | None = None,
        normalizer: Callable[[Path, Path, int, int], object] = normalize_video,
        frame_extractor: Callable[[Path, int, Path], None] | None = None,
    ):
        self.config = config
        self.pose_estimator = pose_estimator
        self.multiplayer_tracker = multiplayer_tracker
        self.shuttle_detector = shuttle_detector
        self.reviewer = reviewer or DisabledVisualReviewer()
        self.agent_router = agent_router or DisabledActionRouter()
        self.agent_observer = agent_observer or DisabledSegmentObserver()
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
        raw_shuttle_candidates = self.shuttle_detector.detect(normalized)
        # TrackNet-style models can produce visually convincing high scores on
        # scoreboards, banners or spectators.  Mixed-doubles navigation is
        # more useful as an explicit "unknown" than as a fabricated rally, so
        # retain only peaks projected on the manually confirmed court surface.
        # This deliberately rejects high-lift points above the far baseline;
        # callers must request a clearer recording rather than infer them.
        shuttle_candidates = tuple(
            candidate
            for candidate in raw_shuttle_candidates
            if selection.court.contains_image_point(candidate.x, candidate.y)
        )
        contacts = tuple(build_contact_candidates(shuttle_candidates, player_samples))
        rallies = tuple(segment_rallies(shuttle_candidates, minimum_candidates=3))
        observation = build_mixed_doubles_observation(
            selection=selection,
            player_samples=player_samples,
            contacts=contacts,
        )
        observation["shuttle_candidate_filter"] = {
            "raw_candidate_count": len(raw_shuttle_candidates),
            "court_surface_candidate_count": len(shuttle_candidates),
            "policy": "outside_court_peaks_rejected_as_insufficient_evidence",
        }
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

    def route_agent(self, video_path: Path, output_dir: Path) -> tuple[ActionRoute, ...]:
        """Run the low-memory local routing tier and release it before pose/7B."""
        normalized, _ = self._normalized_video(video_path, output_dir)
        try:
            routes = self.agent_router.route(normalized, output_dir)
        finally:
            self.agent_router.close()
        # The runner records and rejects low-confidence proposals explicitly;
        # suppressing them here would make a retake outcome look like an empty
        # video rather than an honest confidence boundary.
        return tuple(route for route in routes if isinstance(route, ActionRoute))

    def analyze_agent_route(
        self,
        video_path: Path,
        output_dir: Path,
        route: ActionRoute,
        allowed_values: dict[str, tuple[str, ...]],
    ) -> tuple[VideoEvidenceResult, dict[str, object]]:
        """Analyze one routed unit without borrowing another action's peak."""
        normalized, _ = self._normalized_video(video_path, output_dir)
        relative_root = Path("agent-units") / route.unit_id
        unit_root = output_dir / relative_root
        context_video = unit_root / "private" / "context.mp4"
        extract_clip(normalized, route.start_ms, route.end_ms, context_video)
        raw_evidence = analyze_video(
            video_path=context_video,
            output_dir=unit_root,
            action=route.action,
            pose_estimator=self.pose_estimator,
            reviewer=DisabledVisualReviewer(),
            frame_extractor=self.frame_extractor,
        )
        evidence = prefix_evidence(raw_evidence, route.unit_id, relative_root)
        image_paths: list[Path] = []
        offsets = (0,)
        if self.config.agent_observer_frames_per_phase == 3:
            offsets = (-180, 0, 180)
        elif self.config.agent_observer_frames_per_phase == 2:
            offsets = (-140, 140)
        for segment in raw_evidence.action_package:
            for offset_ms in offsets:
                timestamp_ms = max(segment.start_ms, min(segment.end_ms - 1, segment.anchor_ms + offset_ms))
                image_path = unit_root / "private" / "observation" / f"{segment.phase}-{timestamp_ms}.jpg"
                self.frame_extractor(context_video, timestamp_ms, image_path)
                image_paths.append(image_path)
        # ``analyze_video`` creates the YOLO model inside the pose adapter. It
        # is now out of scope; release cached allocations before loading Qwen
        # 7B so the tiers can run on a single modest GPU.
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        try:
            observed = self.agent_observer.observe(
                action=route.action,
                image_paths=tuple(image_paths),
                base_observation=dict(evidence.observation),
                allowed_values=allowed_values,
            )
        finally:
            self.agent_observer.close()
        return evidence, observed


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
    if config.agent_router_provider == "qwen_local" and config.agent_router_model_path:
        agent_router: ActionRouter = QwenLocalActionRouter(
            os.environ.get("BADMINTON_AGENT_ROUTER_MODEL_PATH", config.agent_router_model_path),
            max_new_tokens=config.visual_review_max_new_tokens,
            maximum_samples=config.agent_router_max_samples,
            maximum_units=config.agent_max_units,
        )
    else:
        agent_router = DisabledActionRouter()
    if config.agent_observer_provider == "qwen_local" and config.agent_observer_model_path:
        agent_observer: SegmentObserver = QwenLocalSegmentObserver(
            os.environ.get("BADMINTON_AGENT_OBSERVER_MODEL_PATH", config.agent_observer_model_path),
            max_new_tokens=max(320, config.visual_review_max_new_tokens),
        )
    else:
        agent_observer = DisabledSegmentObserver()
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
        # Keep deployment-specific checkpoint geometry out of versioned YAML.
        # TrackNet checkpoints encode their own temporal contract (for example
        # the verified public v3 checkpoint uses 8 RGB frames plus a median
        # background), while the bundled private model currently uses 4.
        # Operators must set these variables together with the private model
        # path when their checkpoint differs from the repository default.
        input_width=max(
            64,
            int(
                os.environ.get(
                    "BADMINTON_SHUTTLE_INPUT_WIDTH", config.shuttle_input_width
                )
            ),
        ),
        input_height=max(
            64,
            int(
                os.environ.get(
                    "BADMINTON_SHUTTLE_INPUT_HEIGHT", config.shuttle_input_height
                )
            ),
        ),
        temporal_frames=max(
            3,
            int(
                os.environ.get(
                    "BADMINTON_SHUTTLE_TEMPORAL_FRAMES",
                    config.shuttle_temporal_frames,
                )
            ),
        ),
        background_mode=os.environ.get(
            "BADMINTON_SHUTTLE_BACKGROUND_MODE", config.shuttle_background_mode
        ),
        confidence_threshold=max(
            0.0,
            min(
                1.0,
                float(
                    os.environ.get(
                        "BADMINTON_SHUTTLE_CONFIDENCE_THRESHOLD",
                        config.shuttle_confidence_threshold,
                    )
                ),
            ),
        ),
    )
    return ConfiguredVideoPipeline(
        config=config,
        pose_estimator=pose_estimator,
        multiplayer_tracker=multiplayer_tracker,
        shuttle_detector=shuttle_detector,
        reviewer=reviewer,
        agent_router=agent_router,
        agent_observer=agent_observer,
    )
