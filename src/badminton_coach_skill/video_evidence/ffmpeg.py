from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class VideoMetadata:
    duration_ms: int
    width: int
    height: int
    fps: float


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def probe_video(video_path: Path) -> VideoMetadata:
    """Read video metadata using ffprobe without decoding frames."""
    output = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate:format=duration",
            "-of",
            "json",
            str(video_path),
        ]
    )
    payload = json.loads(output.stdout)
    streams = payload.get("streams", [])
    if not streams:
        raise ValueError("No video stream found")
    stream = streams[0]
    numerator, denominator = str(stream.get("r_frame_rate", "0/1")).split("/", 1)
    fps = float(numerator) / max(float(denominator), 1.0)
    return VideoMetadata(
        duration_ms=round(float(payload.get("format", {}).get("duration", 0.0)) * 1000),
        width=int(stream["width"]),
        height=int(stream["height"]),
        fps=fps,
    )


def normalize_video(
    input_path: Path, output_path: Path, analysis_fps: int = 30, max_width: int = 1280
) -> VideoMetadata:
    """Create a rotation-aware H.264 derivative with a stable analysis timebase."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-map",
            "0:v:0",
            "-an",
            "-vf",
            f"fps={analysis_fps},scale='min({max_width},iw)':-2:force_original_aspect_ratio=decrease",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return probe_video(output_path)


def extract_frame(video_path: Path, timestamp_ms: int, output_path: Path) -> None:
    """Extract one exact timestamp proxy frame without exposing source paths."""
    if timestamp_ms < 0:
        raise ValueError("timestamp_ms must be non-negative")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{timestamp_ms / 1000:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output_path),
        ]
    )
