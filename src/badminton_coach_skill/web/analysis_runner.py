from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from ..coach_media.catalog import build_source_catalog
from ..coach_media.ingestion import ensure_reference_image
from ..coach_media.links import source_timestamp_url
from ..coach_registry import load_coach_knowledge
from ..issue_matcher import match_diagnosis
from ..video_evidence.contracts import ActionPackageSegment, CoachReference, FrameRef
from ..video_evidence.phases import ACTION_PACKAGE_STAGE_OFFSETS_MS
from ..video_evidence.worker import VideoEvidenceResult
from .database import Database, utcnow
from .jobs import expire_jobs
from .media_store import LocalMediaStore
from .models import AnalysisJob, JobState, MediaAsset


class VideoPipeline(Protocol):
    def __call__(self, video_path: Path, output_dir: Path, action: str) -> VideoEvidenceResult:
        """Analyze one private upload and write selected frames under output_dir."""


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
            database, media_store, job.id, "tracking", 22, "Tracking visible learner movement."
        )
        if stopped is not None:
            return stopped
        output_dir = media_store.job_dir(job.id)
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
            action_package=tuple(action_package),
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
            action_package=tuple(action_package),
        )
        report = {
            **diagnosis,
            "frame_refs": [_public_student_frame(frame) for frame in student_frames],
            "action_package": [
                _public_action_segment(segment, job.id) for segment in action_package
            ],
            "action_package_missing_phases": _missing_action_package_phases(
                action_package
            ),
            "coach_references": [
                _public_coach_reference(reference, job.id) for reference in references
            ],
        }
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
