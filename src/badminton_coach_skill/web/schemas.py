from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalysisJobResponse(BaseModel):
    analysis_id: str
    state: str
    progress: int
    expires_at: datetime
    action_hint: str | None = None
    failure_code: str | None = None
    access_token: str | None = None


class AnalysisEventResponse(BaseModel):
    sequence: int
    state: str
    progress: int
    message: str
    created_at: datetime


class AnalysisReportResponse(BaseModel):
    report: dict[str, Any] = Field(description="Bounded Skill diagnosis and phase evidence.")


class MixedDoublesSetupRequest(BaseModel):
    learner_track_id: str
    partner_track_id: str
    court_corners: dict[str, dict[str, float]]
