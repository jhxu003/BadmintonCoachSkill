from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

from .analysis_runner import run_analysis_job
from .database import Database
from .media_store import LocalMediaStore
from .settings import Settings
from .video_pipeline import create_default_video_pipeline


class AnalysisDispatcher(Protocol):
    def enqueue(self, analysis_id: str) -> None:
        """Schedule a queued analysis outside the upload request."""


class LocalAnalysisDispatcher:
    """Development dispatcher. Run the web server on a GPU-capable host for real inference."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="badminton-analysis")

    def enqueue(self, analysis_id: str) -> None:
        self.executor.submit(self._run, analysis_id)

    def _run(self, analysis_id: str) -> None:
        database = Database(self.settings.database_url)
        database.create_all()
        run_analysis_job(
            database=database,
            media_store=LocalMediaStore(self.settings.media_root),
            project_root=self.settings.project_root,
            job_id=analysis_id,
            pipeline=create_default_video_pipeline(self.settings.project_root),
            coach_media_root=self.settings.coach_media_root,
        )

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)


class CeleryAnalysisDispatcher:
    """Production dispatcher that hands GPU work to a separately launched Celery worker."""

    def __init__(self, broker_url: str):
        if not broker_url:
            raise ValueError("CELERY_BROKER_URL is required for celery dispatch")
        try:
            from celery import Celery
        except ImportError as error:
            raise RuntimeError("Celery is unavailable in the active environment") from error
        self._celery = Celery("badminton-coach-web", broker=broker_url)

    def enqueue(self, analysis_id: str) -> None:
        self._celery.send_task("badminton_coach_skill.web.worker.execute_analysis", args=[analysis_id])


def create_dispatcher(settings: Settings) -> AnalysisDispatcher:
    if settings.dispatch_mode == "celery":
        return CeleryAnalysisDispatcher(settings.celery_broker_url or "")
    if settings.dispatch_mode == "local":
        return LocalAnalysisDispatcher(settings)
    raise ValueError("BADMINTON_DISPATCH_MODE must be 'local' or 'celery'")
