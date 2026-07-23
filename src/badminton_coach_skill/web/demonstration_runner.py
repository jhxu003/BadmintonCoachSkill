from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ..coach_media.catalog import build_source_catalog
from ..coach_media.demonstrations import DemonstrationQuery, build_demonstration_plan
from ..coach_media.ingestion import ensure_demonstration_media
from ..coach_registry import load_coach_knowledge
from ..video_evidence.contracts import CoachReference
from .analysis_runner import (
    CatalogLoader,
    ReferenceMaterializer,
    _public_coach_reference,
    _stop_if_media_was_deleted,
)
from .database import Database
from .media_store import LocalMediaStore
from .models import AnalysisJob


def _query_from_profile(job: AnalysisJob, profile: dict[str, object]) -> DemonstrationQuery:
    return DemonstrationQuery(
        coach_id=job.coach_id,
        action=str(profile.get("action", job.action_hint or "")),
        phase=str(profile.get("phase", "preparation")),  # type: ignore[arg-type]
        training_goal=str(profile.get("training_goal", "")),
        level=str(profile.get("level", "beginner")),
        framework_id=str(profile.get("framework_id", "")),
        limit=int(profile.get("limit", 2)),
    )


def run_demonstration_job(
    *,
    database: Database,
    media_store: LocalMediaStore,
    project_root: Path,
    job_id: str,
    catalog_loader: CatalogLoader = build_source_catalog,
    coach_media_root: Path | None = None,
    reference_materializer: ReferenceMaterializer = ensure_demonstration_media,
) -> AnalysisJob:
    """Build a coach teaching demonstration without requiring learner media."""
    job = database.get_job(job_id)
    stopped = _stop_if_media_was_deleted(database, media_store, job.id)
    if stopped is not None or job.state == "completed":
        return stopped or job
    claimed = database.claim_demonstration_job(job.id)
    if claimed is None:
        return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)
    job = claimed
    try:
        profile = database.get_player_profile(job.id)
        query = _query_from_profile(job, profile)
        knowledge = load_coach_knowledge(job.coach_id, project_root)
        catalog = (
            build_source_catalog(job.coach_id, project_root, knowledge=knowledge)
            if catalog_loader is build_source_catalog
            else catalog_loader(job.coach_id, project_root)
        )
        plan = build_demonstration_plan(query, knowledge, catalog)
        selected = list(plan.pop("references"))

        active = database.set_active_state(
            job.id,
            "matching_references",
            55,
            "Extracting same-phase coach demonstration frames and clips.",
        )
        if active is None:
            return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)

        cache_root = coach_media_root or media_store.root.parent / "coach-media"
        materialized: list[CoachReference] = []
        for reference in selected:
            try:
                cached = reference_materializer(reference, cache_root)
            except Exception:
                cached = replace(
                    reference,
                    availability="unavailable",
                    media_key="",
                    clip_media_key="",
                    limitations=tuple(
                        dict.fromkeys(
                            (*reference.limitations, "source_acquisition_failed")
                        )
                    ),
                )
            database.save_coach_reference(cached)
            materialized.append(cached)

        stopped = _stop_if_media_was_deleted(database, media_store, job.id)
        if stopped is not None:
            return stopped
        coach = knowledge["coach"]
        report = {
            "report_type": "coach_demonstration",
            "coach_id": job.coach_id,
            "coach_name": str(coach.get("display_name", job.coach_id)),
            "official_status": str(coach.get("official_status", "non-official research synthesis")),
            "notice": str(coach.get("diagnosis_notice", "")),
            **plan,
            "coach_references": [
                _public_coach_reference(reference, job.id)
                for reference in materialized
            ],
        }
        if not materialized:
            report["limitations"] = list(
                dict.fromkeys(
                    (*report.get("limitations", []), "no_materialized_coach_reference")
                )
            )
        if not database.save_report_if_active(job.id, report):
            return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)
        completed = database.set_active_state(
            job.id, "completed", 100, "Coach demonstration is ready."
        )
        return completed or database.get_job(job.id)
    except Exception as error:
        stopped = _stop_if_media_was_deleted(database, media_store, job.id)
        if stopped is not None:
            return stopped
        failed = database.set_active_state(
            job.id,
            "failed",
            database.get_job(job.id).progress,
            "Coach demonstration could not be prepared from the indexed public sources.",
            failure_code=type(error).__name__,
        )
        return failed or database.get_job(job.id)
