from __future__ import annotations

from datetime import datetime

from .database import Database
from .jobs import expire_jobs
from .media_store import LocalMediaStore


def cleanup_expired_jobs(
    database: Database, media_store: LocalMediaStore, now: datetime | None = None
) -> int:
    """Delete expired private learner media before recording the expired state."""
    return expire_jobs(database, media_store, now=now)
