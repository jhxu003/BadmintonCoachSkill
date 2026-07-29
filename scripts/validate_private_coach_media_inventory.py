#!/usr/bin/env python3
"""Decode-check private coach clips and staged frames on a compute node."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


def dhash(path: Path) -> int:
    with Image.open(path) as image:
        image.load()
        gray = image.convert("L").resize((9, 8))
        pixels = list(gray.getdata())
    value = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            value = (value << 1) | int(
                pixels[offset + column] > pixels[offset + column + 1]
            )
    return value


def ffprobe(ffprobe_path: Path, clip: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(ffprobe_path),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,duration:format=duration",
            "-of",
            "json",
            str(clip),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffprobe", type=Path, required=True)
    args = parser.parse_args()

    project = args.project.resolve()
    rows = [
        json.loads(line)
        for line in args.assets.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [row for row in rows if not row.get("duplicate_of")]
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    clip_durations: list[float] = []
    dimensions: Counter[str] = Counter()
    coach_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for number, row in enumerate(rows, start=1):
        asset_id = row["asset_id"]
        coach_counts[row["coach"]]["assets"] += 1
        clip = project / row["clip"]
        try:
            probe = ffprobe(args.ffprobe, clip)
            streams = probe.get("streams") or []
            if not streams:
                raise RuntimeError("video_stream_missing")
            stream = streams[0]
            duration = float(
                stream.get("duration") or (probe.get("format") or {}).get("duration")
            )
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
            if duration <= 0 or width <= 0 or height <= 0:
                raise RuntimeError("invalid_video_geometry_or_duration")
            expected = float(row["clip_end_seconds"]) - float(row["clip_start_seconds"])
            if abs(duration - expected) > max(0.75, expected * 0.20):
                warnings.append(
                    {
                        "asset_id": asset_id,
                        "kind": "clip_duration_mismatch",
                        "expected_seconds": round(expected, 3),
                        "actual_seconds": round(duration, 3),
                    }
                )
            clip_durations.append(duration)
            dimensions[f"{width}x{height}"] += 1
            coach_counts[row["coach"]]["valid_clips"] += 1
        except Exception as error:  # keep validating the corpus
            failures.append(
                {
                    "asset_id": asset_id,
                    "kind": "clip_decode_failed",
                    "path": str(clip),
                    "error": f"{type(error).__name__}:{error}",
                }
            )

        frame_hashes: list[str] = []
        frame_dhashes: list[int] = []
        frame_sizes: list[str] = []
        for frame_rel in row["frames"]:
            frame = project / frame_rel
            try:
                digest = hashlib.sha256(frame.read_bytes()).hexdigest()
                with Image.open(frame) as image:
                    image.load()
                    width, height = image.size
                if width <= 0 or height <= 0:
                    raise RuntimeError("invalid_image_geometry")
                frame_hashes.append(digest)
                frame_dhashes.append(dhash(frame))
                frame_sizes.append(f"{width}x{height}")
                coach_counts[row["coach"]]["valid_frames"] += 1
            except Exception as error:
                failures.append(
                    {
                        "asset_id": asset_id,
                        "kind": "frame_decode_failed",
                        "path": str(frame),
                        "error": f"{type(error).__name__}:{error}",
                    }
                )
        if len(frame_hashes) != 7:
            failures.append(
                {
                    "asset_id": asset_id,
                    "kind": "stage_frame_count_invalid",
                    "expected": 7,
                    "actual": len(frame_hashes),
                }
            )
        if len(set(frame_hashes)) != len(frame_hashes):
            failures.append(
                {
                    "asset_id": asset_id,
                    "kind": "exact_duplicate_stage_frames",
                    "unique": len(set(frame_hashes)),
                    "actual": len(frame_hashes),
                }
            )
        if len(set(frame_sizes)) > 1:
            warnings.append(
                {
                    "asset_id": asset_id,
                    "kind": "mixed_frame_dimensions",
                    "dimensions": sorted(set(frame_sizes)),
                }
            )
        if len(frame_dhashes) == 7:
            adjacent = [
                (frame_dhashes[index] ^ frame_dhashes[index + 1]).bit_count()
                for index in range(6)
            ]
            if min(adjacent) <= 1:
                warnings.append(
                    {
                        "asset_id": asset_id,
                        "kind": "near_duplicate_adjacent_stage_frames",
                        "minimum_dhash_distance": min(adjacent),
                        "distances": adjacent,
                    }
                )
        if number % 100 == 0:
            print(f"VALIDATED {number}/{len(rows)}", flush=True)

    failure_assets = {row["asset_id"] for row in failures}
    warning_assets = {row["asset_id"] for row in warnings}
    summary = {
        "validation_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host_scope": "compute_node_required",
        "asset_count": len(rows),
        "valid_asset_count": len(rows) - len(failure_assets),
        "failed_asset_count": len(failure_assets),
        "warning_asset_count": len(warning_assets),
        "decoded_clip_count": sum(values["valid_clips"] for values in coach_counts.values()),
        "decoded_frame_count": sum(values["valid_frames"] for values in coach_counts.values()),
        "clip_duration_seconds": {
            "minimum": round(min(clip_durations), 3) if clip_durations else None,
            "maximum": round(max(clip_durations), 3) if clip_durations else None,
            "mean": round(sum(clip_durations) / len(clip_durations), 3)
            if clip_durations
            else None,
        },
        "clip_dimensions": dict(dimensions.most_common()),
        "coaches": {coach: dict(values) for coach, values in sorted(coach_counts.items())},
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in summary.items() if key not in {"failures", "warnings"}},
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
