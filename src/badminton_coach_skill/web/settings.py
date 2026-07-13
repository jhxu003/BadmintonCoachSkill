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
    analysis_ttl: timedelta = timedelta(hours=24)
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
        )

    @classmethod
    def for_test(cls, root: Path) -> "Settings":
        return cls(
            database_url=f"sqlite:///{root / 'test.db'}",
            media_root=root / "student-media",
            coach_media_root=root / "coach-media",
        )
