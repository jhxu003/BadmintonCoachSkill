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
from ..video_evidence.contracts import CoachReference, FrameRef
from ..video_evidence.worker import VideoEvidenceResult
from .database import Database
from .media_store import LocalMediaStore
from .models import AnalysisJob, MediaAsset


class VideoPipeline(Protocol):
    def __call__(self, video_path: Path, output_dir: Path, action: str) -> VideoEvidenceResult:
        """Analyze one private upload and write selected frames under output_dir."""


CatalogLoader = Callable[[str, Path], list[CoachReference]]
ReferenceMaterializer = Callable[[CoachReference, Path], CoachReference]


def _public_student_frame(frame: FrameRef) -> dict[str, object]:
    payload = frame.to_dict()
    payload.pop("media_key", None)
    return payload


def _public_coach_reference(reference: CoachReference) -> dict[str, object]:
    payload = reference.to_dict()
    payload.pop("media_key", None)
    payload["source_jump_url"] = source_timestamp_url(
        reference.source_url, reference.timestamp_ms
    )
    if reference.availability == "cached" and reference.media_key:
        payload["media_url"] = f"/api/coach-references/{reference.reference_id}/frame"
    return payload


def _student_media_key(job_id: str, relative_key: str) -> str:
    relative = Path(relative_key)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("Frame media key must be a relative path inside the analysis job")
    return str(Path(job_id) / relative)


def _retake_guidance(observation: dict[str, object], frames: Iterable[FrameRef]) -> str | None:
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
    if job.state in {"completed", "expired", "deleting"}:
        return job
    try:
        database.set_state(job.id, "normalizing", 8, "Preparing uploaded video.")
        upload = _upload_asset(database, job.id)
        video_path = media_store.resolve_key(upload.media_key)
        if not video_path.is_file():
            raise FileNotFoundError("The uploaded video file is unavailable")

        database.set_state(job.id, "tracking", 22, "Tracking visible learner movement.")
        output_dir = media_store.job_dir(job.id)
        evidence = pipeline(video_path, output_dir, job.action_hint or "unknown")

        database.set_state(job.id, "phase_candidates", 48, "Selecting action-phase keyframes.")
        student_frames = _persist_student_frames(database, media_store, job, evidence.frames)
        database.set_state(job.id, "visual_review", 62, "Reviewing visible movement evidence.")

        database.set_state(job.id, "diagnosing", 76, "Matching the selected coaching system.")
        profile = database.get_player_profile(job.id)
        knowledge = load_coach_knowledge(job.coach_id, project_root)
        catalog = catalog_loader(job.coach_id, project_root)
        initial_diagnosis = match_diagnosis(
            profile,
            evidence.observation,
            knowledge,
            student_frames=student_frames,
            coach_references=catalog,
        )

        database.set_state(job.id, "matching_references", 91, "Binding same-phase coaching references.")
        references = _materialize_matched_references(
            database=database,
            catalog=catalog,
            initial_diagnosis=initial_diagnosis,
            cache_root=coach_media_root or media_store.root.parent / "coach-media",
            materializer=reference_materializer,
        )
        diagnosis = match_diagnosis(
            profile,
            evidence.observation,
            knowledge,
            student_frames=student_frames,
            coach_references=references,
        )
        report = {
            **diagnosis,
            "frame_refs": [_public_student_frame(frame) for frame in student_frames],
            "coach_references": [_public_coach_reference(reference) for reference in references],
        }
        retake_guidance = _retake_guidance(evidence.observation, student_frames)
        if retake_guidance:
            report["retake_guidance"] = retake_guidance
        database.save_report(job.id, report)
        return database.set_state(job.id, "completed", 100, "Evidence report is ready.")
    except Exception as error:
        latest = database.get_job(job.id)
        if latest.state in {"expired", "deleting"}:
            return latest
        return database.set_state(
            job.id,
            "failed",
            latest.progress,
            "Analysis could not be completed. Please upload a clearer full-body video.",
            failure_code=type(error).__name__,
        )
