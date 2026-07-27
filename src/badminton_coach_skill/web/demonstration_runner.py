from __future__ import annotations

from dataclasses import replace
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..coach_media.catalog import build_source_catalog
from ..coach_media.demonstrations import DemonstrationQuery, build_demonstration_plan
from ..coach_media.ingestion import ensure_demonstration_media
from ..coach_media.lesson_ingestion import ensure_video_lesson_media
from ..coach_media.video_lessons import (
    VideoLessonPackage,
    VideoLessonQuery,
    build_video_lesson_plan,
    load_video_lessons,
    replace_lesson_references,
)
from ..coach_registry import load_coach_knowledge
from ..teaching_plan import generate_coaching_plan
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


LessonCatalogLoader = Callable[[str, Path], list[VideoLessonPackage]]
LessonMaterializer = Callable[[VideoLessonPackage, Path], VideoLessonPackage]


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


def _lesson_query_from_profile(
    job: AnalysisJob, profile: dict[str, object]
) -> VideoLessonQuery:
    return VideoLessonQuery(
        coach_id=job.coach_id,
        action=str(profile.get("action", job.action_hint or "")),
        training_goal=str(profile.get("training_goal", "")),
        level=str(profile.get("level", "beginner")),
        framework_id=str(profile.get("framework_id", "")),
        limit=int(profile.get("limit", 2)),
    )


def _public_video_lesson(
    lesson: VideoLessonPackage, analysis_id: str
) -> dict[str, object]:
    payload = lesson.to_dict()
    payload["full_reference"] = _public_coach_reference(
        lesson.full_reference, analysis_id
    )
    payload["stages"] = [
        {
            "stage_id": stage.stage_id,
            "label": stage.label,
            "phase": stage.phase,
            "teaching_points": list(stage.teaching_points),
            "reference": _public_coach_reference(stage.reference, analysis_id),
        }
        for stage in lesson.stages
    ]
    return payload


def _materialize_video_lessons(
    *,
    database: Database,
    media_store: LocalMediaStore,
    coach_media_root: Path | None,
    lessons: list[VideoLessonPackage],
    materializer: LessonMaterializer,
) -> tuple[list[VideoLessonPackage], list[CoachReference]]:
    """Cache only the selected continuous lessons and retain their provenance."""
    cache_root = coach_media_root or media_store.root.parent / "coach-media"
    materialized_lessons: list[VideoLessonPackage] = []
    flattened_references: list[CoachReference] = []
    for lesson in lessons:
        try:
            materialized = materializer(lesson, cache_root)
        except Exception:
            failure_limitations = tuple(
                dict.fromkeys((*lesson.limitations, "source_acquisition_failed"))
            )
            materialized = replace_lesson_references(
                replace(lesson, limitations=failure_limitations),
                full_reference=replace(
                    lesson.full_reference,
                    availability="unavailable",
                    media_key="",
                    clip_media_key="",
                    limitations=tuple(
                        dict.fromkeys(
                            (*lesson.full_reference.limitations, "source_acquisition_failed")
                        )
                    ),
                ),
                stage_references={
                    stage.stage_id: replace(
                        stage.reference,
                        availability="unavailable",
                        media_key="",
                        clip_media_key="",
                        limitations=tuple(
                            dict.fromkeys(
                                (*stage.reference.limitations, "source_acquisition_failed")
                            )
                        ),
                    )
                    for stage in lesson.stages
                },
            )
        references = [
            materialized.full_reference,
            *(stage.reference for stage in materialized.stages),
        ]
        for reference in references:
            database.save_coach_reference(reference)
        flattened_references.extend(references)
        materialized_lessons.append(materialized)
    return materialized_lessons, flattened_references


def run_demonstration_job(
    *,
    database: Database,
    media_store: LocalMediaStore,
    project_root: Path,
    job_id: str,
    catalog_loader: CatalogLoader = build_source_catalog,
    coach_media_root: Path | None = None,
    reference_materializer: ReferenceMaterializer = ensure_demonstration_media,
    lesson_loader: LessonCatalogLoader = load_video_lessons,
    lesson_materializer: LessonMaterializer = ensure_video_lesson_media,
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
        if profile.get("mode") == "structured_coaching_plan":
            player_profile = profile.get("player_profile")
            video_observation = profile.get("video_observation")
            if not isinstance(player_profile, dict) or not isinstance(video_observation, dict):
                raise ValueError(
                    "Structured coaching plans require player_profile and video_observation objects"
                )
            plan = generate_coaching_plan(
                coach_id=job.coach_id,
                player_profile=player_profile,
                video_observation=video_observation,
                root=project_root,
                limit=int(profile.get("limit", 2)),
            )
            selected_lessons = list(plan.pop("_video_lessons", ()))
            if not all(isinstance(lesson, VideoLessonPackage) for lesson in selected_lessons):
                raise RuntimeError("Structured coaching plan produced invalid video lessons")

            active = database.set_active_state(
                job.id,
                "matching_references",
                55,
                "Binding verified continuous coach lessons to the teaching order.",
            )
            if active is None:
                return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)
            materialized_lessons, flattened_references = _materialize_video_lessons(
                database=database,
                media_store=media_store,
                coach_media_root=coach_media_root,
                lessons=selected_lessons,
                materializer=lesson_materializer,
            )
            stopped = _stop_if_media_was_deleted(database, media_store, job.id)
            if stopped is not None:
                return stopped
            report = {
                **plan,
                "video_lessons": [
                    _public_video_lesson(lesson, job.id)
                    for lesson in materialized_lessons
                ],
                "coach_references": [
                    _public_coach_reference(reference, job.id)
                    for reference in flattened_references
                ],
            }
            if not materialized_lessons:
                report["limitations"] = list(
                    dict.fromkeys(
                        (*report.get("limitations", []), "no_materialized_video_lesson")
                    )
                )
            if not database.save_report_if_active(job.id, report):
                return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)
            completed = database.set_active_state(
                job.id, "completed", 100, "Structured coaching plan is ready."
            )
            return completed or database.get_job(job.id)

        if profile.get("mode") == "video_lesson":
            query = _lesson_query_from_profile(job, profile)
            knowledge = load_coach_knowledge(job.coach_id, project_root)
            lessons = lesson_loader(job.coach_id, project_root)
            plan = build_video_lesson_plan(query, knowledge, lessons)
            selected_lessons = list(plan.pop("video_lessons"))

            active = database.set_active_state(
                job.id,
                "matching_references",
                55,
                "Extracting continuous coach video lessons and ordered stage media.",
            )
            if active is None:
                return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)

            materialized_lessons, flattened_references = _materialize_video_lessons(
                database=database,
                media_store=media_store,
                coach_media_root=coach_media_root,
                lessons=selected_lessons,
                materializer=lesson_materializer,
            )

            stopped = _stop_if_media_was_deleted(database, media_store, job.id)
            if stopped is not None:
                return stopped
            coach = knowledge["coach"]
            report = {
                "report_type": "coach_video_lesson",
                "coach_id": job.coach_id,
                "coach_name": str(coach.get("display_name", job.coach_id)),
                "official_status": str(
                    coach.get("official_status", "non-official research synthesis")
                ),
                "notice": str(coach.get("diagnosis_notice", "")),
                **plan,
                "video_lessons": [
                    _public_video_lesson(lesson, job.id)
                    for lesson in materialized_lessons
                ],
                "coach_references": [
                    _public_coach_reference(reference, job.id)
                    for reference in flattened_references
                ],
            }
            if not materialized_lessons:
                report["limitations"] = list(
                    dict.fromkeys(
                        (*report.get("limitations", []), "no_materialized_video_lesson")
                    )
                )
            if not database.save_report_if_active(job.id, report):
                return _stop_if_media_was_deleted(database, media_store, job.id) or database.get_job(job.id)
            completed = database.set_active_state(
                job.id, "completed", 100, "Coach video lesson is ready."
            )
            return completed or database.get_job(job.id)

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
