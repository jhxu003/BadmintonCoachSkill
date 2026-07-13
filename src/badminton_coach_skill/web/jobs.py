from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from secrets import token_urlsafe
from uuid import uuid4

from .database import Database, utcnow
from .media_store import LocalMediaStore
from .models import AnalysisJob


def create_analysis_job(
    database: Database,
    coach_id: str,
    action_hint: str | None = None,
    player_profile: dict[str, object] | None = None,
    ttl: timedelta = timedelta(hours=24),
) -> AnalysisJob:
    created_at = utcnow()
    job = AnalysisJob(
        id=str(uuid4()),
        coach_id=coach_id,
        state="uploaded",
        progress=0,
        created_at=created_at,
        expires_at=created_at + ttl,
        action_hint=action_hint,
        access_token=token_urlsafe(32),
    )
    database.create_job(job, player_profile or {}, access_token=job.access_token or "")
    database.set_state(job.id, "uploaded", 0, "Video upload accepted.")
    return replace(database.get_job(job.id), access_token=job.access_token)


def expire_jobs(database: Database, media_store: LocalMediaStore, now: datetime | None = None) -> int:
    expiry_time = now or utcnow()
    expired = 0
    for job in database.list_expired_jobs(expiry_time):
        if job.state != "expired":
            database.set_state(job.id, "deleting", job.progress, "Deleting expired student media.")
        media_store.delete_job(job.id)
        database.delete_media_assets(job.id)
        if job.state != "expired":
            database.set_state(job.id, "expired", 100, "Student media expired and was deleted.")
        expired += 1
    return expired


def delete_analysis_job(database: Database, media_store: LocalMediaStore, job_id: str) -> AnalysisJob:
    job = database.get_job(job_id)
    if job.state == "expired":
        return job
    database.set_state(job.id, "deleting", job.progress, "Deleting student media on request.")
    media_store.delete_job(job.id)
    database.delete_media_assets(job.id)
    return database.set_state(job.id, "expired", 100, "Student media deleted on request.")
