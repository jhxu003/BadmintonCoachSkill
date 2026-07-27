from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil
from typing import Callable
from uuid import uuid4

from ..video_evidence.contracts import CoachReference
from .ingestion import (
    DownloadSource,
    ExtractReferenceClip,
    ExtractReferenceFrame,
    download_public_source,
    extract_reference_clip,
    extract_reference_frame,
)
from .video_lessons import (
    VideoLessonPackage,
    replace_lesson_references,
    staged_video_lesson_root,
)


def _lesson_root(lesson: VideoLessonPackage) -> Path:
    return (
        Path(lesson.coach_id)
        / lesson.source_id
        / "lessons"
        / lesson.lesson_id
    )


def _stage_media_keys(
    lesson: VideoLessonPackage,
    stage_id: str,
    reference: CoachReference,
) -> tuple[Path, Path]:
    root = _lesson_root(lesson)
    image = root / f"{stage_id}-{reference.timestamp_ms}.jpg"
    clip = root / (
        f"{stage_id}-{reference.window_start_ms}-{reference.window_end_ms}.mp4"
    )
    return image, clip


def _full_clip_key(lesson: VideoLessonPackage) -> Path:
    return _lesson_root(lesson) / (
        f"full-{lesson.playback_start_ms}-{lesson.playback_end_ms}.mp4"
    )


def _full_image_key(lesson: VideoLessonPackage) -> Path:
    if lesson.stages:
        return _stage_media_keys(
            lesson,
            lesson.stages[0].stage_id,
            lesson.stages[0].reference,
        )[0]
    return _lesson_root(lesson) / f"full-{lesson.full_reference.timestamp_ms}.jpg"


def _staged_lesson_media(
    lesson: VideoLessonPackage,
) -> tuple[Path, dict[str, Path]] | None:
    """Locate a complete, deployment-private staged lesson without downloading.

    A configured lesson root is an explicit operator-provided trust boundary;
    it is never inferred from a source URL.  Require both its continuous clip
    and every reviewed stage image before using it, otherwise the normal
    public-source acquisition path remains in effect.
    """
    staged_root = staged_video_lesson_root(lesson.coach_id)
    if staged_root is None:
        return None
    media_root = staged_root / "private-media" / lesson.lesson_id
    full_clip = media_root / "action.mp4"
    frames = {
        stage.stage_id: media_root / "frames" / f"stage-{index:02d}-{stage.stage_id}.jpg"
        for index, stage in enumerate(lesson.stages, start=1)
    }
    if not full_clip.is_file() or not all(path.is_file() for path in frames.values()):
        return None
    return full_clip, frames


def _cached_reference(
    reference: CoachReference,
    image_key: Path,
    clip_key: Path,
    start_ms: int,
    end_ms: int,
) -> CoachReference:
    return replace(
        reference,
        availability="cached",
        media_key=str(image_key),
        clip_media_key=str(clip_key),
        clip_start_ms=start_ms,
        clip_end_ms=end_ms,
    )


def _cached_lesson(
    lesson: VideoLessonPackage,
    *,
    full_clip_key: Path,
    full_image_key: Path,
    stage_paths: dict[str, tuple[Path, Path]],
) -> VideoLessonPackage:
    stage_references = {
        stage.stage_id: _cached_reference(
            stage.reference,
            stage_paths[stage.stage_id][0],
            stage_paths[stage.stage_id][1],
            int(stage.reference.window_start_ms or 0),
            int(stage.reference.window_end_ms or 0),
        )
        for stage in lesson.stages
    }
    full_reference = _cached_reference(
        lesson.full_reference,
        full_image_key,
        full_clip_key,
        lesson.playback_start_ms,
        lesson.playback_end_ms,
    )
    return replace_lesson_references(
        lesson,
        full_reference=full_reference,
        stage_references=stage_references,
    )


def _prime_from_staged_lesson_media(
    lesson: VideoLessonPackage,
    cache_root: Path,
    *,
    full_clip_key: Path,
    full_image_key: Path,
    stage_paths: dict[str, tuple[Path, Path]],
    clip_extractor: ExtractReferenceClip,
) -> bool:
    """Copy a reviewed private episode into cache and derive its stage clips.

    Stage windows in the catalog are source-video timestamps.  The staged
    action file begins at ``lesson.playback_start_ms``, so derive the local
    offsets rather than treating the clipped file as a full source video.
    """
    staged = _staged_lesson_media(lesson)
    if staged is None:
        return False
    staged_full_clip, staged_frames = staged
    full_clip = cache_root / full_clip_key
    if not full_clip.is_file():
        shutil.copyfile(staged_full_clip, full_clip)
    if not full_clip.is_file():
        return False
    for stage in lesson.stages:
        image_key, clip_key = stage_paths[stage.stage_id]
        image = cache_root / image_key
        clip = cache_root / clip_key
        if not image.is_file():
            shutil.copyfile(staged_frames[stage.stage_id], image)
        if not clip.is_file():
            start_ms = max(
                0,
                int(stage.reference.window_start_ms or 0) - lesson.playback_start_ms,
            )
            end_ms = max(
                start_ms + 1,
                int(stage.reference.window_end_ms or 0) - lesson.playback_start_ms,
            )
            clip_extractor(full_clip, start_ms, end_ms, clip)
        if not image.is_file() or not clip.is_file():
            return False
    return (cache_root / full_image_key).is_file()


def ensure_video_lesson_media(
    lesson: VideoLessonPackage,
    cache_root: Path,
    downloader: DownloadSource = download_public_source,
    frame_extractor: ExtractReferenceFrame = extract_reference_frame,
    clip_extractor: ExtractReferenceClip = extract_reference_clip,
) -> VideoLessonPackage:
    """Materialize one full episode and all ordered stage media from one download."""
    lesson_root = cache_root / _lesson_root(lesson)
    lesson_root.mkdir(parents=True, exist_ok=True)
    full_clip_key = _full_clip_key(lesson)
    full_clip = cache_root / full_clip_key
    full_image_key = _full_image_key(lesson)
    full_image = cache_root / full_image_key
    stage_paths = {
        stage.stage_id: _stage_media_keys(lesson, stage.stage_id, stage.reference)
        for stage in lesson.stages
    }
    complete = full_clip.is_file() and full_image.is_file() and all(
        (cache_root / image_key).is_file() and (cache_root / clip_key).is_file()
        for image_key, clip_key in stage_paths.values()
    )
    if not complete:
        try:
            _prime_from_staged_lesson_media(
                lesson,
                cache_root,
                full_clip_key=full_clip_key,
                full_image_key=full_image_key,
                stage_paths=stage_paths,
                clip_extractor=clip_extractor,
            )
        except Exception:
            # A malformed optional staging tree must not make a public source
            # unusable.  The normal acquisition path below retains its own
            # bounded error handling and reports a clear limitation if needed.
            pass
        complete = full_clip.is_file() and full_image.is_file() and all(
            (cache_root / image_key).is_file() and (cache_root / clip_key).is_file()
            for image_key, clip_key in stage_paths.values()
        )
    if complete:
        return _cached_lesson(
            lesson,
            full_clip_key=full_clip_key,
            full_image_key=full_image_key,
            stage_paths=stage_paths,
        )

    download_dir = cache_root / ".downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    attempt_id = uuid4().hex
    transient = download_dir / (
        f"{lesson.coach_id}-{lesson.source_id}-{lesson.lesson_id}-{attempt_id}.mp4"
    )
    staging_files: list[Path] = []
    try:
        downloader(lesson.source_url, transient)
        if not full_clip.is_file():
            staging = full_clip.with_name(f".{full_clip.stem}-{attempt_id}.tmp.mp4")
            staging_files.append(staging)
            clip_extractor(
                transient,
                lesson.playback_start_ms,
                lesson.playback_end_ms,
                staging,
            )
            if not staging.is_file():
                raise RuntimeError("video_lesson_full_clip_extraction_failed")
            staging.replace(full_clip)
        if not full_image.is_file() and not lesson.stages:
            image_staging = full_image.with_name(
                f".{full_image.stem}-{attempt_id}.tmp{full_image.suffix}"
            )
            staging_files.append(image_staging)
            frame_extractor(
                transient, lesson.full_reference.timestamp_ms, image_staging
            )
            if not image_staging.is_file():
                raise RuntimeError("video_lesson_full_frame_extraction_failed")
            image_staging.replace(full_image)

        stage_references: dict[str, CoachReference] = {}
        for stage in lesson.stages:
            image_key, clip_key = stage_paths[stage.stage_id]
            image = cache_root / image_key
            clip = cache_root / clip_key
            image.parent.mkdir(parents=True, exist_ok=True)
            if not image.is_file():
                image_staging = image.with_name(
                    f".{image.stem}-{attempt_id}.tmp{image.suffix}"
                )
                staging_files.append(image_staging)
                frame_extractor(transient, stage.reference.timestamp_ms, image_staging)
                if not image_staging.is_file():
                    raise RuntimeError("video_lesson_stage_frame_extraction_failed")
                image_staging.replace(image)
            if not clip.is_file():
                clip_staging = clip.with_name(
                    f".{clip.stem}-{attempt_id}.tmp{clip.suffix}"
                )
                staging_files.append(clip_staging)
                clip_extractor(
                    transient,
                    int(stage.reference.window_start_ms or 0),
                    int(stage.reference.window_end_ms or 0),
                    clip_staging,
                )
                if not clip_staging.is_file():
                    raise RuntimeError("video_lesson_stage_clip_extraction_failed")
                clip_staging.replace(clip)
            stage_references[stage.stage_id] = _cached_reference(
                stage.reference,
                image_key,
                clip_key,
                int(stage.reference.window_start_ms or 0),
                int(stage.reference.window_end_ms or 0),
            )

        full_reference = _cached_reference(
            lesson.full_reference,
            full_image_key,
            full_clip_key,
            lesson.playback_start_ms,
            lesson.playback_end_ms,
        )
        return replace_lesson_references(
            lesson,
            full_reference=full_reference,
            stage_references=stage_references,
        )
    finally:
        for staging in staging_files:
            staging.unlink(missing_ok=True)
        if download_dir.exists():
            for candidate in download_dir.glob(f"{transient.stem}*"):
                candidate.unlink(missing_ok=True)
