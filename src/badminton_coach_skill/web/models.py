from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


JobState = Literal[
    "uploaded",
    "queued",
    "normalizing",
    "tracking",
    "phase_candidates",
    "visual_review",
    "diagnosing",
    "matching_references",
    "needs_player_selection",
    "completed",
    "failed",
    "deleting",
    "expired",
]


@dataclass(frozen=True)
class AnalysisJob:
    id: str
    coach_id: str
    state: JobState
    progress: int
    created_at: datetime
    expires_at: datetime
    action_hint: str | None = None
    failure_code: str | None = None
    access_token: str | None = None


@dataclass(frozen=True)
class AnalysisEvent:
    sequence: int
    job_id: str
    state: JobState
    progress: int
    message: str
    created_at: datetime


@dataclass(frozen=True)
class MediaAsset:
    id: str
    job_id: str
    media_key: str
    kind: Literal["upload", "derivative", "student_frame"]
    expires_at: datetime
