from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .contracts import FrameRef
from .ffmpeg import extract_frame
from .phases import PhaseCandidate, PoseSample, select_phase_candidates
from .pose import PoseEstimator
from .vlm_review import DisabledVisualReviewer, VisualReview, VisualReviewer


@dataclass(frozen=True)
class VideoEvidenceResult:
    observation: dict[str, object]
    frames: tuple[FrameRef, ...]
    candidates: tuple[PhaseCandidate, ...]


def _shoulder_line(sample: PoseSample) -> float | None:
    shoulders = [
        value
        for value in (sample.left_shoulder_y, sample.right_shoulder_y)
        if value is not None
    ]
    return sum(shoulders) / len(shoulders) if shoulders else None


def _elbow_observation(sample: PoseSample | None) -> tuple[str, tuple[str, ...]]:
    if sample is None or sample.racket_elbow_y is None:
        return "unknown", ()
    shoulder = _shoulder_line(sample)
    if shoulder is None:
        return "unknown", ()
    if sample.racket_elbow_y > shoulder + 0.04:
        return "below_shoulder", ("elbow_below_shoulder",)
    return "near_shoulder", ("elbow_near_shoulder_height",)


def build_observation_and_frames(
    action: str,
    candidates: Iterable[PhaseCandidate],
    samples_by_timestamp: dict[int, PoseSample],
    frame_media_keys: dict[int, str],
    camera_view: str,
    reviewer: VisualReviewer | None = None,
    image_paths: dict[int, Path] | None = None,
) -> tuple[dict[str, object], list[FrameRef]]:
    """Convert selected candidate frames into a bounded Skill observation payload."""
    visual_reviewer = reviewer or DisabledVisualReviewer()
    selected = list(candidates)
    missing: list[str] = [
        "contact_point",
        "wrist_elbow_sequence",
        "hip_shoulder_sequence",
        "racket_side_structure",
        "follow_through",
    ]
    reviewed_candidates: list[tuple[PhaseCandidate, str, VisualReview]] = []
    rejected_non_action = False
    for index, candidate in enumerate(selected, start=1):
        frame_id = f"student-{candidate.phase}-{candidate.timestamp_ms}-{index}"
        media_key = frame_media_keys.get(candidate.timestamp_ms)
        if not media_key:
            continue
        image_path = image_paths.get(candidate.timestamp_ms) if image_paths else None
        review = visual_reviewer.review(candidate, image_path or Path(media_key), frame_id)
        if review.phase_assessment != "plausible":
            rejected_non_action = True
            continue
        reviewed_candidates.append((candidate, media_key, review))

    top_elbow_candidate = next(
        (candidate for candidate, _, _ in reviewed_candidates if candidate.phase == "top_elbow"),
        None,
    )
    elbow_height, elbow_facts = _elbow_observation(
        samples_by_timestamp.get(top_elbow_candidate.timestamp_ms)
        if top_elbow_candidate
        else None
    )
    keyframes: list[dict[str, object]] = []
    frames: list[FrameRef] = []
    for index, (candidate, media_key, review) in enumerate(reviewed_candidates, start=1):
        frame_id = f"student-{candidate.phase}-{candidate.timestamp_ms}-{index}"
        phase_facts = elbow_facts if candidate.phase == "top_elbow" else ()
        facts = tuple(dict.fromkeys((*phase_facts, *review.visible_facts)))
        limitations = tuple(
            dict.fromkeys(
                (*review.limitations, "exact_shuttle_contact_not_visible", "calibrated_3d_biomechanics_not_available")
            )
        )
        frames.append(
            FrameRef(
                frame_id=frame_id,
                owner="student",
                phase=candidate.phase,
                timestamp_ms=candidate.timestamp_ms,
                media_key=media_key,
                confidence=candidate.confidence,
                visible_facts=facts,
                limitations=limitations,
                camera_view=review.camera_view if review.camera_view != "unknown" else camera_view,
            )
        )
        keyframes.append(
            {
                "label": candidate.phase,
                "time_ms": candidate.timestamp_ms,
                "frame_id": frame_id,
                "phase": candidate.phase,
                "media_key": media_key,
                "confidence": candidate.confidence,
                "visible_facts": list(facts),
                "limitations": list(limitations),
            }
        )
    if top_elbow_candidate is None:
        missing.append("elbow_height_before_hit")
    if rejected_non_action and not reviewed_candidates:
        missing.append("action_phase_evidence")
    return (
        {
            "action": action,
            "camera_view": camera_view,
            "fps_quality": "derived_from_video_pipeline",
            "phase_observations": {},
            "contact_point": "unknown",
            "elbow_height_before_hit": elbow_height,
            "wrist_elbow_sequence": "unknown",
            "hip_shoulder_sequence": "unknown",
            "racket_side_structure": "unknown",
            "follow_through": "unknown",
            "footwork_observations": {},
            "missing_observations": sorted(set(missing)),
            "keyframes": keyframes,
        },
        frames,
    )


def analyze_video(
    video_path: Path,
    output_dir: Path,
    action: str,
    pose_estimator: PoseEstimator,
    frame_extractor: Callable[[Path, int, Path], None] = extract_frame,
    reviewer: VisualReviewer | None = None,
) -> VideoEvidenceResult:
    """Extract bounded phase evidence from one already-normalized student video."""
    track = pose_estimator.estimate(video_path)
    candidates = select_phase_candidates(list(track.samples), action)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_media_keys: dict[int, str] = {}
    image_paths: dict[int, Path] = {}
    for candidate in candidates:
        if candidate.timestamp_ms in frame_media_keys:
            continue
        filename = f"{candidate.phase}-{candidate.timestamp_ms}.jpg"
        relative_key = str(Path("frames") / filename)
        target = output_dir / relative_key
        frame_extractor(video_path, candidate.timestamp_ms, target)
        frame_media_keys[candidate.timestamp_ms] = relative_key
        image_paths[candidate.timestamp_ms] = target
    observation, frames = build_observation_and_frames(
        action=action,
        candidates=candidates,
        samples_by_timestamp={sample.timestamp_ms: sample for sample in track.samples},
        frame_media_keys=frame_media_keys,
        camera_view=track.camera_view,
        reviewer=reviewer,
        image_paths=image_paths,
    )
    return VideoEvidenceResult(
        observation=observation,
        frames=tuple(frames),
        candidates=tuple(candidates),
    )
