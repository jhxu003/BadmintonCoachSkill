"""Public-source coach reference catalog and private media cache helpers."""

from .catalog import build_source_catalog
from .demonstrations import (
    DemonstrationQuery,
    available_actions,
    build_demonstration_plan,
    select_demonstration_references,
    select_teaching_frameworks,
)
from .ingestion import ensure_demonstration_media
from .matcher import match_coach_references

__all__ = [
    "DemonstrationQuery",
    "available_actions",
    "build_demonstration_plan",
    "build_source_catalog",
    "ensure_demonstration_media",
    "match_coach_references",
    "select_demonstration_references",
    "select_teaching_frameworks",
]
