#!/usr/bin/env python3
"""Export one reviewed coach action as a browser-safe clip and ordered frames."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Keyframe:
    filename: str
    timestamp: float


def parse_keyframe(value: str) -> Keyframe:
    try:
        filename, timestamp_text = value.rsplit("=", 1)
        timestamp = float(timestamp_text)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            "keyframes must use FILENAME=ABSOLUTE_SECONDS"
        ) from exc
    if not filename.endswith(".jpg") or Path(filename).name != filename:
        raise argparse.ArgumentTypeError("keyframe filename must be a plain .jpg name")
    return Keyframe(filename=filename, timestamp=timestamp)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe_duration(ffprobe: str, video: Path) -> float:
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    return float(payload["format"]["duration"])


def export_lesson(args: argparse.Namespace) -> None:
    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_file():
        raise SystemExit(f"source video does not exist: {source}")
    if args.end <= args.start:
        raise SystemExit("--end must be greater than --start")
    if len(args.keyframe) != 7:
        raise SystemExit("exactly seven --keyframe values are required")
    filenames = [item.filename for item in args.keyframe]
    if len(set(filenames)) != len(filenames):
        raise SystemExit("keyframe filenames must be unique")
    for item in args.keyframe:
        if not args.start <= item.timestamp <= args.end:
            raise SystemExit(
                f"keyframe {item.filename} at {item.timestamp} is outside the clip window"
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as raw:
        temporary = Path(raw)
        frame_dir = temporary / "keyframes"
        frame_dir.mkdir()
        clip = temporary / "action.mp4"

        run(
            [
                args.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{args.start:.3f}",
                "-t",
                f"{args.end - args.start:.3f}",
                "-i",
                str(source),
                "-an",
                "-vf",
                "scale=360:-2:flags=lanczos",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "28",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(clip),
            ]
        )

        for item in args.keyframe:
            run(
                [
                    args.ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    f"{item.timestamp:.3f}",
                    "-i",
                    str(source),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=360:-2:flags=lanczos",
                    "-q:v",
                    "3",
                    str(frame_dir / item.filename),
                ]
            )

        duration = probe_duration(args.ffprobe, clip)
        expected = args.end - args.start
        if abs(duration - expected) > 0.15:
            raise SystemExit(
                f"exported duration {duration:.3f}s differs from expected {expected:.3f}s"
            )
        if output.exists():
            shutil.rmtree(output)
        temporary.rename(output)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--source", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--start", type=float, required=True)
    result.add_argument("--end", type=float, required=True)
    result.add_argument(
        "--keyframe",
        action="append",
        type=parse_keyframe,
        required=True,
        help="ordered FILENAME=ABSOLUTE_SECONDS; provide exactly seven",
    )
    result.add_argument("--ffmpeg", default="ffmpeg")
    result.add_argument("--ffprobe", default="ffprobe")
    return result


if __name__ == "__main__":
    export_lesson(parser().parse_args())
