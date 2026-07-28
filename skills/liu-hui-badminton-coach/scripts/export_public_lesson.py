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
from typing import Any


MIN_CONTEXT_SIDE_SECONDS = 20.0


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


def load_review_manifest(path: Path, start: float, end: float) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"review manifest does not exist: {path}")
    try:
        review = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid review manifest: {path}") from exc
    if not isinstance(review, dict):
        raise SystemExit("review manifest must be a JSON object")
    if review.get("demonstrator_role") != "coach":
        raise SystemExit("public export requires demonstrator_role=coach")
    if review.get("example_polarity") != "correct":
        raise SystemExit("public export requires example_polarity=correct")
    if review.get("context_review_status") != "agent_reviewed":
        raise SystemExit("public export requires context_review_status=agent_reviewed")
    basis = review.get("review_basis")
    if not isinstance(basis, list) or not basis or any(
        not isinstance(item, str) or not item.strip() for item in basis
    ):
        raise SystemExit("public export requires a non-empty review_basis string list")
    if not isinstance(review.get("source_id"), str) or not review["source_id"].strip():
        raise SystemExit("public export requires source_id")
    if not isinstance(review.get("source_url"), str) or not review["source_url"].startswith(
        ("https://", "http://")
    ):
        raise SystemExit("public export requires an http(s) source_url")
    try:
        reviewed_start = float(review["action_start_seconds"])
        reviewed_end = float(review["action_end_seconds"])
        context_start = float(review["context_start_seconds"])
        context_end = float(review["context_end_seconds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit("review manifest has invalid action/context boundaries") from exc
    if context_start < 0 or reviewed_start < 0 or context_end <= context_start:
        raise SystemExit("review manifest has invalid action/context boundaries")
    if abs(reviewed_start - start) > 0.001 or abs(reviewed_end - end) > 0.001:
        raise SystemExit("export boundaries must exactly match the reviewed action boundaries")
    if (
        start - context_start < MIN_CONTEXT_SIDE_SECONDS
        or context_end - end < MIN_CONTEXT_SIDE_SECONDS
    ):
        raise SystemExit(
            "review context must include at least 20 seconds before and after "
            "the exported action"
        )
    return {
        "version": 1,
        "source_id": review["source_id"].strip(),
        "source_url": review["source_url"],
        "action_start_seconds": reviewed_start,
        "action_end_seconds": reviewed_end,
        "context_start_seconds": context_start,
        "context_end_seconds": context_end,
        "demonstrator_role": "coach",
        "example_polarity": "correct",
        "context_review_status": "agent_reviewed",
        "review_basis": [item.strip() for item in basis],
    }


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
    review = load_review_manifest(args.review_manifest.resolve(), args.start, args.end)

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

        (temporary / "review.json").write_text(
            json.dumps(review, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        existing_readme = output / "README.md"
        if existing_readme.is_file():
            shutil.copy2(existing_readme, temporary / "README.md")

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
        "--review-manifest",
        type=Path,
        required=True,
        help="agent-reviewed JSON proving coach identity and correct-example polarity",
    )
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
