from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
from dataclasses import replace
from typing import Callable
from uuid import uuid4

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
        review_status=reference.review_status,
        teaching_use=reference.teaching_use,
    )


DownloadSource = Callable[[str, Path], None]
ExtractReferenceFrame = Callable[[Path, int, Path], None]
ExtractReferenceClip = Callable[[Path, int, int, Path], None]
PUBLIC_SOURCE_TIMEOUT_SECONDS = 120
PUBLIC_SOURCE_MAX_BYTES = 512 * 1024 * 1024
PUBLIC_SOURCE_DOWNLOAD_ATTEMPTS = 2
PUBLIC_REFERENCE_FORMAT = "bestvideo[width<=480][ext=mp4]/best[width<=480][ext=mp4]/bestvideo[ext=mp4]/best[ext=mp4]"
PUBLIC_REFERENCE_FORMAT_SORT = "res,+size"


class PublicSourceDownloadError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def download_public_source_in_process(source_url: str, target: Path) -> None:
    """Use yt-dlp in the current worker process for high-latency shared environments."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    from ..video_evidence.ffmpeg import ffmpeg_executable

    options = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "socket_timeout": 20,
        "retries": 2,
        "fragment_retries": 2,
        "max_filesize": PUBLIC_SOURCE_MAX_BYTES,
        "format": PUBLIC_REFERENCE_FORMAT,
        "format_sort": PUBLIC_REFERENCE_FORMAT_SORT.split(","),
        "outtmpl": str(target),
        "ffmpeg_location": ffmpeg_executable(),
        "postprocessors": [
            {"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}
        ],
    }
    try:
        with YoutubeDL(options) as downloader:
            result = downloader.download([source_url])
    except DownloadError as error:
        target.unlink(missing_ok=True)
        raise PublicSourceDownloadError("public_source_download_rejected") from error
    except OSError as error:
        target.unlink(missing_ok=True)
        raise PublicSourceDownloadError("public_source_download_io_error") from error
    if result != 0 or not target.is_file():
        target.unlink(missing_ok=True)
        raise PublicSourceDownloadError("public_source_download_failed")


def download_public_source(source_url: str, target: Path) -> None:
    """Download one public source to a private transient location for frame extraction."""
    mode = os.environ.get("BADMINTON_YTDLP_MODE", "subprocess").strip().lower()
    if mode == "in_process":
        download_public_source_in_process(source_url, target)
        return
    if mode != "subprocess":
        raise PublicSourceDownloadError("unsupported_ytdlp_mode")
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
    timed_out = False
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
        except subprocess.TimeoutExpired:
            timed_out = True
            continue
        except OSError:
            continue
        if completed.returncode == 0 and target.exists():
            return
    raise PublicSourceDownloadError(
        "public_source_download_timeout" if timed_out else "public_source_download_failed"
    )


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


def _ensure_reference_media(
    reference: CoachReference,
    cache_root: Path,
    downloader: DownloadSource = download_public_source,
    extractor: ExtractReferenceFrame = extract_reference_frame,
    clip_extractor: ExtractReferenceClip = extract_reference_clip,
    *,
    backfill_clip: bool,
) -> CoachReference:
    relative = _relative_image_key(reference)
    cached_image = cache_root / relative
    clip_relative = _relative_clip_key(reference)
    cached_clip = cache_root / clip_relative
    clip_start_ms, clip_end_ms = _reference_clip_window(reference)
    if cached_image.is_file() and cached_clip.is_file():
        return replace(
            reference,
            availability="cached",
            media_key=str(relative),
            clip_media_key=str(clip_relative),
            clip_start_ms=clip_start_ms,
            clip_end_ms=clip_end_ms,
        )
    if cached_image.is_file() and not backfill_clip:
        return replace(
            reference,
            availability="cached",
            media_key=str(relative),
            clip_media_key="",
            clip_start_ms=None,
            clip_end_ms=None,
        )

    download_dir = cache_root / ".downloads"
    attempt_id = uuid4().hex
    transient = download_dir / (
        f"{reference.coach_id}-{reference.source_id}-{attempt_id}.mp4"
    )
    image_staging = cached_image.with_name(
        f".{cached_image.stem}-{attempt_id}.tmp{cached_image.suffix}"
    )
    clip_staging = cached_clip.with_name(
        f".{cached_clip.stem}-{attempt_id}.tmp{cached_clip.suffix}"
    )
    try:
        downloader(reference.source_url, transient)
        if not cached_image.is_file():
            extractor(transient, reference.timestamp_ms, image_staging)
            if not image_staging.is_file():
                raise RuntimeError("reference_frame_extraction_failed")
            image_staging.replace(cached_image)
        if not cached_image.is_file():
            raise RuntimeError("reference_frame_extraction_failed")
        if not cached_clip.is_file():
            try:
                clip_extractor(transient, clip_start_ms, clip_end_ms, clip_staging)
                if not clip_staging.is_file():
                    raise RuntimeError("reference_clip_extraction_failed")
                clip_staging.replace(cached_clip)
            except Exception:
                return replace(
                    reference,
                    availability="cached",
                    media_key=str(relative),
                    clip_media_key="",
                    clip_start_ms=None,
                    clip_end_ms=None,
                    limitations=tuple(
                        dict.fromkeys(
                            (*reference.limitations, "reference_clip_acquisition_failed")
                        )
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
    except PublicSourceDownloadError as error:
        if cached_image.is_file():
            return replace(
                reference,
                availability="cached",
                media_key=str(relative),
                clip_media_key="",
                clip_start_ms=None,
                clip_end_ms=None,
                limitations=tuple(
                    dict.fromkeys(
                        (
                            *reference.limitations,
                            error.code,
                            "reference_clip_acquisition_failed",
                        )
                    )
                ),
            )
        return replace(
            reference,
            availability="unavailable",
            media_key="",
            clip_media_key="",
            clip_start_ms=None,
            clip_end_ms=None,
            limitations=tuple(
                dict.fromkeys(
                    (*reference.limitations, error.code, "source_acquisition_failed")
                )
            ),
        )
    except Exception:
        if cached_image.is_file():
            return replace(
                reference,
                availability="cached",
                media_key=str(relative),
                clip_media_key="",
                clip_start_ms=None,
                clip_end_ms=None,
                limitations=tuple(
                    dict.fromkeys(
                        (*reference.limitations, "reference_clip_acquisition_failed")
                    )
                ),
            )
        return replace(
            reference,
            availability="unavailable",
            media_key="",
            clip_media_key="",
            clip_start_ms=None,
            clip_end_ms=None,
            limitations=tuple(dict.fromkeys((*reference.limitations, "source_acquisition_failed"))),
        )
    finally:
        image_staging.unlink(missing_ok=True)
        clip_staging.unlink(missing_ok=True)
        for candidate in download_dir.glob(f"{transient.stem}*") if download_dir.exists() else ():
            candidate.unlink(missing_ok=True)


def ensure_reference_image(
    reference: CoachReference,
    cache_root: Path,
    downloader: DownloadSource = download_public_source,
    extractor: ExtractReferenceFrame = extract_reference_frame,
    clip_extractor: ExtractReferenceClip = extract_reference_clip,
) -> CoachReference:
    """Materialize an indexed reference frame and preserve any existing short clip.

    A pre-existing image cache is returned without a network request for compatibility
    with diagnosis jobs that need only a comparison frame.
    """
    return _ensure_reference_media(
        reference,
        cache_root,
        downloader,
        extractor,
        clip_extractor,
        backfill_clip=False,
    )


def ensure_demonstration_media(
    reference: CoachReference,
    cache_root: Path,
    downloader: DownloadSource = download_public_source,
    extractor: ExtractReferenceFrame = extract_reference_frame,
    clip_extractor: ExtractReferenceClip = extract_reference_clip,
) -> CoachReference:
    """Materialize both the demonstration frame and 0.8-second process clip.

    The temporary full video is always removed. Existing image-only caches are safely
    backfilled with the short clip, while failures retain the usable frame.
    """
    return _ensure_reference_media(
        reference,
        cache_root,
        downloader,
        extractor,
        clip_extractor,
        backfill_clip=True,
    )
