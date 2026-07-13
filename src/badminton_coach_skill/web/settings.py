from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    media_root: Path
    coach_media_root: Path
    project_root: Path
    dispatch_mode: str = "local"
    celery_broker_url: str | None = None
    analysis_ttl: timedelta = timedelta(hours=24)
    cleanup_interval_seconds: float = 900.0
    max_upload_bytes: int = 1_500_000_000
    websocket_poll_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> "Settings":
        runtime_root = Path(
            os.environ.get("BADMINTON_RUNTIME_ROOT", Path.cwd() / ".runtime")
        ).expanduser()
        runtime_root.mkdir(parents=True, exist_ok=True)
        database_url = os.environ.get(
            "DATABASE_URL", f"sqlite:///{runtime_root / 'badminton-coach.db'}"
        )
        return cls(
            database_url=database_url,
            media_root=Path(
                os.environ.get("STUDENT_MEDIA_ROOT", runtime_root / "student-media")
            ).expanduser(),
            coach_media_root=Path(
                os.environ.get("COACH_MEDIA_ROOT", runtime_root / "coach-media")
            ).expanduser(),
            project_root=Path(os.environ.get("BADMINTON_PROJECT_ROOT", Path.cwd())).expanduser(),
            dispatch_mode=os.environ.get("BADMINTON_DISPATCH_MODE", "local"),
            celery_broker_url=os.environ.get("CELERY_BROKER_URL"),
            analysis_ttl=timedelta(
                hours=max(1.0, float(os.environ.get("ANALYSIS_TTL_HOURS", "24")))
            ),
            cleanup_interval_seconds=max(
                60.0, float(os.environ.get("CLEANUP_INTERVAL_SECONDS", "900"))
            ),
        )

    @classmethod
    def for_test(cls, root: Path) -> "Settings":
        return cls(
            database_url=f"sqlite:///{root / 'test.db'}",
            media_root=root / "student-media",
            coach_media_root=root / "coach-media",
            project_root=Path.cwd(),
        )
