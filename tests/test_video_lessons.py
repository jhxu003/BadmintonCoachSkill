from __future__ import annotations

from pathlib import Path

import pytest

from badminton_coach_skill.coach_media.video_lessons import (
    VideoLessonPackage,
    VideoLessonStage,
    load_video_lessons,
)
from badminton_coach_skill.video_evidence.contracts import CoachReference


PHASES = (
    "preparation",
    "start",
    "arrival",
    "top_elbow",
    "contact_window",
    "follow_through",
    "recovery",
)


def _stage(phase: str, index: int) -> VideoLessonStage:
    anchor = 100 + index * 100
    return VideoLessonStage(
        stage_id=f"stage-{index}",
        label=phase,
        reference=CoachReference(
            reference_id=f"reference-{index}",
            coach_id="liu-hui",
            source_id="LH_BILI_SEASON_BV1A54Y1T7PE",
            phase=phase,  # type: ignore[arg-type]
            timestamp_ms=anchor,
            source_url="https://example.invalid/source",
            confidence="high",
            actions=("high_clear",),
            framework_ids=(),
            availability="indexed",
            window_start_ms=anchor - 40,
            window_end_ms=anchor + 40,
            review_status="agent_reviewed",
        ),
    )


def _lesson(phases: tuple[str, ...]) -> VideoLessonPackage:
    stages = tuple(_stage(phase, index) for index, phase in enumerate(phases))
    return VideoLessonPackage(
        lesson_id="seven-phase-fixture",
        coach_id="liu-hui",
        action="high_clear",
        lesson_topic="fixture",
        family_id="overhead",
        taxonomy_path=("stroke_families.high_clear",),
        semantic_review_status="agent_reviewed",
        source_id="LH_BILI_SEASON_BV1A54Y1T7PE",
        source_url="https://example.invalid/source",
        title="fixture",
        completeness="complete_demonstration",
        review_status="agent_reviewed",
        teaching_summary="fixture",
        episode_start_ms=0,
        episode_end_ms=1000,
        full_reference=stages[0].reference,
        stages=stages,
    )


def test_complete_demonstration_requires_every_phase() -> None:
    incomplete = PHASES[:-1] + ("follow_through",)
    with pytest.raises(ValueError, match="missing required phases"):
        _lesson(incomplete)


def test_complete_demonstration_accepts_seven_ordered_phases() -> None:
    lesson = _lesson(PHASES)
    assert tuple(stage.phase for stage in lesson.stages) == PHASES


def test_public_complete_lesson_obeys_seven_phase_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    lessons = load_video_lessons("liu-hui", root)
    complete = [lesson for lesson in lessons if lesson.completeness == "complete_demonstration"]
    assert complete
    assert all(tuple(stage.phase for stage in lesson.stages) == PHASES for lesson in complete)
