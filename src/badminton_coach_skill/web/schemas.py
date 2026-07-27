from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..video_evidence.contracts import Phase


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


class CoachDemonstrationRequest(BaseModel):
    coach_id: str
    action: str
    phase: Phase | None = None
    training_goal: str = ""
    level: str = "beginner"
    framework_id: str = ""
    limit: int = Field(default=2, ge=1, le=3)


class StructuredCoachingPlanRequest(BaseModel):
    """A bounded observation supplied by a human or upstream video agent."""

    coach_id: str
    player_profile: dict[str, Any]
    video_observation: dict[str, Any]
    limit: int = Field(default=2, ge=1, le=3)
