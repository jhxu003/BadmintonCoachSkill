from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from ..coach_media.catalog import build_source_catalog
from ..coach_media.ingestion import ensure_reference_image
from ..coach_media.links import source_timestamp_url
from ..coach_registry import load_coach_knowledge
from ..issue_matcher import match_diagnosis
from ..video_evidence.contracts import ActionPackageSegment, CoachReference, FrameRef
from ..video_evidence.multiplayer import ParticipantSelection
from ..video_evidence.multiplayer_pipeline import (
    PlayerDiscoveryResult,
    RallyFrameRef,
)
from ..video_evidence.phases import ACTION_PACKAGE_STAGE_OFFSETS_MS
from ..video_evidence.worker import VideoEvidenceResult
from .database import Database, utcnow
from .jobs import expire_jobs
from .media_store import LocalMediaStore
from .models import AnalysisJob, JobState, MediaAsset


class VideoPipeline(Protocol):
    def __call__(self, video_path: Path, output_dir: Path, action: str) -> VideoEvidenceResult:
        """Analyze one private upload and write selected frames under output_dir."""

    def discover_players(
        self, video_path: Path, output_dir: Path
    ) -> PlayerDiscoveryResult:
        """Find four stable player candidates and a private selection frame."""

    def analyze_mixed_doubles(
        self,
        video_path: Path,
        output_dir: Path,
        selection: ParticipantSelection,
    ) -> VideoEvidenceResult:
        """Analyze four confirmed player tracks plus shuttle heatmap candidates."""


CatalogLoader = Callable[[str, Path], list[CoachReference]]
ReferenceMaterializer = Callable[[CoachReference, Path], CoachReference]


def _public_student_frame(frame: FrameRef) -> dict[str, object]:
    payload = frame.to_dict()
    payload.pop("media_key", None)
    return payload


def _public_action_segment(
    segment: ActionPackageSegment, analysis_id: str
) -> dict[str, object]:
    payload = segment.to_dict()
    payload.pop("media_key", None)
    if segment.media_key:
        payload["media_url"] = (
            f"/api/analyses/{analysis_id}/segments/{segment.segment_id}"
        )
    return payload


def _public_coach_reference(reference: CoachReference, analysis_id: str) -> dict[str, object]:
    payload = reference.to_dict()
    payload.pop("media_key", None)
    payload["source_jump_url"] = source_timestamp_url(
        reference.source_url, reference.timestamp_ms
    )
    if reference.availability == "cached" and reference.media_key:
        payload["media_url"] = (
            f"/api/coach-references/{reference.reference_id}/frame?analysis_id={analysis_id}"
        )
    payload.pop("clip_media_key", None)
    if reference.availability == "cached" and reference.clip_media_key:
        payload["clip_media_url"] = (
            f"/api/coach-references/{reference.reference_id}/clip?analysis_id={analysis_id}"
        )
    return payload


def _student_media_key(job_id: str, relative_key: str) -> str:
    relative = Path(relative_key)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("Frame media key must be a relative path inside the analysis job")
    return str(Path(job_id) / relative)


ACTION_PACKAGE_PHASE_LABELS = {
    "preparation": "启动与后退",
    "start": "最后两步与制动",
    "arrival": "引拍、侧身与起跳准备",
    "top_elbow": "架拍",
    "contact_window": "腾空与击球附近",
    "follow_through": "随挥与落地",
    "recovery": "回位",
}


def _missing_action_package_phases(
    action_package: Iterable[ActionPackageSegment],
) -> list[str]:
    available = {segment.phase for segment in action_package if segment.media_key}
    return [
        phase
        for phase, _ in ACTION_PACKAGE_STAGE_OFFSETS_MS
        if phase not in available
    ]


def _retake_guidance(
    observation: dict[str, object],
    frames: Iterable[FrameRef],
    action_package: Iterable[ActionPackageSegment],
) -> str | None:
    missing_phases = _missing_action_package_phases(action_package)
    if missing_phases:
        missing_labels = "、".join(
            ACTION_PACKAGE_PHASE_LABELS[phase] for phase in missing_phases
        )
        return (
            f"本次视频没有连续覆盖：{missing_labels}。"
            "请用侧后方机位，保持全身和持拍侧清晰可见，从启动、后退、最后两步、起跳、挥拍、落地到回位完整重拍一次。"
        )
    if any(True for _ in frames):
        return None
    action = str(observation.get("action", "动作"))
    camera_view = str(observation.get("camera_view", "unknown"))
    if action in {"smash", "high_clear", "drop"}:
        view = "侧后方"
    elif camera_view == "front":
        view = "侧后方"
    else:
        view = "侧后方或侧面"
    return f"请用{view}机位重拍一次{action}：全身和持拍侧保持清晰可见，从启动、到位、挥拍到回位连续拍摄，不要只截击球瞬间。"


def _mixed_doubles_retake_guidance(
    multiplayer_payload: dict[str, object], rally_frames: Iterable[RallyFrameRef]
) -> str | None:
    if int(multiplayer_payload.get("tracked_player_count", 0)) < 4:
        return "请用固定全场机位重拍：四名球员从脚到头都保持可见，避免场边人员遮挡或进入球场区域。"
    if int(multiplayer_payload.get("shuttle_candidate_count", 0)) == 0:
        return "请用固定全场机位重拍完整回合：提高快门与画面清晰度，确保白色羽球在背景和灯光下可辨。"
    if not any(True for _ in rally_frames):
        return "请保留发球前到回合结束的完整回合，并确保四名球员、场地边线和羽球同时可见。"
    return None


def _upload_asset(database: Database, job_id: str) -> MediaAsset:
    uploads = database.list_media_assets(job_id, kind="upload")
    if not uploads:
        raise FileNotFoundError("The uploaded video asset is unavailable")
    return uploads[0]


def _stop_if_media_was_deleted(
    database: Database, media_store: LocalMediaStore, job_id: str
) -> AnalysisJob | None:
    latest = database.get_job(job_id)
    if latest.expires_at <= utcnow() and latest.state not in {"deleting", "expired"}:
        expire_jobs(database, media_store, now=utcnow())
        latest = database.get_job(job_id)
    if latest.state not in {"deleting", "expired"}:
        return None
    media_store.delete_job(job_id)
    database.delete_media_assets(job_id)
    return database.get_job(job_id)


def _advance_active_job(
    database: Database,
    media_store: LocalMediaStore,
    job_id: str,
    state: JobState,
    progress: int,
    message: str,
) -> AnalysisJob | None:
    updated = database.set_active_state(job_id, state, progress, message)
    if updated is not None:
        return None
    return _stop_if_media_was_deleted(database, media_store, job_id) or database.get_job(job_id)


def _persist_student_frames(
    database: Database,
    media_store: LocalMediaStore,
    job: AnalysisJob,
    frames: Iterable[FrameRef],
) -> list[FrameRef]:
    persisted: list[FrameRef] = []
    for frame in frames:
        if frame.owner != "student":
            continue
        media_key = _student_media_key(job.id, frame.media_key)
        if not media_store.resolve_key(media_key).is_file():
            continue
        existing = database.find_media_asset(job.id, frame.frame_id)
        if existing is None:
            database.add_media_asset(
                MediaAsset(
                    id=frame.frame_id,
                    job_id=job.id,
                    media_key=media_key,
                    kind="student_frame",
                    expires_at=job.expires_at,
                )
            )
        persisted.append(frame)
    return persisted


def _persist_action_package(
    database: Database,
    media_store: LocalMediaStore,
    job: AnalysisJob,
    segments: Iterable[ActionPackageSegment],
) -> list[ActionPackageSegment]:
    persisted: list[ActionPackageSegment] = []
    for segment in segments:
        media_key = _student_media_key(job.id, segment.media_key)
        if not media_store.resolve_key(media_key).is_file():
            continue
        existing = database.find_media_asset(job.id, segment.segment_id)
        if existing is None:
            database.add_media_asset(
                MediaAsset(
                    id=segment.segment_id,
                    job_id=job.id,
                    media_key=media_key,
                    kind="student_segment",
                    expires_at=job.expires_at,
                )
            )
        persisted.append(segment)
    return persisted


def _persist_player_discovery(
    database: Database,
    media_store: LocalMediaStore,
    job: AnalysisJob,
    discovery: PlayerDiscoveryResult,
) -> None:
    media_key = _student_media_key(job.id, discovery.frame_media_key)
    if not media_store.resolve_key(media_key).is_file():
        raise FileNotFoundError("The mixed-doubles selection frame is unavailable")
    asset_id = str(uuid4())
    database.add_media_asset(
        MediaAsset(
            id=asset_id,
            job_id=job.id,
            media_key=media_key,
            kind="selection_frame",
            expires_at=job.expires_at,
        )
    )
    database.save_analysis_setup_candidates(
        job.id,
        {
            "frame_asset_id": asset_id,
            "timestamp_ms": discovery.timestamp_ms,
            "width": discovery.width,
            "height": discovery.height,
            "players": [player.to_dict() for player in discovery.players],
        },
    )


def _persist_rally_frames(
    database: Database,
    media_store: LocalMediaStore,
    job: AnalysisJob,
    frames: Iterable[RallyFrameRef],
) -> list[RallyFrameRef]:
    persisted: list[RallyFrameRef] = []
    for frame in frames:
        media_key = _student_media_key(job.id, frame.media_key)
        if not media_store.resolve_key(media_key).is_file():
            continue
        if database.find_media_asset(job.id, frame.frame_id) is None:
            database.add_media_asset(
                MediaAsset(
                    id=frame.frame_id,
                    job_id=job.id,
                    media_key=media_key,
                    kind="student_frame",
                    expires_at=job.expires_at,
                )
            )
        persisted.append(frame)
    return persisted


def _public_rally_frame(frame: RallyFrameRef, analysis_id: str) -> dict[str, object]:
    payload = frame.to_dict()
    payload.pop("media_key", None)
    payload["media_url"] = (
        f"/api/analyses/{analysis_id}/frames/{frame.frame_id}"
    )
    return payload


def _selection_from_setup(setup: dict[str, object]) -> ParticipantSelection | None:
    raw = setup.get("selection")
    if not isinstance(raw, dict):
        return None
    return ParticipantSelection.from_payload(
        learner_track_id=str(raw.get("learner_track_id", "")),
        partner_track_id=str(raw.get("partner_track_id", "")),
        candidate_track_ids=tuple(str(item) for item in raw.get("candidate_track_ids", [])),
        court_corners=raw.get("court_corners"),
    )


def _materialize_matched_references(
    *,
    database: Database,
    catalog: list[CoachReference],
    initial_diagnosis: dict[str, object],
    cache_root: Path,
    materializer: ReferenceMaterializer,
) -> list[CoachReference]:
    catalog_by_id = {reference.reference_id: reference for reference in catalog}
    selected_ids: list[str] = []
    for evidence in initial_diagnosis.get("issue_evidence", []):
        if not isinstance(evidence, dict):
            continue
        selected_ids.extend(str(reference_id) for reference_id in evidence.get("coach_reference_ids", []))

    materialized: list[CoachReference] = []
    for reference_id in dict.fromkeys(selected_ids):
        reference = catalog_by_id.get(reference_id)
        if reference is None:
            continue
        try:
            cached = materializer(reference, cache_root)
        except Exception:
            cached = replace(
                reference,
                availability="unavailable",
                media_key="",
                limitations=tuple(
                    dict.fromkeys((*reference.limitations, "source_acquisition_failed"))
                ),
            )
        database.save_coach_reference(cached)
        materialized.append(cached)
    return materialized


def run_analysis_job(
    *,
    database: Database,
    media_store: LocalMediaStore,
    project_root: Path,
    job_id: str,
    pipeline: VideoPipeline,
    catalog_loader: CatalogLoader = build_source_catalog,
    coach_media_root: Path | None = None,
    reference_materializer: ReferenceMaterializer = ensure_reference_image,
) -> AnalysisJob:
    """Execute a queued analysis outside the HTTP request and persist a public-safe report."""
    job = database.get_job(job_id)
    stopped = _stop_if_media_was_deleted(database, media_store, job.id)
    if stopped is not None or job.state == "completed":
        return stopped or job
    claimed = database.claim_analysis_job(job.id)
    if claimed is None:
        return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)
    job = claimed
    try:
        upload = _upload_asset(database, job.id)
        video_path = media_store.resolve_key(upload.media_key)
        if not video_path.is_file():
            raise FileNotFoundError("The uploaded video file is unavailable")

        stopped = _advance_active_job(
            database,
            media_store,
            job.id,
            "tracking",
            22,
            "Tracking four visible players."
            if job.action_hint == "mixed_doubles"
            else "Tracking visible learner movement.",
        )
        if stopped is not None:
            return stopped
        output_dir = media_store.job_dir(job.id)
        selection: ParticipantSelection | None = None
        if job.action_hint == "mixed_doubles":
            setup = database.get_analysis_setup(job.id) or {}
            selection = _selection_from_setup(setup)
            if selection is None:
                discover = getattr(pipeline, "discover_players", None)
                if not callable(discover):
                    raise RuntimeError("Mixed-doubles player discovery is unavailable")
                discovery = discover(video_path, output_dir)
                _persist_player_discovery(database, media_store, job, discovery)
                waiting = database.set_active_state(
                    job.id,
                    "needs_player_selection",
                    30,
                    "Select the learner, partner, and four court corners.",
                )
                if waiting is not None:
                    return waiting
                return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)
            analyze_mixed = getattr(pipeline, "analyze_mixed_doubles", None)
            if not callable(analyze_mixed):
                raise RuntimeError("Mixed-doubles analysis is unavailable")
            evidence = analyze_mixed(video_path, output_dir, selection)
        else:
            evidence = pipeline(video_path, output_dir, job.action_hint or "unknown")
        deleted = _stop_if_media_was_deleted(database, media_store, job.id)
        if deleted is not None:
            return deleted

        stopped = _advance_active_job(
            database, media_store, job.id, "phase_candidates", 48, "Selecting action-phase keyframes."
        )
        if stopped is not None:
            return stopped
        student_frames = _persist_student_frames(database, media_store, job, evidence.frames)
        action_package = _persist_action_package(
            database, media_store, job, evidence.action_package
        )
        rally_frames = _persist_rally_frames(
            database,
            media_store,
            job,
            evidence.multiplayer.rally_frames if evidence.multiplayer else (),
        )
        deleted = _stop_if_media_was_deleted(database, media_store, job.id)
        if deleted is not None:
            return deleted
        stopped = _advance_active_job(
            database, media_store, job.id, "visual_review", 62, "Reviewing visible movement evidence."
        )
        if stopped is not None:
            return stopped

        stopped = _advance_active_job(
            database, media_store, job.id, "diagnosing", 76, "Matching the selected coaching system."
        )
        if stopped is not None:
            return stopped
        profile = database.get_player_profile(job.id)
        knowledge = load_coach_knowledge(job.coach_id, project_root)
        catalog = catalog_loader(job.coach_id, project_root)
        deleted = _stop_if_media_was_deleted(database, media_store, job.id)
        if deleted is not None:
            return deleted
        initial_diagnosis = match_diagnosis(
            profile,
            evidence.observation,
            knowledge,
            student_frames=student_frames,
            coach_references=catalog,
            action_package=None if selection is not None else tuple(action_package),
        )

        stopped = _advance_active_job(
            database, media_store, job.id, "matching_references", 91, "Binding same-phase coaching references."
        )
        if stopped is not None:
            return stopped
        references = _materialize_matched_references(
            database=database,
            catalog=catalog,
            initial_diagnosis=initial_diagnosis,
            cache_root=coach_media_root or media_store.root.parent / "coach-media",
            materializer=reference_materializer,
        )
        deleted = _stop_if_media_was_deleted(database, media_store, job.id)
        if deleted is not None:
            return deleted
        diagnosis = match_diagnosis(
            profile,
            evidence.observation,
            knowledge,
            student_frames=student_frames,
            coach_references=references,
            action_package=None if selection is not None else tuple(action_package),
        )
        report = {
            **diagnosis,
            "frame_refs": [_public_student_frame(frame) for frame in student_frames],
            "action_package": [
                _public_action_segment(segment, job.id) for segment in action_package
            ],
            "action_package_missing_phases": (
                []
                if selection is not None
                else _missing_action_package_phases(action_package)
            ),
            "coach_references": [
                _public_coach_reference(reference, job.id) for reference in references
            ],
        }
        if selection is not None and evidence.multiplayer is not None:
            report["participants"] = selection.to_dict()
            multiplayer_payload = evidence.multiplayer.public_payload(selection)
            report["multiplayer_evidence"] = multiplayer_payload
            report["rally_frames"] = [
                _public_rally_frame(frame, job.id) for frame in rally_frames
            ]
            retake_guidance = _mixed_doubles_retake_guidance(
                multiplayer_payload, rally_frames
            )
        else:
            retake_guidance = _retake_guidance(
                evidence.observation, student_frames, action_package
            )
        if retake_guidance:
            report["retake_guidance"] = retake_guidance
        if not database.save_report_if_active(job.id, report):
            return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)
        completed = database.set_active_state(job.id, "completed", 100, "Evidence report is ready.")
        if completed is not None:
            return completed
        return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)
    except Exception as error:
        stopped = _stop_if_media_was_deleted(database, media_store, job.id)
        if stopped is not None:
            return stopped
        failed = database.set_active_state(
            job.id,
            "failed",
            database.get_job(job.id).progress,
            "Analysis could not be completed. Please upload a clearer full-body video.",
            failure_code=type(error).__name__,
        )
        return failed or database.get_job(job.id)
