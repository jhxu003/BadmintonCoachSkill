from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from dataclasses import replace
from typing import Callable

from ..video_evidence.contracts import CoachReference


def cache_reference_image(reference: CoachReference, image_path: Path, cache_root: Path) -> CoachReference:
    """Copy an already-authorized extracted reference frame into private cache storage."""
    if not image_path.is_file():
        raise FileNotFoundError(image_path)
    relative = Path(reference.coach_id) / reference.source_id / f"{reference.timestamp_ms}.jpg"
    target = cache_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image_path, target)
    return CoachReference(
        reference_id=reference.reference_id,
        coach_id=reference.coach_id,
        source_id=reference.source_id,
        phase=reference.phase,
        timestamp_ms=reference.timestamp_ms,
        source_url=reference.source_url,
        confidence=reference.confidence,
        actions=reference.actions,
        framework_ids=reference.framework_ids,
        availability="cached",
        media_key=str(relative),
        clip_media_key=reference.clip_media_key,
        clip_start_ms=reference.clip_start_ms,
        clip_end_ms=reference.clip_end_ms,
        title=reference.title,
        window_start_ms=reference.window_start_ms,
        window_end_ms=reference.window_end_ms,
        visible_facts=reference.visible_facts,
        limitations=reference.limitations,
    )


DownloadSource = Callable[[str, Path], None]
ExtractReferenceFrame = Callable[[Path, int, Path], None]
ExtractReferenceClip = Callable[[Path, int, int, Path], None]
PUBLIC_SOURCE_TIMEOUT_SECONDS = 120
PUBLIC_SOURCE_MAX_BYTES = 512 * 1024 * 1024
PUBLIC_SOURCE_DOWNLOAD_ATTEMPTS = 2
PUBLIC_REFERENCE_FORMAT = "bestvideo[width<=480][ext=mp4]/best[width<=480][ext=mp4]/bestvideo[ext=mp4]/best[ext=mp4]"
PUBLIC_REFERENCE_FORMAT_SORT = "res,+size"


def download_public_source(source_url: str, target: Path) -> None:
    """Download one public source to a private transient location for frame extraction."""
    target.parent.mkdir(parents=True, exist_ok=True)
    from ..video_evidence.ffmpeg import ffmpeg_executable

    command = [
        "yt-dlp",
        "--no-playlist",
        "--no-progress",
        "--socket-timeout",
        "20",
        "--retries",
        "2",
        "--fragment-retries",
        "2",
        "--max-filesize",
        str(PUBLIC_SOURCE_MAX_BYTES),
        "--format",
        PUBLIC_REFERENCE_FORMAT,
        "--format-sort",
        PUBLIC_REFERENCE_FORMAT_SORT,
        "--remux-video",
        "mp4",
        "--ffmpeg-location",
        ffmpeg_executable(),
        "--output",
        str(target),
        source_url,
    ]
    for _ in range(PUBLIC_SOURCE_DOWNLOAD_ATTEMPTS):
        target.unlink(missing_ok=True)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=PUBLIC_SOURCE_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if completed.returncode == 0 and target.exists():
            return
    raise RuntimeError("public_source_download_failed")


def extract_reference_frame(video_path: Path, timestamp_ms: int, image_path: Path) -> None:
    from ..video_evidence.ffmpeg import extract_frame

    extract_frame(video_path, timestamp_ms, image_path)


def extract_reference_clip(
    video_path: Path, start_ms: int, end_ms: int, clip_path: Path
) -> None:
    from ..video_evidence.ffmpeg import extract_clip

    extract_clip(video_path, start_ms, end_ms, clip_path)


def _relative_image_key(reference: CoachReference) -> Path:
    return Path(reference.coach_id) / reference.source_id / f"{reference.timestamp_ms}.jpg"


def _reference_clip_window(reference: CoachReference) -> tuple[int, int]:
    start_ms = max(0, reference.timestamp_ms - 400)
    return start_ms, start_ms + 800


def _relative_clip_key(reference: CoachReference) -> Path:
    start_ms, end_ms = _reference_clip_window(reference)
    return (
        Path(reference.coach_id)
        / reference.source_id
        / f"{reference.timestamp_ms}-{start_ms}-{end_ms}.mp4"
    )


def ensure_reference_image(
    reference: CoachReference,
    cache_root: Path,
    downloader: DownloadSource = download_public_source,
    extractor: ExtractReferenceFrame = extract_reference_frame,
    clip_extractor: ExtractReferenceClip = extract_reference_clip,
) -> CoachReference:
    """Materialize one indexed public reference as a private cached frame when possible.

    The temporary full video is always removed. Failures preserve provenance and are
    returned as an explicit unavailable state instead of silently substituting media.
    """
    relative = _relative_image_key(reference)
    cached_image = cache_root / relative
    clip_relative = _relative_clip_key(reference)
    cached_clip = cache_root / clip_relative
    clip_start_ms, clip_end_ms = _reference_clip_window(reference)
    if cached_image.is_file():
        cached_clip_key = str(clip_relative) if cached_clip.is_file() else ""
        return replace(
            reference,
            availability="cached",
            media_key=str(relative),
            clip_media_key=cached_clip_key,
            clip_start_ms=clip_start_ms if cached_clip_key else None,
            clip_end_ms=clip_end_ms if cached_clip_key else None,
        )

    download_dir = cache_root / ".downloads"
    transient = download_dir / f"{reference.coach_id}-{reference.source_id}.mp4"
    try:
        downloader(reference.source_url, transient)
        extractor(transient, reference.timestamp_ms, cached_image)
        if not cached_image.is_file():
            raise RuntimeError("reference_frame_extraction_failed")
        try:
            clip_extractor(transient, clip_start_ms, clip_end_ms, cached_clip)
        except Exception:
            return replace(
                reference,
                availability="cached",
                media_key=str(relative),
                limitations=tuple(
                    dict.fromkeys((*reference.limitations, "reference_clip_acquisition_failed"))
                ),
            )
        if not cached_clip.is_file():
            raise RuntimeError("reference_clip_extraction_failed")
        return replace(
            reference,
            availability="cached",
            media_key=str(relative),
            clip_media_key=str(clip_relative),
            clip_start_ms=clip_start_ms,
            clip_end_ms=clip_end_ms,
        )
    except Exception:
        return replace(
            reference,
            availability="unavailable",
            media_key="",
            limitations=tuple(dict.fromkeys((*reference.limitations, "source_acquisition_failed"))),
        )
    finally:
        for candidate in download_dir.glob(f"{transient.stem}*") if download_dir.exists() else ():
            candidate.unlink(missing_ok=True)
