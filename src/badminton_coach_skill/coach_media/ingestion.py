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
        title=reference.title,
        window_start_ms=reference.window_start_ms,
        window_end_ms=reference.window_end_ms,
        visible_facts=reference.visible_facts,
        limitations=reference.limitations,
    )


DownloadSource = Callable[[str, Path], None]
ExtractReferenceFrame = Callable[[Path, int, Path], None]


def download_public_source(source_url: str, target: Path) -> None:
    """Download one public source to a private transient location for frame extraction."""
    target.parent.mkdir(parents=True, exist_ok=True)
    from ..video_evidence.ffmpeg import ffmpeg_executable

    completed = subprocess.run(
        [
            "yt-dlp",
            "--no-playlist",
            "--no-progress",
            "--remux-video",
            "mp4",
            "--ffmpeg-location",
            ffmpeg_executable(),
            "--output",
            str(target),
            source_url,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not target.exists():
        raise RuntimeError("public_source_download_failed")


def extract_reference_frame(video_path: Path, timestamp_ms: int, image_path: Path) -> None:
    from ..video_evidence.ffmpeg import extract_frame

    extract_frame(video_path, timestamp_ms, image_path)


def _relative_image_key(reference: CoachReference) -> Path:
    return Path(reference.coach_id) / reference.source_id / f"{reference.timestamp_ms}.jpg"


def ensure_reference_image(
    reference: CoachReference,
    *,
    cache_root: Path,
    downloader: DownloadSource = download_public_source,
    extractor: ExtractReferenceFrame = extract_reference_frame,
) -> CoachReference:
    """Materialize one indexed public reference as a private cached frame when possible.

    The temporary full video is always removed. Failures preserve provenance and are
    returned as an explicit unavailable state instead of silently substituting media.
    """
    relative = _relative_image_key(reference)
    cached_image = cache_root / relative
    if cached_image.is_file():
        return replace(reference, availability="cached", media_key=str(relative))

    download_dir = cache_root / ".downloads"
    transient = download_dir / f"{reference.coach_id}-{reference.source_id}.mp4"
    try:
        downloader(reference.source_url, transient)
        extractor(transient, reference.timestamp_ms, cached_image)
        if not cached_image.is_file():
            raise RuntimeError("reference_frame_extraction_failed")
        return replace(reference, availability="cached", media_key=str(relative))
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
