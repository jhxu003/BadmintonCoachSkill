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
from .lesson_ingestion import ensure_video_lesson_media
from .matcher import match_coach_references
from .video_lessons import (
    VideoLessonPackage,
    VideoLessonQuery,
    VideoLessonStage,
    build_video_lesson_plan,
    load_video_lessons,
    select_video_lessons,
)

__all__ = [
    "DemonstrationQuery",
    "available_actions",
    "build_demonstration_plan",
    "build_source_catalog",
    "ensure_demonstration_media",
    "ensure_video_lesson_media",
    "VideoLessonPackage",
    "VideoLessonQuery",
    "VideoLessonStage",
    "build_video_lesson_plan",
    "load_video_lessons",
    "match_coach_references",
    "select_demonstration_references",
    "select_teaching_frameworks",
    "select_video_lessons",
]
