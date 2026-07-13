from __future__ import annotations

import os

from .analysis_runner import run_analysis_job
from .cleanup import cleanup_expired_jobs
from .database import Database
from .media_store import LocalMediaStore
from .settings import Settings
from .video_pipeline import create_default_video_pipeline


def execute_analysis(analysis_id: str) -> None:
    settings = Settings.from_env()
    database = Database(settings.database_url)
    database.create_all()
    run_analysis_job(
        database=database,
        media_store=LocalMediaStore(settings.media_root),
        project_root=settings.project_root,
        job_id=analysis_id,
        pipeline=create_default_video_pipeline(settings.project_root),
        coach_media_root=settings.coach_media_root,
    )


def expire_student_media() -> int:
    settings = Settings.from_env()
    database = Database(settings.database_url)
    database.create_all()
    return cleanup_expired_jobs(database, LocalMediaStore(settings.media_root))


try:
    from celery import Celery

    celery_app = Celery(
        "badminton-coach-worker",
        broker=os.environ.get("CELERY_BROKER_URL"),
    )
    celery_app.task(name="badminton_coach_skill.web.worker.execute_analysis")(execute_analysis)
    celery_app.task(name="badminton_coach_skill.web.worker.expire_student_media")(expire_student_media)
    celery_app.conf.beat_schedule = {
        "expire-student-media-hourly": {
            "task": "badminton_coach_skill.web.worker.expire_student_media",
            "schedule": 3600.0,
        }
    }
except ImportError:
    celery_app = None
