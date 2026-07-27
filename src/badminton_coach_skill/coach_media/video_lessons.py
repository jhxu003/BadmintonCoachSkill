from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
from typing import Any, Literal

import yaml

from ..coach_registry import load_coach_config, load_coach_knowledge
from ..source_index import read_source_index
from ..video_evidence.contracts import CONFIDENCES, PHASES, CoachReference, Phase
from .demonstrations import (
    DemonstrationQuery,
    available_actions,
    select_teaching_frameworks,
)


LessonCompleteness = Literal[
    "complete_demonstration",
    "partial_demonstration",
    "static_explanation",
    "concept_only",
]
LessonReviewStatus = Literal["agent_reviewed", "model_candidate"]

_COMPLETENESS_PRIORITY: dict[LessonCompleteness, int] = {
    "complete_demonstration": 4,
    "partial_demonstration": 3,
    "static_explanation": 2,
    "concept_only": 1,
}
_PHASE_ORDER = (
    "preparation",
    "start",
    "arrival",
    "top_elbow",
    "contact_window",
    "follow_through",
    "recovery",
)
_COMPLETE_DEMONSTRATION_PHASES = frozenset(_PHASE_ORDER)
_STAGED_LESSON_ROOT_ENV = {
    "liu-hui": "BADMINTON_VIDEO_LESSON_ROOT",
    "li-yuxuan": "BADMINTON_LI_YUXUAN_VIDEO_LESSON_ROOT",
    "zheng-siwei": "BADMINTON_ZHENG_SIWEI_VIDEO_LESSON_ROOT",
}


def _validate_media_key_component(value: str, field: str) -> None:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"{field} must be a safe media-key component")


@dataclass(frozen=True)
class VideoLessonStage:
    """One ordered teaching stage inside one continuous coach demonstration."""

    stage_id: str
    label: str
    reference: CoachReference
    teaching_points: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.stage_id or not self.label:
            raise ValueError("stage_id and label are required")
        _validate_media_key_component(self.stage_id, "stage_id")
        if self.reference.window_start_ms is None or self.reference.window_end_ms is None:
            raise ValueError("lesson stage requires a bounded clip window")
        if not (
            self.reference.window_start_ms
            <= self.reference.timestamp_ms
            <= self.reference.window_end_ms
        ):
            raise ValueError("lesson stage anchor must fall inside its clip window")

    @property
    def phase(self) -> Phase:
        return self.reference.phase

    def to_dict(self) -> dict[str, object]:
        return {
            "stage_id": self.stage_id,
            "label": self.label,
            "phase": self.reference.phase,
            "teaching_points": list(self.teaching_points),
            "reference": self.reference.to_dict(),
        }


@dataclass(frozen=True)
class VideoLessonPackage:
    """A source-video teaching unit with one bounded episode and ordered stages."""

    lesson_id: str
    coach_id: str
    action: str
    lesson_topic: str
    family_id: str
    taxonomy_path: tuple[str, ...]
    semantic_review_status: LessonReviewStatus
    source_id: str
    source_url: str
    title: str
    completeness: LessonCompleteness
    review_status: LessonReviewStatus
    teaching_summary: str
    episode_start_ms: int
    episode_end_ms: int
    full_reference: CoachReference
    stages: tuple[VideoLessonStage, ...]
    clip_start_ms: int | None = None
    clip_end_ms: int | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not (
            self.lesson_id
            and self.coach_id
            and self.action
            and self.lesson_topic
            and self.family_id
            and self.source_id
        ):
            raise ValueError(
                "lesson_id, coach_id, action, lesson_topic, family_id, and source_id are required"
            )
        if not self.taxonomy_path or any(not value for value in self.taxonomy_path):
            raise ValueError("lesson taxonomy_path must contain non-empty entries")
        if self.semantic_review_status not in {"agent_reviewed", "model_candidate"}:
            raise ValueError(
                f"Unsupported semantic review status: {self.semantic_review_status}"
            )
        _validate_media_key_component(self.lesson_id, "lesson_id")
        _validate_media_key_component(self.coach_id, "coach_id")
        _validate_media_key_component(self.source_id, "source_id")
        if self.completeness not in _COMPLETENESS_PRIORITY:
            raise ValueError(f"Unsupported lesson completeness: {self.completeness}")
        if self.review_status not in {"agent_reviewed", "model_candidate"}:
            raise ValueError(f"Unsupported lesson review status: {self.review_status}")
        if self.episode_start_ms < 0 or self.episode_end_ms <= self.episode_start_ms:
            raise ValueError("lesson episode must be positive and ordered")
        if self.playback_start_ms < 0 or self.playback_end_ms <= self.playback_start_ms:
            raise ValueError("lesson playback clip must be positive and ordered")
        if self.playback_start_ms > self.episode_start_ms:
            raise ValueError("lesson playback clip must start no later than the action")
        if self.playback_end_ms < self.episode_end_ms:
            raise ValueError("lesson playback clip must include the complete action")
        anchors = [stage.reference.timestamp_ms for stage in self.stages]
        if anchors != sorted(anchors) or len(anchors) != len(set(anchors)):
            raise ValueError("lesson stage anchors must be strictly increasing")
        stage_ids = [stage.stage_id for stage in self.stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("lesson stage ids must be unique")
        phase_indexes = [_PHASE_ORDER.index(stage.phase) for stage in self.stages]
        if phase_indexes != sorted(phase_indexes):
            raise ValueError("lesson stages must not regress through the action phases")
        if any(
            not self.episode_start_ms
            <= stage.reference.timestamp_ms
            <= self.episode_end_ms
            for stage in self.stages
        ):
            raise ValueError("lesson stages must stay inside the continuous episode")
        if any(
            stage.reference.window_start_ms is None
            or stage.reference.window_end_ms is None
            or stage.reference.window_start_ms < self.episode_start_ms
            or stage.reference.window_end_ms > self.episode_end_ms
            for stage in self.stages
        ):
            raise ValueError("lesson stage windows must stay inside the continuous episode")
        if self.completeness == "complete_demonstration":
            if len(self.stages) < len(_PHASE_ORDER):
                raise ValueError(
                    "complete demonstrations require all seven ordered action phases"
                )
            missing_phases = _COMPLETE_DEMONSTRATION_PHASES.difference(
                stage.phase for stage in self.stages
            )
            if missing_phases:
                raise ValueError(
                    "complete demonstrations are missing required phases: "
                    + ", ".join(sorted(missing_phases))
                )

    @property
    def playback_start_ms(self) -> int:
        return self.episode_start_ms if self.clip_start_ms is None else self.clip_start_ms

    @property
    def playback_end_ms(self) -> int:
        return self.episode_end_ms if self.clip_end_ms is None else self.clip_end_ms

    def to_dict(self) -> dict[str, object]:
        return {
            "lesson_id": self.lesson_id,
            "coach_id": self.coach_id,
            "action": self.action,
            "lesson_topic": self.lesson_topic,
            "family_id": self.family_id,
            "taxonomy_path": list(self.taxonomy_path),
            "semantic_review_status": self.semantic_review_status,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "title": self.title,
            "completeness": self.completeness,
            "review_status": self.review_status,
            "teaching_summary": self.teaching_summary,
            "episode_start_ms": self.episode_start_ms,
            "episode_end_ms": self.episode_end_ms,
            "action_start_ms": self.episode_start_ms,
            "action_end_ms": self.episode_end_ms,
            "clip_start_ms": self.playback_start_ms,
            "clip_end_ms": self.playback_end_ms,
            "full_reference": self.full_reference.to_dict(),
            "stages": [stage.to_dict() for stage in self.stages],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class VideoLessonQuery:
    coach_id: str
    action: str
    training_goal: str = ""
    level: str = "beginner"
    framework_id: str = ""
    limit: int = 2

    def __post_init__(self) -> None:
        if not self.coach_id or not self.action:
            raise ValueError("coach_id and action are required")
        if self.level not in {"beginner", "intermediate", "advanced", "competitive"}:
            raise ValueError(f"Unsupported level: {self.level}")
        if self.limit < 1 or self.limit > 3:
            raise ValueError("limit must be between 1 and 3")


def _milliseconds(value: object, field: str) -> int:
    try:
        milliseconds = round(float(value) * 1000)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be a number of seconds") from error
    if milliseconds < 0:
        raise ValueError(f"{field} must be non-negative")
    return milliseconds


def _source_rows(root: Path, coach_id: str) -> dict[str, dict[str, str]]:
    config = load_coach_config(coach_id, root)
    return {
        row["source_id"]: row
        for row in read_source_index(root / str(config["source_index"]))
    }


def _lesson_paths(root: Path, coach_id: str) -> list[Path]:
    staged_root_env = _STAGED_LESSON_ROOT_ENV.get(coach_id, "")
    staged_root_value = os.environ.get(staged_root_env, "").strip()
    if staged_root_env and staged_root_value:
        staged_root = Path(staged_root_value).expanduser()
        index_path = staged_root / "video-lessons-index.yaml"
        if not index_path.is_file():
            raise ValueError(
                f"{staged_root_env} must contain video-lessons-index.yaml"
            )
        index = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
        if not isinstance(index, dict) or not isinstance(index.get("lessons"), list):
            raise ValueError("staged video lesson index must contain a lessons list")
        paths: list[Path] = []
        for item in index["lessons"]:
            if not isinstance(item, dict):
                raise ValueError("staged video lesson index item must be an object")
            shard = Path(str(item.get("shard", "")))
            if (
                not str(shard)
                or shard.is_absolute()
                or ".." in shard.parts
                or shard.parts[0] != "video-lessons"
            ):
                raise ValueError("staged lesson shard must stay under video-lessons/")
            path = staged_root / shard
            if not path.is_file():
                raise ValueError(f"missing staged lesson shard: {path.name}")
            if path not in paths:
                paths.append(path)
        return sorted(paths)

    config = load_coach_config(coach_id, root)
    reference_root = root / str(config["reference_path"])
    paths = [reference_root / "video-lessons.yaml"]
    shard_root = reference_root / "video-lessons"
    if shard_root.is_dir():
        paths.extend(sorted(shard_root.glob("*.yaml")))
    return [path for path in paths if path.is_file()]


def _reference_from_stage(
    *,
    coach_id: str,
    action: str,
    lesson_id: str,
    source_id: str,
    source_url: str,
    title: str,
    review_status: LessonReviewStatus,
    row: dict[str, Any],
) -> VideoLessonStage:
    phase = str(row.get("phase", ""))
    if phase not in PHASES:
        raise ValueError(f"Unsupported lesson phase: {phase}")
    confidence = str(row.get("confidence", "medium"))
    if confidence not in CONFIDENCES:
        raise ValueError(f"Unsupported lesson confidence: {confidence}")
    stage_id = str(row.get("stage_id", "")).strip()
    start_ms = _milliseconds(row.get("start_seconds"), "stage.start_seconds")
    anchor_ms = _milliseconds(row.get("anchor_seconds"), "stage.anchor_seconds")
    end_ms = _milliseconds(row.get("end_seconds"), "stage.end_seconds")
    if end_ms <= start_ms:
        raise ValueError("lesson stage end must be after its start")
    reference = CoachReference(
        reference_id=f"{lesson_id}-{stage_id}",
        coach_id=coach_id,
        source_id=source_id,
        phase=phase,  # type: ignore[arg-type]
        timestamp_ms=anchor_ms,
        source_url=source_url,
        confidence=confidence,  # type: ignore[arg-type]
        actions=(action,),
        framework_ids=tuple(str(item) for item in row.get("framework_ids", [])),
        availability="indexed",
        title=title,
        window_start_ms=start_ms,
        window_end_ms=end_ms,
        visible_facts=tuple(str(item) for item in row.get("visible_facts", [])),
        limitations=tuple(str(item) for item in row.get("limitations", [])),
        review_status=review_status,
        teaching_use=str(row.get("teaching_use", "")),
    )
    return VideoLessonStage(
        stage_id=stage_id,
        label=str(row.get("label", "")).strip(),
        reference=reference,
        teaching_points=tuple(str(item) for item in row.get("teaching_points", [])),
    )


def load_video_lessons(coach_id: str, root: str | Path) -> list[VideoLessonPackage]:
    """Load reviewed or candidate source-video lesson packages without touching media."""
    project_root = Path(root)
    paths = _lesson_paths(project_root, coach_id)
    if not paths:
        return []
    rows: list[Any] = []
    for path in paths:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            rows.extend(payload.get("lessons", []))
    source_rows = _source_rows(project_root, coach_id)
    lessons: list[VideoLessonPackage] = []
    seen_lesson_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        lesson_id = str(row.get("lesson_id", "")).strip()
        if lesson_id in seen_lesson_ids:
            raise ValueError(f"Duplicate video lesson id: {lesson_id}")
        seen_lesson_ids.add(lesson_id)
        source_id = str(row.get("source_id", "")).strip()
        source = source_rows.get(source_id)
        if source is None:
            raise ValueError(f"Unknown lesson source_id: {source_id}")
        action = str(row.get("action", "")).strip()
        lesson_topic = str(row.get("lesson_topic", "")).strip()
        family_id = str(row.get("family_id", "")).strip()
        taxonomy_path = tuple(str(item).strip() for item in row.get("taxonomy_path", []))
        semantic_review_status = str(
            row.get("semantic_review_status", "model_candidate")
        )
        if semantic_review_status not in {"agent_reviewed", "model_candidate"}:
            raise ValueError(
                f"Unsupported semantic review status: {semantic_review_status}"
            )
        review_status = str(row.get("review_status", "model_candidate"))
        if review_status not in {"agent_reviewed", "model_candidate"}:
            raise ValueError(f"Unsupported lesson review status: {review_status}")
        episode = row.get("episode", {}) or {}
        start_ms = _milliseconds(episode.get("start_seconds"), "episode.start_seconds")
        end_ms = _milliseconds(episode.get("end_seconds"), "episode.end_seconds")
        if end_ms <= start_ms:
            raise ValueError("lesson episode end must be after its start")
        clip_start_ms = _milliseconds(
            episode.get("clip_start_seconds", episode.get("start_seconds")),
            "episode.clip_start_seconds",
        )
        clip_end_ms = _milliseconds(
            episode.get("clip_end_seconds", episode.get("end_seconds")),
            "episode.clip_end_seconds",
        )
        stages = tuple(
            _reference_from_stage(
                coach_id=coach_id,
                action=action,
                lesson_id=lesson_id,
                source_id=source_id,
                source_url=source["url"],
                title=source["title"],
                review_status=review_status,  # type: ignore[arg-type]
                row=stage,
            )
            for stage in row.get("stages", [])
            if isinstance(stage, dict)
        )
        full_reference = CoachReference(
            reference_id=f"{lesson_id}-full",
            coach_id=coach_id,
            source_id=source_id,
            phase=stages[0].phase if stages else "preparation",
            timestamp_ms=stages[0].reference.timestamp_ms if stages else start_ms,
            source_url=source["url"],
            confidence=str(row.get("confidence", "medium")),  # type: ignore[arg-type]
            actions=(action,),
            framework_ids=tuple(str(item) for item in row.get("framework_ids", [])),
            availability="indexed",
            title=source["title"],
            window_start_ms=clip_start_ms,
            window_end_ms=clip_end_ms,
            visible_facts=("continuous_coach_demonstration",),
            limitations=tuple(str(item) for item in row.get("limitations", [])),
            review_status=review_status,  # type: ignore[arg-type]
            teaching_use="Continuous source-video episode for the ordered lesson stages.",
        )
        lessons.append(
            VideoLessonPackage(
                lesson_id=lesson_id,
                coach_id=coach_id,
                action=action,
                lesson_topic=lesson_topic,
                family_id=family_id,
                taxonomy_path=taxonomy_path,
                semantic_review_status=semantic_review_status,  # type: ignore[arg-type]
                source_id=source_id,
                source_url=source["url"],
                title=source["title"],
                completeness=str(row.get("completeness", "partial_demonstration")),  # type: ignore[arg-type]
                review_status=review_status,  # type: ignore[arg-type]
                teaching_summary=str(row.get("teaching_summary", "")),
                episode_start_ms=start_ms,
                episode_end_ms=end_ms,
                full_reference=full_reference,
                stages=stages,
                clip_start_ms=clip_start_ms,
                clip_end_ms=clip_end_ms,
                limitations=tuple(str(item) for item in row.get("limitations", [])),
            )
        )
    return sorted(lessons, key=lambda lesson: (lesson.source_id, lesson.episode_start_ms, lesson.lesson_id))


def _lesson_score(
    lesson: VideoLessonPackage,
    framework_source_ids: set[str],
) -> tuple[int, int, int, str]:
    score = _COMPLETENESS_PRIORITY[lesson.completeness] * 100
    score += 1000 if lesson.review_status == "agent_reviewed" else 0
    score += 80 if lesson.source_id in framework_source_ids else 0
    score += min(70, len(lesson.stages) * 10)
    return score, len(lesson.stages), -lesson.episode_start_ms, lesson.lesson_id


def select_video_lessons(
    query: VideoLessonQuery,
    frameworks: list[dict[str, object]],
    lessons: list[VideoLessonPackage],
) -> list[VideoLessonPackage]:
    """Select only publishable continuous teaching demonstrations.

    The catalog deliberately retains partial, static, and model-only packages
    for private review.  They must never become a learner-facing fallback just
    because no complete package exists for the requested action.
    """
    candidates = [
        lesson
        for lesson in lessons
        if (
            lesson.coach_id == query.coach_id
            and lesson.action == query.action
            and lesson.completeness == "complete_demonstration"
            and lesson.review_status == "agent_reviewed"
            and lesson.semantic_review_status == "agent_reviewed"
        )
    ]
    framework_source_ids = {
        str(source_id)
        for framework in frameworks
        for source_id in framework.get("source_ids", [])
    }
    return sorted(
        candidates,
        key=lambda lesson: _lesson_score(lesson, framework_source_ids),
        reverse=True,
    )[: query.limit]


def build_video_lesson_plan(
    query: VideoLessonQuery,
    knowledge: dict[str, Any],
    lessons: list[VideoLessonPackage],
) -> dict[str, object]:
    actions = available_actions(knowledge)
    if query.action not in actions:
        raise ValueError(
            f"Unsupported action {query.action!r}. Available actions: {', '.join(actions)}"
        )
    framework_query = DemonstrationQuery(
        coach_id=query.coach_id,
        action=query.action,
        phase="preparation",
        training_goal=query.training_goal,
        level=query.level,
        framework_id=query.framework_id,
        limit=query.limit,
    )
    frameworks = select_teaching_frameworks(knowledge, framework_query)
    if query.framework_id and not frameworks:
        raise ValueError(
            f"Framework {query.framework_id!r} does not support action {query.action!r}"
        )
    selected = select_video_lessons(query, frameworks, lessons)
    limitations = [
        "non_official_public_source_research_synthesis",
        "ordinary_monocular_video_does_not_prove_contact_racket_face_force_or_3d_kinematics",
    ]
    if not selected:
        limitations.append("no_reliable_video_lesson_package")
    elif any(lesson.review_status != "agent_reviewed" for lesson in selected):
        limitations.append("video_lesson_package_requires_manual_review")
    return {
        "query": {
            "coach_id": query.coach_id,
            "action": query.action,
            "training_goal": query.training_goal,
            "level": query.level,
            "framework_id": query.framework_id,
        },
        "teaching_routes": frameworks,
        "video_lessons": selected,
        "limitations": limitations,
    }


def load_video_lesson_plan(query: VideoLessonQuery, root: str | Path) -> dict[str, object]:
    project_root = Path(root)
    return build_video_lesson_plan(
        query,
        load_coach_knowledge(query.coach_id, project_root),
        load_video_lessons(query.coach_id, project_root),
    )


def replace_lesson_references(
    lesson: VideoLessonPackage,
    *,
    full_reference: CoachReference,
    stage_references: dict[str, CoachReference],
) -> VideoLessonPackage:
    return replace(
        lesson,
        full_reference=full_reference,
        stages=tuple(
            replace(stage, reference=stage_references.get(stage.stage_id, stage.reference))
            for stage in lesson.stages
        ),
    )
