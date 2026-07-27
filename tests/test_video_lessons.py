from __future__ import annotations

from pathlib import Path

import pytest

from badminton_coach_skill.coach_media.video_lessons import (
    VideoLessonPackage,
    VideoLessonStage,
    load_video_lessons,
)
from badminton_coach_skill.coach_media.lesson_ingestion import ensure_video_lesson_media
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


def test_configured_staged_lesson_media_is_used_before_redownloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lesson = _lesson(PHASES)
    staged_root = tmp_path / "staged-lessons"
    staged_media = staged_root / "private-media" / lesson.lesson_id
    frames = staged_media / "frames"
    frames.mkdir(parents=True)
    action = staged_media / "action.mp4"
    action.write_bytes(b"reviewed-action")
    for index, stage in enumerate(lesson.stages, start=1):
        (frames / f"stage-{index:02d}-{stage.stage_id}.jpg").write_bytes(
            f"reviewed-{stage.stage_id}".encode()
        )
    monkeypatch.setenv("BADMINTON_VIDEO_LESSON_ROOT", str(staged_root))

    extracted_windows: list[tuple[int, int]] = []

    def unexpected_network(*_: object) -> None:
        raise AssertionError("staged reviewed media should avoid public redownload")

    def extract_staged_clip(_: Path, start_ms: int, end_ms: int, target: Path) -> None:
        extracted_windows.append((start_ms, end_ms))
        target.write_bytes(b"stage-clip")

    materialized = ensure_video_lesson_media(
        lesson,
        tmp_path / "cache",
        downloader=unexpected_network,
        frame_extractor=unexpected_network,
        clip_extractor=extract_staged_clip,
    )

    assert materialized.full_reference.availability == "cached"
    assert all(stage.reference.availability == "cached" for stage in materialized.stages)
    assert len(extracted_windows) == len(PHASES)
    assert not (tmp_path / "cache" / ".downloads").exists()
