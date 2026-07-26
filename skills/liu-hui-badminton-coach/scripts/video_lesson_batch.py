#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Iterable
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont
import yaml


BATCH_VERSION = 1
PHASES = [
    ("preparation", "preparation", "准备"),
    ("start", "start", "启动"),
    ("loading", "top_elbow", "引拍／加载"),
    ("acceleration", "top_elbow", "加速前段"),
    ("contact_neighborhood", "contact_window", "近似击球窗口"),
    ("release", "contact_window", "释放"),
    ("follow_through", "follow_through", "随挥"),
    ("recovery", "recovery", "回收"),
    ("ready_again", "recovery", "恢复稳定"),
]
CLASSIFICATIONS = {
    "continuous_demonstration",
    "partial_demonstration",
    "static_explanation",
    "concept_only",
    "reject",
}
CONFIDENCES = {"low", "medium", "high"}
VISIBILITIES = {"clear", "intermittent", "not_visible", "unclear"}
PURITIES = {"low", "medium", "high"}
COMPATIBILITIES = {"yes", "unclear", "no"}
STAGE_CODES = {
    "preparation",
    "start",
    "overhead_loading",
    "contact_neighborhood",
    "follow_through",
    "recovery",
}
EVIDENCE_CODES = {
    "full_action_trajectory",
    "partial_action_trajectory",
    "body_visible",
    "racket_visible",
    "recovery_visible",
    "multiple_repetitions",
    "talking_or_pointing",
    "isolated_racket_manipulation",
    "grip_or_racket_face_explanation",
    "shuttle_throw_without_racket_action",
    "ordinary_hand_gesture",
}
LIMITATION_CODES = {
    "exact_contact_not_visible",
    "sparse_sampling",
    "incomplete_sequence",
    "technique_variant_visual_ambiguous",
    "no_full_action",
    "person_or_racket_occluded",
}
REJECTING_EVIDENCE = {
    "isolated_racket_manipulation",
    "grip_or_racket_face_explanation",
    "shuttle_throw_without_racket_action",
    "ordinary_hand_gesture",
}


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def atomic_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    temporary.replace(path)


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def probe_duration(source: Path, ffmpeg: Path) -> float:
    completed = run(
        [
            str(ffmpeg.with_name("ffprobe")),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(source),
        ],
        capture=True,
    )
    return float(completed.stdout.decode().strip())


def load_routes(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    routes = sorted(
        document["routes"], key=lambda row: int(row.get("priority", 0)), reverse=True
    )
    for route in routes:
        route["_regex"] = re.compile(str(route["pattern"]), re.IGNORECASE)
    document["routes"] = routes
    document["route_map"] = {route["route_id"]: route for route in routes}
    return document


def source_index(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle, delimiter="\t")}


def extract_bvid(*values: str) -> str:
    for value in values:
        match = re.search(r"BV[0-9A-Za-z]+", value or "")
        if match:
            return match.group(0)
    return ""


def choose_rows(
    rows: list[dict[str, Any]], start: int, stop: int | None, shard: int, shards: int
) -> list[dict[str, Any]]:
    sliced = rows[start:stop]
    if shards < 1 or not 0 <= shard < shards:
        raise ValueError("invalid shard selection")
    return [row for index, row in enumerate(sliced) if index % shards == shard]


def selected_rows(manifest: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    rows = list(manifest["videos"])
    requested = set(getattr(args, "job_id", []) or [])
    if requested:
        available = {str(row["job_id"]) for row in rows}
        missing = sorted(requested.difference(available))
        if missing:
            raise RuntimeError(f"requested_job_ids_missing:{','.join(missing)}")
        rows = [row for row in rows if str(row["job_id"]) in requested]
    return choose_rows(rows, args.start, args.stop, args.shard, args.shards)


def private_video_root(raw_root: Path, job_id: str) -> Path:
    """Resolve either the legacy flat corpus or a restored nested corpus."""
    direct = raw_root / job_id
    nested = raw_root / "video-corpus" / job_id
    if direct.is_dir() or not nested.is_dir():
        return direct
    return nested


def private_asset(raw_root: Path, job_id: str, filename: str) -> Path:
    return private_video_root(raw_root, job_id) / filename


def resolve_source(raw_root: Path, source_cache: Path, video: dict[str, Any]) -> Path:
    """Prefer a cached source, then an already restored private source.

    The latter avoids a second network download or a 56 GB corpus copy during
    migration recovery.  A missing source is intentionally returned as the
    cache location so download_source retains its existing error handling.
    """
    cached = source_cache / f"{video['job_id']}.mp4"
    if cached.is_file() and cached.stat().st_size > 0:
        return cached
    restored = private_asset(raw_root, str(video["job_id"]), "source_video.mp4")
    if restored.is_file() and restored.stat().st_size > 0:
        return restored
    return cached


def command_inventory(args: argparse.Namespace) -> None:
    review = yaml.safe_load(args.asr_review.read_text(encoding="utf-8"))
    indexed = source_index(args.source_index)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in review["windows"]:
        grouped.setdefault(str(row["job_id"]), []).append(row)
    videos: list[dict[str, Any]] = []
    for job_id, windows in sorted(grouped.items()):
        first = windows[0]
        source_id = str(first["source_id"])
        source = indexed.get(source_id, {})
        metadata_path = private_asset(args.raw_root, job_id, "metadata.json")
        metadata: dict[str, Any] = {}
        if metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metadata = {}
        title = str(first.get("source_title") or source.get("title") or metadata.get("title") or source_id)
        url = str(source.get("url") or metadata.get("webpage_url") or "")
        duration = float(metadata.get("duration") or max(float(row["end_seconds"]) for row in windows))
        videos.append(
            {
                "video_index": len(videos),
                "job_id": job_id,
                "source_id": source_id,
                "title": title,
                "url": url,
                "bvid": extract_bvid(url, str(metadata.get("id", "")), job_id),
                "duration_seconds": round(duration, 3),
                "metadata_available": metadata_path.is_file(),
                "private_asr_available": private_asset(args.raw_root, job_id, "asr.json").is_file(),
                "semantic_windows": [
                    {
                        "window_id": str(row["window_id"]),
                        "start_seconds": float(row["start_seconds"]),
                        "end_seconds": float(row["end_seconds"]),
                        "topic_tags": list(row.get("topic_tags", [])),
                        "signal_status": str(row.get("signal_status", "")),
                    }
                    for row in sorted(windows, key=lambda item: float(item["start_seconds"]))
                ],
            }
        )
    if args.expected_count and len(videos) != args.expected_count:
        raise RuntimeError(f"expected {args.expected_count} videos, found {len(videos)}")
    payload = {
        "batch_version": BATCH_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "video_count": len(videos),
        "semantic_window_count": sum(len(row["semantic_windows"]) for row in videos),
        "source_duration_hours": round(sum(row["duration_seconds"] for row in videos) / 3600, 3),
        "videos": videos,
    }
    atomic_json(args.output, payload)
    print("VIDEO_LESSON_INVENTORY", json.dumps({k: payload[k] for k in ("video_count", "semantic_window_count", "source_duration_hours")}, ensure_ascii=False))


def download_source(video: dict[str, Any], output: Path, yt_dlp: Path) -> None:
    if output.is_file() and output.stat().st_size > 0:
        return
    if not video["url"]:
        raise RuntimeError("source_url_missing")
    temporary_root = output.parent / ".downloads" / f"{video['job_id']}-{uuid4().hex}"
    temporary_root.mkdir(parents=True, exist_ok=False)
    try:
        template = temporary_root / "source.%(ext)s"
        completed = run(
            [
                str(yt_dlp),
                "--no-playlist",
                "--no-warnings",
                "--no-part",
                "--format",
                "bv*[height<=720]/bestvideo[height<=720]/best[height<=720]",
                "--output",
                str(template),
                "--print",
                "after_move:filepath",
                str(video["url"]),
            ],
            capture=True,
        )
        candidates = [Path(line.strip()) for line in completed.stdout.decode().splitlines() if line.strip()]
        candidates = [path for path in candidates if path.is_file()]
        if not candidates:
            candidates = list(temporary_root.glob("source.*"))
        if len(candidates) != 1 or candidates[0].stat().st_size <= 0:
            raise RuntimeError("downloaded_source_not_resolved")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(candidates[0]), output)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def private_window_text(asr: dict[str, Any], start: float, end: float) -> str:
    return " ".join(
        str(segment.get("text", ""))
        for segment in asr.get("segments", [])
        if float(segment.get("end", 0)) > start and float(segment.get("start", 0)) < end
    )


def route_semantic_unit(
    title: str,
    text: str,
    topic_tags: list[str],
    routes: dict[str, Any],
) -> list[dict[str, Any]]:
    title_matches = [route for route in routes["routes"] if route["_regex"].search(title)]
    transcript_matches = [route for route in routes["routes"] if route["_regex"].search(text)]
    if title_matches:
        allowed_actions = {str(route["action"]) for route in title_matches}
        scoped_transcript = [
            route for route in transcript_matches if str(route["action"]) in allowed_actions
        ]
        matches = scoped_transcript or title_matches
        basis = (
            "title_scoped_private_asr_route"
            if scoped_transcript
            else "title_scoped_asr_ambiguous"
        )
    else:
        matches = transcript_matches
        basis = "private_asr_keyword_route"
    if not matches:
        matches = [
            routes["route_map"][routes["topic_fallbacks"][tag]]
            for tag in topic_tags
            if tag in routes.get("topic_fallbacks", {})
        ]
        basis = "reviewed_asr_topic_fallback"
    unique: dict[str, dict[str, Any]] = {}
    for route in matches:
        unique.setdefault(str(route["route_id"]), route)
    matches = sorted(unique.values(), key=lambda row: int(row.get("priority", 0)), reverse=True)
    actions = {str(row["action"]) for row in matches}
    if actions.intersection({"light_drop", "slice_drop", "heavy_slice_drop"}):
        matches = [row for row in matches if row["action"] != "drop"]
    if "jump_smash" in actions:
        matches = [row for row in matches if row["action"] != "smash"]
    if any(action in actions for action in ("forehand_drive", "backhand_drive")):
        matches = [row for row in matches if row["action"] != "drive"]
    technical_actions = actions.difference({"equipment", "racket_preparation"})
    if technical_actions:
        matches = [
            row
            for row in matches
            if row["action"] not in {"equipment", "racket_preparation"}
        ]
    return [
        {
            "route_id": row["route_id"],
            "action": row["action"],
            "label_zh": row["label_zh"],
            "family_id": row["family_id"],
            "taxonomy_path": list(row["taxonomy_path"]),
            "semantic_basis": basis,
        }
        for row in matches[:3]
    ]


def scan_motion(source: Path, ffmpeg: Path, duration: float, fps: float) -> dict[str, Any]:
    import numpy as np

    width, height = 96, 160
    completed = run(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(source),
            "-vf", f"fps={fps:.6f},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=gray",
            "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
        ],
        capture=True,
    )
    pixels = width * height
    count = len(completed.stdout) // pixels
    frames = np.frombuffer(completed.stdout[: count * pixels], dtype=np.uint8).reshape(count, height, width)
    differences = np.abs(frames[1:].astype(np.int16) - frames[:-1].astype(np.int16)).mean(axis=(1, 2))
    return {
        "duration_seconds": duration,
        "fps": fps,
        "frame_count": count,
        "difference_scores": [round(float(value), 5) for value in differences],
    }


def motion_candidates(
    motion: dict[str, Any], start: float, end: float, focus: float, count: int
) -> list[tuple[float, float, float]]:
    import numpy as np

    fps = float(motion["fps"])
    values = np.asarray(motion["difference_scores"], dtype=np.float32)
    left = max(0, int(math.floor(start * fps)))
    right = min(len(values), int(math.ceil(end * fps)))
    segment = values[left:right]
    if len(segment) < 1:
        return []
    sustained_window = min(len(segment), max(1, int(round(focus * fps))))
    burst_window = min(
        len(segment), max(1, int(round(min(1.5, focus) * fps)))
    )
    proposals: list[tuple[float, float, float]] = []
    ranked: list[tuple[float, int, int]] = []
    for scale_order, window in enumerate((sustained_window, burst_window)):
        scores = np.convolve(
            segment, np.ones(window, dtype=np.float32) / window, mode="valid"
        )
        ranked.extend(
            (float(scores[index]), scale_order, int(index))
            for index in np.argsort(scores)[::-1]
        )
    for score, scale_order, index in sorted(ranked, reverse=True):
        window = sustained_window if scale_order == 0 else burst_window
        peak_center = left / fps + (float(index) + window / 2) / fps
        candidate_start = max(start, peak_center - focus / 2)
        candidate_end = min(end, candidate_start + focus)
        candidate_start = max(start, candidate_end - focus)
        center = (candidate_start + candidate_end) / 2
        if any(
            abs(center - (a + b) / 2) < focus * 0.8 for a, b, _ in proposals
        ):
            continue
        proposals.append(
            (
                round(candidate_start, 4),
                round(candidate_end, 4),
                round(score, 5),
            )
        )
        if len(proposals) >= count:
            break
    return proposals


def temporal_pose_candidates(
    pose_root: Path | None,
    job_id: str,
    duration: float,
    focus: float,
) -> list[tuple[float, float, float]]:
    """Turn pre-reviewed dense-pose spans into bounded VLM candidates.

    A pose sequence only identifies a compact visible-motion interval.  It is
    not itself a lesson decision, so the returned windows still pass through
    the same semantic route and strict VLM action gate as every other
    candidate.  A long, uninterrupted pose group can contain several repeated
    swings.  It is deliberately split into short, lightly overlapping windows
    instead of being centred into one broad candidate: a published episode
    must contain exactly one visible repetition, never a montage of drills.
    """
    if pose_root is None:
        return []
    path = pose_root / job_id / "pose.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        timestamps = sorted(
            float(value) for value in payload.get("timestamps_seconds", [])
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        return []
    groups: list[list[float]] = []
    for timestamp in timestamps:
        if not groups or timestamp - groups[-1][-1] > 0.55:
            groups.append([timestamp])
        else:
            groups[-1].append(timestamp)
    proposals: list[tuple[float, float, float]] = []
    for group_index, group in enumerate(groups, start=1):
        if len(group) < 3:
            continue
        group_start, group_end = group[0], group[-1]
        span = group_end - group_start
        # Keep a small amount of context before/after the pose evidence, but
        # do not turn a compact repetition into a multi-repetition montage.
        left = max(0.0, group_start - 0.16)
        right = min(duration, group_end + 0.16)
        if span <= focus:
            starts = [max(0.0, min(left, duration - focus))]
        else:
            # Cover the pose span with short windows anchored at both ends.
            # This is preferable to a sliding-window flood: the Qwen gate
            # receives enough context for a complete repetition but not a
            # near-duplicate stack of the same repetition.
            count = max(2, math.ceil(span / max(0.65, focus * 0.95)))
            final_start = max(left, right - focus)
            if count == 2:
                starts = [left, final_start]
            else:
                starts = [
                    left + (final_start - left) * index / (count - 1)
                    for index in range(count)
                ]
        for window_index, start in enumerate(starts, start=1):
            end = min(duration, start + focus)
            start = max(0.0, end - focus)
            if end - start < 0.65:
                continue
            # Dominates motion ranking only within the candidate proposal
            # stage; action admission remains entirely VLM-gated.  The tiny
            # suffix makes ordering deterministic without changing ranking.
            score = 100000.0 + len(group) + group_index / 100 + window_index / 10000
            proposals.append((round(start, 4), round(end, 4), score))
    return proposals


def sample_timestamps(start: float, end: float, count: int) -> list[float]:
    inset = min(0.06, max(0.0, (end - start) / (count * 6)))
    return [start + inset + (end - start - 2 * inset) * index / (count - 1) for index in range(count)]


def extract_frame(source: Path, ffmpeg: Path, timestamp: float, output: Path) -> float:
    if output.is_file() and output.stat().st_size > 0:
        return timestamp
    output.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    attempts = list(
        dict.fromkeys(max(0.0, timestamp - offset) for offset in (0, 0.35, 0.75, 1.5, 3.0))
    )
    for actual_timestamp in attempts:
        try:
            run([str(ffmpeg), "-hide_banner", "-loglevel", "fatal", "-y", "-ss", f"{actual_timestamp:.3f}", "-i", str(source), "-frames:v", "1", "-vf", "scale='min(384,iw)':-2", "-q:v", "2", str(output)])
        except subprocess.CalledProcessError as error:
            last_error = error
            continue
        if output.is_file() and output.stat().st_size > 0:
            return actual_timestamp
        last_error = RuntimeError(
            f"ffmpeg produced no frame at {actual_timestamp:.3f}s for {source}"
        )
    assert last_error is not None
    raise last_error


def contact_sheet(paths: list[Path], timestamps: list[float], output: Path) -> None:
    images = [Image.open(path).convert("RGB") for path in paths]
    try:
        columns = 5
        rows = math.ceil(len(images) / columns)
        width = 384
        label = 24
        height = max(image.height for image in images) + label
        sheet = Image.new("RGB", (columns * width, rows * height), "black")
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default()
        for index, (image, timestamp) in enumerate(zip(images, timestamps)):
            x, y = index % columns * width, index // columns * height
            sheet.paste(image, (x, y + label))
            draw.text((x + 6, y + 5), f"{index + 1:02d} {timestamp:.3f}s", fill="white", font=font)
        output.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(output, quality=90)
    finally:
        for image in images:
            image.close()


def video_root(batch_root: Path, video: dict[str, Any]) -> Path:
    return batch_root / "videos" / video["job_id"]


def set_status(root: Path, stage: str, state: str, **extra: Any) -> None:
    previous: dict[str, Any] = {}
    path = root / "status.json"
    if path.is_file():
        previous = json.loads(path.read_text(encoding="utf-8"))
    if state != "failed":
        previous.pop("error", None)
    previous.update({"stage": stage, "state": state, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **extra})
    atomic_json(path, previous)


def command_prepare(args: argparse.Namespace) -> None:
    if args.temporal_pose_only and args.temporal_pose_root is None:
        raise ValueError("--temporal-pose-only requires --temporal-pose-root")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    routes = load_routes(args.routing)
    rows = selected_rows(manifest, args)
    source_cache = args.source_cache or args.batch_root / "sources"
    for number, video in enumerate(rows, start=1):
        root = video_root(args.batch_root, video)
        candidates_path = root / "candidates.json"
        if candidates_path.is_file() and not args.force:
            print("PREPARE_SKIP", video["job_id"], flush=True)
            continue
        try:
            set_status(root, "prepare", "running")
            source = resolve_source(args.raw_root, source_cache, video)
            download_source(video, source, args.yt_dlp)
            duration = probe_duration(source, args.ffmpeg)
            atomic_json(root / "source.json", {"path": str(source), "size": source.stat().st_size, "sha256": sha256(source), "duration_seconds": round(duration, 3)})
            motion_path = root / "motion-scan.json"
            motion = (
                {
                    "duration_seconds": duration,
                    "fps": args.motion_scan_fps,
                    "frame_count": 0,
                    "difference_scores": [],
                    "skipped": "restored_temporal_pose_only",
                }
                if args.temporal_pose_only
                else scan_motion(source, args.ffmpeg, duration, args.motion_scan_fps)
            )
            atomic_json(motion_path, motion)
            asr_path = private_asset(args.raw_root, str(video["job_id"]), "asr.json")
            asr = json.loads(asr_path.read_text(encoding="utf-8")) if asr_path.is_file() else {"segments": []}
            units: list[dict[str, Any]] = []
            candidates: list[dict[str, Any]] = []
            for unit_index, window in enumerate(video["semantic_windows"], start=1):
                text = private_window_text(asr, float(window["start_seconds"]), float(window["end_seconds"]))
                routed = route_semantic_unit(video["title"], text, list(window["topic_tags"]), routes)
                unit = {**window, "semantic_unit_id": f"unit-{unit_index:03d}", "techniques": routed}
                units.append(unit)
                motion_proposals = (
                    []
                    if args.temporal_pose_only
                    else motion_candidates(
                        motion,
                        float(window["start_seconds"]),
                        min(duration, float(window["end_seconds"])),
                        args.focus_seconds,
                        args.candidates_per_unit,
                    )
                )
                for start, end, score in motion_proposals:
                    if any(abs(float(candidate["start_seconds"]) - start) < 0.8 for candidate in candidates):
                        continue
                    primary = routed[0] if routed else {
                        "route_id": "unknown",
                        "action": "unknown",
                        "label_zh": "未知技术候选",
                        "family_id": "unknown",
                        "taxonomy_path": ["unreviewed.unknown"],
                        "semantic_basis": "insufficient_semantic_evidence",
                    }
                    candidates.append({
                        "candidate_id": "",
                        "semantic_unit_id": unit["semantic_unit_id"],
                        "source_window_id": window["window_id"],
                        "start_seconds": start,
                        "end_seconds": end,
                        "motion_score": score,
                        **primary,
                        "techniques": routed,
                    })
            for start, end, score in temporal_pose_candidates(
                args.temporal_pose_root,
                str(video["job_id"]),
                duration,
                args.focus_seconds,
            ):
                center = (start + end) / 2
                matching = [
                    unit
                    for unit in units
                    if float(unit["start_seconds"])
                    <= center
                    <= float(unit["end_seconds"])
                ]
                unit = matching[0] if matching else min(
                    units,
                    key=lambda item: min(
                        abs(center - float(item["start_seconds"])),
                        abs(center - float(item["end_seconds"])),
                    ),
                )
                if any(
                    abs(float(candidate["start_seconds"]) - start) < 0.8
                    for candidate in candidates
                ):
                    continue
                routed = list(unit["techniques"])
                primary = routed[0] if routed else {
                    "route_id": "unknown",
                    "action": "unknown",
                    "label_zh": "未知技术候选",
                    "family_id": "unknown",
                    "taxonomy_path": ["unreviewed.unknown"],
                    "semantic_basis": "insufficient_semantic_evidence",
                }
                candidates.append(
                    {
                        "candidate_id": "",
                        "semantic_unit_id": unit["semantic_unit_id"],
                        "source_window_id": unit["window_id"],
                        "start_seconds": start,
                        "end_seconds": end,
                        "motion_score": score,
                        "candidate_basis": "restored_temporal_pose_seed",
                        **primary,
                        "techniques": routed,
                    }
                )
            by_unit: dict[str, list[dict[str, Any]]] = {}
            for candidate in candidates:
                by_unit.setdefault(candidate["semantic_unit_id"], []).append(candidate)
            primary = [
                max(rows, key=lambda row: float(row["motion_score"]))
                for rows in by_unit.values()
            ]
            primary_ids = {id(row) for row in primary}
            extras = [row for row in candidates if id(row) not in primary_ids]
            candidates = sorted(
                primary, key=lambda row: float(row["motion_score"]), reverse=True
            )[: args.max_candidates_per_video]
            if len(candidates) < args.max_candidates_per_video:
                candidates.extend(
                    sorted(
                        extras,
                        key=lambda row: float(row["motion_score"]),
                        reverse=True,
                    )[: args.max_candidates_per_video - len(candidates)]
                )
            candidates = sorted(candidates, key=lambda row: float(row["start_seconds"]))
            for index, candidate in enumerate(candidates, start=1):
                candidate["candidate_id"] = f"candidate-{index:03d}"
                safe_source_end = max(0.0, duration - 0.35)
                candidate_end = min(
                    float(candidate["end_seconds"]), safe_source_end
                )
                candidate_start = min(
                    float(candidate["start_seconds"]),
                    max(0.0, candidate_end - 0.65),
                )
                candidate["start_seconds"] = round(candidate_start, 4)
                candidate["end_seconds"] = round(candidate_end, 4)
                timestamps = sample_timestamps(float(candidate["start_seconds"]), float(candidate["end_seconds"]), args.frames_per_candidate)
                frame_paths: list[Path] = []
                actual_timestamps: list[float] = []
                for frame_index, timestamp in enumerate(timestamps, start=1):
                    frame = root / "candidate-frames" / candidate["candidate_id"] / f"frame-{frame_index:02d}-{timestamp:.3f}.jpg"
                    actual_timestamps.append(
                        extract_frame(source, args.ffmpeg, timestamp, frame)
                    )
                    frame_paths.append(frame)
                sheet = root / "candidate-sheets" / f"{candidate['candidate_id']}.jpg"
                contact_sheet(frame_paths, actual_timestamps, sheet)
                candidate["timestamps"] = [
                    round(value, 6) for value in actual_timestamps
                ]
                candidate["frame_paths"] = [str(path.relative_to(root)) for path in frame_paths]
                candidate["contact_sheet"] = str(sheet.relative_to(root))
            atomic_json(candidates_path, {"video": video, "semantic_inventory": units, "candidate_count": len(candidates), "candidates": candidates})
            set_status(root, "prepare", "succeeded", candidate_count=len(candidates))
            print("PREPARE_DONE", number, len(rows), video["job_id"], len(candidates), flush=True)
        except Exception as error:
            set_status(root, "prepare", "failed", error=f"{type(error).__name__}:{error}")
            print("PREPARE_FAILED", video["job_id"], repr(error), flush=True)


def gate_prompt(candidate: dict[str, Any]) -> str:
    techniques = candidate.get("techniques") or [candidate]
    racket_required = any(
        technique["family_id"] not in {"footwork", "doubles_context", "equipment"}
        for technique in techniques
    )
    labels = "、".join(
        f"{technique['label_zh']}({technique['action']})" for technique in techniques
    )
    return (
        "Return exactly one minified JSON object and no markdown. The images are ordered frames from one public badminton coaching video. "
        f"The reviewed title/ASR route assigns this window to one of these controlled lesson topics: {labels}. "
        "Do not quote, reconstruct, or summarize subtitles or transcripts. Only verify whether the visible frames contain one real coordinated badminton technique execution compatible with that fixed route. "
        "continuous_demonstration requires a meaningful preparation/start, active movement path, finish, and recovery. partial_demonstration is a genuine execution with a major stage cut. "
        "Talking, pointing, posing, grip adjustment, racket-face placement, isolated wrist/forearm rotation, or a small racket wave while explaining is static_explanation. Throwing a shuttle by hand without executing the routed technique is not an action. "
        "If multiple repetitions are visible, action_repetitions counts all visible repetitions, but action_start_frame and action_end_frame must delimit only the single most complete repetition rather than the whole multi-repetition span. "
        f"Racket visibility required for admission: {str(racket_required).lower()}. Footwork may be admitted without a visible racket. "
        "Output exactly these twelve keys: classification, confidence, demonstration_purity, person_visibility, racket_visibility, action_repetitions, action_start_frame, action_end_frame, visible_stage_coverage, semantic_compatibility, observed_evidence, scope_limitations. "
        "classification is continuous_demonstration, partial_demonstration, static_explanation, concept_only, or reject. confidence and demonstration_purity are low, medium, or high. person_visibility and racket_visibility are clear, intermittent, not_visible, or unclear. "
        "action frame fields are 1-based integers and must span at least three ordered frames; use 0 and 0 when no action exists. visible_stage_coverage uses preparation, start, overhead_loading, contact_neighborhood, follow_through, recovery. semantic_compatibility is yes, unclear, or no. "
        "observed_evidence uses full_action_trajectory, partial_action_trajectory, body_visible, racket_visible, recovery_visible, multiple_repetitions, talking_or_pointing, isolated_racket_manipulation, grip_or_racket_face_explanation, shuttle_throw_without_racket_action, ordinary_hand_gesture. "
        "scope_limitations uses exact_contact_not_visible, sparse_sampling, incomplete_sequence, technique_variant_visual_ambiguous, no_full_action, person_or_racket_occluded. "
        "Consistency rule: continuous_demonstration is permitted only when one complete visible repetition covers its claimed stages. If classification is continuous_demonstration, scope_limitations MUST NOT include no_full_action or incomplete_sequence; use exact_contact_not_visible, sparse_sampling, or technique_variant_visual_ambiguous when those are the only limits. If the visible sequence is not complete, classify partial_demonstration or reject instead. "
        "Never claim exact shuttle contact, racket-face angle, grip pressure, force magnitude, true internal rotation, calibrated 3D biomechanics, or opponent intent."
    )


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str) and value.strip().lower() not in {"", "none", "no", "null"}:
        return [
            item.strip()
            for item in re.split(r"[,，;；]", value)
            if item.strip()
        ]
    return []


def normalize_gate_consistency(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep a model's explicit insufficiency signal fail-closed.

    A model can emit a superficially positive classification together with
    ``no_full_action`` or ``incomplete_sequence``.  Those fields conflict, but
    they are not a licence to promote the clip: removing the limitation turned
    static explanations and truncated motions into publishable lessons.  The
    admission gate below already rejects either limitation, so preserve the
    original structured evidence for human review.
    """
    return payload


def parse_gate(raw: str, frame_count: int) -> tuple[dict[str, Any] | None, str | None]:
    left, right = raw.find("{"), raw.rfind("}")
    if left < 0 or right <= left:
        return None, "json_object_not_found"
    try:
        payload = json.loads(raw[left : right + 1])
    except json.JSONDecodeError as error:
        return None, f"json_decode_error:{error.msg}"
    required = {"classification", "confidence", "demonstration_purity", "person_visibility", "racket_visibility", "action_repetitions", "action_start_frame", "action_end_frame", "visible_stage_coverage", "semantic_compatibility", "observed_evidence", "scope_limitations"}
    if not isinstance(payload, dict):
        return None, "invalid_payload"
    if "action_repetitions" not in payload and payload.get("classification") in {
        "continuous_demonstration",
        "partial_demonstration",
    }:
        payload["action_repetitions"] = 1
    if set(payload) != required:
        return None, "invalid_keys"
    for key in ("action_repetitions", "action_start_frame", "action_end_frame"):
        if isinstance(payload[key], str) and payload[key].isdigit():
            payload[key] = int(payload[key])
    for key in ("visible_stage_coverage", "observed_evidence", "scope_limitations"):
        payload[key] = string_list(payload[key])
    if payload.get("demonstration_purity") in {"not_visible", "unclear", "none"}:
        payload["demonstration_purity"] = "low"
    if payload.get("classification") in {"static_explanation", "concept_only", "reject"}:
        payload["action_repetitions"] = 0
        payload["action_start_frame"] = 0
        payload["action_end_frame"] = 0
        payload["visible_stage_coverage"] = []
    if payload["classification"] not in CLASSIFICATIONS or payload["confidence"] not in CONFIDENCES or payload["demonstration_purity"] not in PURITIES:
        return None, "invalid_classification_or_confidence"
    if payload["person_visibility"] not in VISIBILITIES or payload["racket_visibility"] not in VISIBILITIES or payload["semantic_compatibility"] not in COMPATIBILITIES:
        return None, "invalid_visibility_or_compatibility"
    if not all(isinstance(payload[key], int) for key in ("action_repetitions", "action_start_frame", "action_end_frame")):
        return None, "invalid_action_integer"
    if not set(payload["visible_stage_coverage"]).issubset(STAGE_CODES) or not set(payload["observed_evidence"]).issubset(EVIDENCE_CODES) or not set(payload["scope_limitations"]).issubset(LIMITATION_CODES):
        return None, "invalid_code"
    action = payload["classification"] in {"continuous_demonstration", "partial_demonstration"}
    if action:
        start, end = payload["action_start_frame"], payload["action_end_frame"]
        if (
            not (1 <= start < end <= frame_count and end - start >= 2)
            or REJECTING_EVIDENCE.intersection(payload["observed_evidence"])
        ):
            payload["classification"] = "reject"
            payload["demonstration_purity"] = "low"
            payload["action_repetitions"] = 0
            payload["action_start_frame"] = 0
            payload["action_end_frame"] = 0
            payload["visible_stage_coverage"] = []
            payload["scope_limitations"] = list(
                dict.fromkeys(payload["scope_limitations"] + ["incomplete_sequence"])
            )
    elif payload["action_start_frame"] or payload["action_end_frame"] or payload["action_repetitions"]:
        return None, "non_action_fields_must_be_zero"
    return normalize_gate_consistency(payload), None


def normalized_reject_payload() -> dict[str, Any]:
    """Preserve an unusable model response as a schema-valid non-action result."""
    return {
        "classification": "reject",
        "confidence": "low",
        "demonstration_purity": "low",
        "person_visibility": "unclear",
        "racket_visibility": "unclear",
        "action_repetitions": 0,
        "action_start_frame": 0,
        "action_end_frame": 0,
        "visible_stage_coverage": [],
        "semantic_compatibility": "unclear",
        "observed_evidence": [],
        "scope_limitations": ["incomplete_sequence"],
    }


def admitted(candidate: dict[str, Any], payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    payload = normalize_gate_consistency(dict(payload))
    if payload["classification"] != "continuous_demonstration":
        return False
    if payload["action_repetitions"] != 1:
        return False
    if (
        payload["confidence"] != "high"
        or payload["demonstration_purity"] != "high"
        or payload["semantic_compatibility"] != "yes"
        or payload["person_visibility"] != "clear"
        or len(payload["visible_stage_coverage"]) < 4
        or "full_action_trajectory" not in payload["observed_evidence"]
        or {"no_full_action", "incomplete_sequence"}.intersection(
            payload["scope_limitations"]
        )
    ):
        return False
    if (
        candidate["family_id"]
        not in {"footwork", "doubles_context", "equipment"}
        and payload["racket_visibility"] != "clear"
    ):
        return False
    return not REJECTING_EVIDENCE.intersection(payload["observed_evidence"])


def review_candidate(candidate: dict[str, Any], payload: dict[str, Any] | None) -> bool:
    """Keep strong but incomplete demonstrations for human review only.

    A sparse contact sheet can cut a real action at either end.  It must not
    pass the automatic admission gate, but losing it entirely makes reviewers
    inspect only talking frames.  This predicate intentionally never changes
    ``admitted`` and callers must opt in explicitly before materialising a
    review preview.
    """
    if not payload or payload["classification"] != "partial_demonstration":
        return False
    if payload["action_repetitions"] != 1:
        return False
    if (
        payload["demonstration_purity"] not in {"medium", "high"}
        or payload["semantic_compatibility"] != "yes"
        or payload["person_visibility"] != "clear"
        or len(payload["visible_stage_coverage"]) < 4
        or "full_action_trajectory" not in payload["observed_evidence"]
        or REJECTING_EVIDENCE.intersection(payload["observed_evidence"])
    ):
        return False
    if (
        candidate["family_id"]
        not in {"footwork", "doubles_context", "equipment"}
        and payload["racket_visibility"] != "clear"
    ):
        return False
    return True


def materializable(
    candidate: dict[str, Any], payload: dict[str, Any] | None, include_review_candidates: bool
) -> bool:
    return admitted(candidate, payload) or (
        include_review_candidates and review_candidate(candidate, payload)
    )


def command_gate(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = selected_rows(manifest, args)
    pending_videos = [row for row in rows if (video_root(args.batch_root, row) / "candidates.json").is_file()]
    if not pending_videos:
        print("GATE_NOTHING_TO_DO")
        return

    gate_jobs: list[tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]] = []
    for video in pending_videos:
        root = video_root(args.batch_root, video)
        document = json.loads((root / "candidates.json").read_text(encoding="utf-8"))
        candidate_map = {
            row["candidate_id"]: row for row in document["candidates"]
        }
        results_path = root / "gate-results.jsonl"
        existing: dict[str, dict[str, Any]] = {}
        if results_path.is_file():
            latest_rows: dict[str, dict[str, Any]] = {}
            for line in results_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    candidate = candidate_map.get(row["candidate_id"])
                    # Raw model text is the audit source of truth.  Reparse it
                    # on every resumable gate pass so a previous implementation
                    # cannot preserve a normalised/overwritten payload and turn
                    # an explicit "no_full_action" into an admitted lesson.
                    if candidate and row.get("raw_output"):
                        payload, parse_error = parse_gate(
                            row["raw_output"], len(candidate["frame_paths"])
                        )
                        if not parse_error:
                            row["payload"] = payload
                            row["parse_error"] = None
                        else:
                            row["payload"] = normalized_reject_payload()
                            row["parse_error"] = None
                            row["normalization_error"] = parse_error
                    if candidate and row.get("payload") and not row.get("parse_error"):
                        row["payload"] = normalize_gate_consistency(
                            dict(row["payload"])
                        )
                        row["admitted"] = admitted(candidate, row["payload"])
                        row["review_candidate"] = review_candidate(
                            candidate, row["payload"]
                        )
                        existing[row["candidate_id"]] = row
                    latest_rows[row["candidate_id"]] = row
            compacted = [
                latest_rows[row["candidate_id"]]
                for row in document["candidates"]
                if row["candidate_id"] in latest_rows
            ]
            atomic_jsonl(results_path, compacted)
        if len(existing) == len(document["candidates"]):
            set_status(
                root,
                "gate",
                "succeeded",
                completed_candidates=len(existing),
                admitted_candidates=sum(bool(row["admitted"]) for row in existing.values()),
                review_candidate_count=sum(
                    bool(row.get("review_candidate")) for row in existing.values()
                ),
            )
        else:
            set_status(root, "gate", "running", completed_candidates=len(existing))
            gate_jobs.append((video, document, existing))
        print(
            "GATE_REFRESH",
            video["job_id"],
            len(existing),
            len(document["candidates"]),
            sum(bool(row["admitted"]) for row in existing.values()),
            sum(bool(row.get("review_candidate")) for row in existing.values()),
            flush=True,
        )

    if not gate_jobs:
        print("GATE_REFRESH_COMPLETE")
        return

    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    processor = AutoProcessor.from_pretrained(args.model, local_files_only=True, use_fast=True, min_pixels=4 * 28 * 28, max_pixels=160 * 28 * 28)
    model = AutoModelForImageTextToText.from_pretrained(
        args.model,
        local_files_only=True,
        device_map="auto",
        max_memory={0: os.environ.get("BADMINTON_QWEN_GPU_MAX_MEMORY", "17GiB"), "cpu": os.environ.get("BADMINTON_QWEN_CPU_MAX_MEMORY", "64GiB")},
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
    )
    model.eval()
    for video_number, (video, document, existing) in enumerate(gate_jobs, start=1):
        root = video_root(args.batch_root, video)
        results_path = root / "gate-results.jsonl"
        for candidate_number, candidate in enumerate(document["candidates"], start=1):
            if candidate["candidate_id"] in existing:
                continue
            content: list[dict[str, str]] = []
            for index, (relative, timestamp) in enumerate(zip(candidate["frame_paths"], candidate["timestamps"]), start=1):
                content.extend([{"type": "text", "text": f"Ordered frame {index}, {timestamp:.3f}s"}, {"type": "image", "path": str(root / relative)}])
            content.append({"type": "text", "text": gate_prompt(candidate)})
            chat = processor.apply_chat_template([{"role": "user", "content": content}], tokenize=False, add_generation_prompt=True)
            images = [Image.open(root / relative).convert("RGB") for relative in candidate["frame_paths"]]
            try:
                inputs = processor(text=[chat], images=images, return_tensors="pt", padding=True).to(model.device)
            finally:
                for image in images:
                    image.close()
            torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            with torch.inference_mode():
                generated = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False)
            inference_seconds = time.perf_counter() - started
            input_length = inputs.input_ids.shape[1]
            raw = processor.batch_decode(generated[:, input_length:], skip_special_tokens=True)[0].strip()
            payload, parse_error = parse_gate(raw, len(candidate["frame_paths"]))
            normalization_error = None
            if parse_error:
                normalization_error = parse_error
                payload = normalized_reject_payload()
                parse_error = None
            result = {
                "candidate_id": candidate["candidate_id"],
                "payload": payload,
                "parse_error": parse_error,
                "raw_output": raw,
                "admitted": admitted(candidate, payload),
                "review_candidate": review_candidate(candidate, payload),
                "inference_seconds": round(inference_seconds, 3),
                "peak_gpu_allocated_gib": round(torch.cuda.max_memory_allocated() / 1024**3, 3),
            }
            if normalization_error:
                result["normalization_error"] = normalization_error
            with results_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            print("GATE", video_number, len(gate_jobs), video["job_id"], candidate_number, len(document["candidates"]), candidate["candidate_id"], payload["classification"] if payload else parse_error, result["admitted"], result["review_candidate"], flush=True)
            del inputs, generated
            torch.cuda.empty_cache()
        latest: dict[str, dict[str, Any]] = {}
        for line in results_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                latest[row["candidate_id"]] = row
        rows_done = [latest[row["candidate_id"]] for row in document["candidates"] if row["candidate_id"] in latest]
        atomic_jsonl(results_path, rows_done)
        set_status(
            root,
            "gate",
            "succeeded",
            completed_candidates=len(rows_done),
            admitted_candidates=sum(bool(row["admitted"]) for row in rows_done),
            review_candidate_count=sum(
                bool(row.get("review_candidate")) for row in rows_done
            ),
        )


def overlap(left: tuple[float, float], right: tuple[float, float]) -> float:
    return max(0.0, min(left[1], right[1]) - max(left[0], right[0]))


def action_interval(candidate: dict[str, Any], payload: dict[str, Any]) -> tuple[float, float]:
    timestamps = [float(value) for value in candidate["timestamps"]]
    step = (timestamps[-1] - timestamps[0]) / max(1, len(timestamps) - 1)
    start = max(float(candidate["start_seconds"]), timestamps[payload["action_start_frame"] - 1] - step * 0.45)
    end = min(float(candidate["end_seconds"]), timestamps[payload["action_end_frame"] - 1] + step * 0.45)
    return round(start, 4), round(end, 4)


def episode_score(candidate: dict[str, Any], payload: dict[str, Any]) -> float:
    return round(
        (5 if payload["classification"] == "continuous_demonstration" else 3)
        + {"high": 2, "medium": 1, "low": 0}[payload["demonstration_purity"]]
        + {"yes": 1, "unclear": 0.2, "no": -3}[payload["semantic_compatibility"]]
        + min(1.5, len(payload["visible_stage_coverage"]) * 0.25)
        + min(1, float(candidate["motion_score"]) / 12),
        4,
    )


def stage_tip(family: str, phase_id: str) -> str:
    if family == "footwork":
        tips = {
            "preparation": "观察重心稳定、双脚可启动的准备状态。",
            "start": "观察第一步如何建立移动方向。",
            "loading": "观察身体降重心并为移动或起跳蓄势。",
            "acceleration": "观察连续步伐如何把身体送向目标区域。",
            "contact_neighborhood": "这是动作路线中最接近到位或腾空的阶段，不代表精确击球。",
            "release": "观察完成主要移动后如何释放惯性。",
            "follow_through": "观察落地或制动如何接续发生。",
            "recovery": "观察身体如何重新取得平衡。",
            "ready_again": "观察是否恢复到可衔接下一拍的状态。",
        }
    else:
        tips = {
            "preparation": "观察身体、持拍侧和球拍均处于可启动的准备状态。",
            "start": "观察挥拍如何从等待状态开始建立。",
            "loading": "观察身体与持拍臂如何进入引拍和加载阶段。",
            "acceleration": "观察球拍路线和身体转动如何连续加速。",
            "contact_neighborhood": "这里只标记球拍通过预期击球区域的近似窗口。",
            "release": "观察球拍通过近似窗口后动作如何继续释放。",
            "follow_through": "观察随挥路线，不要把击球窗口当作动作终点。",
            "recovery": "观察随挥后身体和球拍如何回收。",
            "ready_again": "观察动作结束后是否重新形成稳定准备状态。",
        }
    return tips[phase_id]


def extract_clip(source: Path, ffmpeg: Path, start: float, end: float, output: Path) -> None:
    if output.is_file() and output.stat().st_size > 0:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    run([str(ffmpeg), "-hide_banner", "-loglevel", "fatal", "-y", "-ss", f"{start:.3f}", "-t", f"{end-start:.3f}", "-i", str(source), "-an", "-vf", "scale='min(720,iw)':-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-movflags", "+faststart", str(output)])


def render_video_preview(root: Path, video: dict[str, Any], inventory: list[dict[str, Any]], packages: list[dict[str, Any]]) -> None:
    sections: list[str] = []
    package_map = {row["action"]: row for row in packages}
    for unit in inventory:
        for technique in unit["techniques"]:
            package = package_map.get(technique["action"])
            if not package:
                continue
            episodes: list[str] = []
            for episode in package["episodes"]:
                cards = "".join(f'<figure><img src="{html.escape(frame["image"])}"><figcaption><b>{frame["frame_index"]:02d} · {html.escape(frame["label_zh"])}</b><p>{html.escape(frame["teaching_point_zh"])}</p><small>{html.escape(frame["evidence_boundary_zh"])}</small></figcaption></figure>' for frame in episode["frames"])
                episodes.append(f'<article><h3>{html.escape(episode["episode_id"])}</h3><p>动作 {episode["action_start_seconds"]:.3f}–{episode["action_end_seconds"]:.3f}s；播放 {episode["clip_start_seconds"]:.3f}–{episode["clip_end_seconds"]:.3f}s</p><video controls preload="metadata" src="{html.escape(episode["clip"])}"></video><div class="grid">{cards}</div></article>')
            sections.append(f'<section><h2>{html.escape(package["label_zh"])} · {html.escape(package["action"])}</h2><p>{html.escape(package["teaching_summary_zh"])}</p>{"".join(episodes) or "<p>no_reliable_action_episode</p>"}</section>')
    document = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(video["title"])}</title><style>body{{font:15px/1.55 system-ui;max-width:1500px;margin:24px auto;padding:0 16px;background:#07111f;color:#edf5ff}}section,article{{background:#102038;border:1px solid #29405d;border-radius:14px;padding:18px;margin:18px 0}}video{{display:block;width:min(420px,100%);max-height:650px;margin:12px auto;background:#000}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}figure{{margin:0;background:#091625;border-radius:10px;overflow:hidden}}img{{width:100%;aspect-ratio:9/16;object-fit:cover}}figcaption{{padding:10px}}small{{color:#9bb0c8}}</style></head><body><h1>{html.escape(video["title"])}</h1><p>{html.escape(video["source_id"])}</p>{"".join(sections)}</body></html>'''
    (root / "preview.html").write_text(document, encoding="utf-8")


def command_materialize(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = selected_rows(manifest, args)
    for video in rows:
        root = video_root(args.batch_root, video)
        candidates_path, results_path = root / "candidates.json", root / "gate-results.jsonl"
        if not candidates_path.is_file() or not results_path.is_file():
            continue
        try:
            document = json.loads(candidates_path.read_text(encoding="utf-8"))
            candidates = {row["candidate_id"]: row for row in document["candidates"]}
            results = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            grouped: dict[str, list[dict[str, Any]]] = {}
            for result in results:
                candidate = candidates[result["candidate_id"]]
                payload = (
                    normalize_gate_consistency(dict(result["payload"]))
                    if result.get("payload")
                    else None
                )
                if not materializable(
                    candidate, payload, args.include_review_candidates
                ):
                    continue
                start, end = action_interval(candidate, payload)
                if end - start < 0.65:
                    continue
                for technique in candidate.get("techniques") or [candidate]:
                    grouped.setdefault(technique["action"], []).append({
                        "candidate": candidate,
                        "technique": technique,
                        "payload": payload,
                        "action_start_seconds": start,
                        "action_end_seconds": end,
                        "action_duration_seconds": round(end - start, 4),
                        "score": episode_score(candidate, payload),
                    })
            selected: list[dict[str, Any]] = []
            for action, episodes in grouped.items():
                kept: list[dict[str, Any]] = []
                for episode in sorted(episodes, key=lambda row: row["score"], reverse=True):
                    interval = (episode["action_start_seconds"], episode["action_end_seconds"])
                    if any(overlap(interval, (other["action_start_seconds"], other["action_end_seconds"])) / min(interval[1]-interval[0], other["action_end_seconds"]-other["action_start_seconds"]) > 0.45 for other in kept):
                        continue
                    kept.append(episode)
                    if len(kept) >= args.max_episodes_per_technique:
                        break
                selected.extend(kept)
            ordered = sorted(selected, key=lambda row: row["action_start_seconds"])
            source_record_path = root / "source.json"
            source_record = (
                json.loads(source_record_path.read_text(encoding="utf-8"))
                if source_record_path.is_file()
                else {}
            )
            prepared_duration = float(
                source_record.get("duration_seconds", video["duration_seconds"])
            )
            for index, episode in enumerate(ordered):
                next_start = next((later["action_start_seconds"] for later in ordered[index+1:] if later["action_start_seconds"] > episode["action_end_seconds"]), None)
                latest = prepared_duration if next_start is None else max(episode["action_end_seconds"], next_start - 0.25)
                episode["clip_start_seconds"] = episode["action_start_seconds"]
                episode["clip_end_seconds"] = round(min(episode["action_end_seconds"] + args.post_roll_seconds, latest), 4)
                episode["clip_duration_seconds"] = round(episode["clip_end_seconds"] - episode["clip_start_seconds"], 4)
            source_cache = args.source_cache or args.batch_root / "sources"
            source = Path(str(source_record.get("path") or source_cache / f"{video['job_id']}.mp4"))
            if not source.is_file() or source.stat().st_size <= 0:
                raise RuntimeError(f"prepared_source_missing:{source}")
            packages: list[dict[str, Any]] = []
            route_by_action: dict[str, dict[str, Any]] = {}
            for unit in document["semantic_inventory"]:
                for route in unit["techniques"]:
                    route_by_action.setdefault(route["action"], route)
            for action, route in route_by_action.items():
                action_episodes = [
                    row for row in ordered if row["technique"]["action"] == action
                ]
                package = {"action": action, "label_zh": route["label_zh"], "family_id": route["family_id"], "taxonomy_path": route["taxonomy_path"], "semantic_review_status": "model_candidate", "teaching_summary_zh": f"按公开视频标题、私有 ASR 内存路由和可见动作门控整理的{route['label_zh']}教学候选；进入正式 Skill 前必须人工复核。", "episodes": []}
                for episode_index, episode in enumerate(action_episodes, start=1):
                    episode_id = f"{action}-episode-{episode_index:02d}"
                    episode_root = root / "episodes" / "_shared" / episode["candidate"]["candidate_id"]
                    clip = episode_root / "action.mp4"
                    extract_clip(source, args.ffmpeg, episode["clip_start_seconds"], episode["clip_end_seconds"], clip)
                    timestamps = sample_timestamps(episode["action_start_seconds"], episode["action_end_seconds"], len(PHASES))
                    frames: list[dict[str, Any]] = []
                    stage_frame_paths: list[Path] = []
                    step = (timestamps[-1] - timestamps[0]) / max(1, len(timestamps)-1)
                    for frame_index, ((stage_id, phase, label), timestamp) in enumerate(zip(PHASES, timestamps), start=1):
                        frame = episode_root / "frames" / f"stage-{frame_index:02d}-{stage_id}.jpg"
                        extract_frame(source, args.ffmpeg, timestamp, frame)
                        stage_frame_paths.append(frame)
                        frames.append({"frame_index": frame_index, "stage_id": stage_id, "phase": phase, "label_zh": label, "start_seconds": round(max(episode["action_start_seconds"], timestamp-step*0.45),4), "anchor_seconds": round(timestamp,4), "end_seconds": round(min(episode["action_end_seconds"], timestamp+step*0.45),4), "image": str(frame.relative_to(root)), "teaching_point_zh": stage_tip(route["family_id"], stage_id), "evidence_boundary_zh": "仅描述普通单目视频中这一时刻可见的二维姿态和动作路线；不能确认精确触球、拍面角度、真实内旋、握拍压力、力量大小或三维运动学。"})
                    contact_sheet(
                        stage_frame_paths,
                        timestamps,
                        episode_root / "stage-sheet.jpg",
                    )
                    candidate_actions = [
                        row["action"]
                        for row in episode["candidate"].get("techniques")
                        or [episode["technique"]]
                    ]
                    package["episodes"].append({
                        "episode_id": episode_id,
                        "candidate_id": episode["candidate"]["candidate_id"],
                        "candidate_actions": candidate_actions,
                        "semantic_assignment_status": (
                            "resolved"
                            if len(candidate_actions) == 1
                            else "agent_review_required"
                        ),
                        "classification": episode["payload"]["classification"],
                        "confidence": episode["payload"]["confidence"],
                        "demonstration_purity": episode["payload"]["demonstration_purity"],
                        "semantic_compatibility": episode["payload"]["semantic_compatibility"],
                        "action_repetitions": episode["payload"]["action_repetitions"],
                        "visible_stage_coverage": episode["payload"]["visible_stage_coverage"],
                        "score": episode["score"],
                        "action_start_seconds": episode["action_start_seconds"],
                        "action_end_seconds": episode["action_end_seconds"],
                        "action_duration_seconds": episode["action_duration_seconds"],
                        "clip_start_seconds": episode["clip_start_seconds"],
                        "clip_end_seconds": episode["clip_end_seconds"],
                        "clip_duration_seconds": episode["clip_duration_seconds"],
                        "clip": str(clip.relative_to(root)),
                        "frames": frames,
                        "review_status": (
                            "model_candidate"
                            if admitted(episode["candidate"], episode["payload"])
                            else "required_human_review"
                        ),
                        "automatic_admission": admitted(
                            episode["candidate"], episode["payload"]
                        ),
                        "scope_limitations": episode["payload"]["scope_limitations"],
                    })
                packages.append(package)
            lesson = {"artifact_version": 2, "video": video, "semantic_inventory": document["semantic_inventory"], "techniques": packages, "scope_boundary_zh": "普通单目视频只能支持可见二维动作路线；证据不足时返回不知道或建议补充示范。"}
            atomic_json(root / "lesson-package.json", lesson)
            render_video_preview(root, video, document["semantic_inventory"], packages)
            set_status(root, "materialize", "succeeded", technique_count=len(packages), episode_count=sum(len(row["episodes"]) for row in packages))
            print("MATERIALIZE_DONE", video["job_id"], len(packages), sum(len(row["episodes"]) for row in packages), flush=True)
        except Exception as error:
            set_status(root, "materialize", "failed", error=f"{type(error).__name__}:{error}")
            print("MATERIALIZE_FAILED", video["job_id"], repr(error), flush=True)


def command_summarize(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    videos: list[dict[str, Any]] = []
    queue: list[dict[str, Any]] = []
    high_by_family: dict[str, list[dict[str, Any]]] = {}
    queued_candidates: set[str] = set()
    for video in manifest["videos"]:
        root = video_root(args.batch_root, video)
        status = json.loads((root / "status.json").read_text(encoding="utf-8")) if (root / "status.json").is_file() else {"state": "pending", "stage": "inventory"}
        record = {"video_index": video["video_index"], "job_id": video["job_id"], "source_id": video["source_id"], "title": video["title"], "state": status.get("state"), "stage": status.get("stage"), "preview": str((root / "preview.html").relative_to(args.batch_root)) if (root / "preview.html").is_file() else "", "technique_count": 0, "episode_count": 0}
        lesson_path = root / "lesson-package.json"
        if lesson_path.is_file():
            lesson = json.loads(lesson_path.read_text(encoding="utf-8"))
            record["technique_count"] = len(lesson["techniques"])
            record["episode_count"] = sum(len(row["episodes"]) for row in lesson["techniques"])
            for technique in lesson["techniques"]:
                if not technique["episodes"]:
                    queue.append({"review_key": f"{video['job_id']}:{technique['action']}:semantic-gap", "job_id": video["job_id"], "source_id": video["source_id"], "action": technique["action"], "family_id": technique["family_id"], "reason": "no_reliable_action_episode", "tier": "required", "decision": "pending"})
                for episode in technique["episodes"]:
                    candidate_key = f"{video['job_id']}:{episode['candidate_id']}"
                    candidate_actions = episode.get("candidate_actions") or [
                        technique["action"]
                    ]
                    if len(candidate_actions) > 1:
                        if candidate_key not in queued_candidates:
                            queue.append(
                                {
                                    "review_key": candidate_key,
                                    "job_id": video["job_id"],
                                    "source_id": video["source_id"],
                                    "action": "",
                                    "allowed_actions": candidate_actions,
                                    "candidate_id": episode["candidate_id"],
                                    "preview": record["preview"],
                                    "reason": "semantic_action_ambiguous",
                                    "tier": "required",
                                    "decision": "pending",
                                }
                            )
                            queued_candidates.add(candidate_key)
                        continue
                    item = {"review_key": f"{video['job_id']}:{technique['action']}:{episode['episode_id']}", "job_id": video["job_id"], "source_id": video["source_id"], "action": technique["action"], "family_id": technique["family_id"], "episode_id": episode["episode_id"], "candidate_id": episode["candidate_id"], "preview": record["preview"], "reason": "high_confidence_sample_pool", "tier": "sample_pool", "decision": "pending"}
                    high = (
                        episode["classification"] == "continuous_demonstration"
                        and episode["confidence"] == "high"
                        and episode["demonstration_purity"] == "high"
                        and episode["semantic_compatibility"] == "yes"
                        and episode.get("action_repetitions") == 1
                        and len(episode.get("visible_stage_coverage", [])) >= 4
                        and not {"no_full_action", "incomplete_sequence"}.intersection(
                            episode.get("scope_limitations", [])
                        )
                    )
                    if high:
                        high_by_family.setdefault(technique["family_id"], []).append(item)
                    else:
                        item["reason"], item["tier"] = "ambiguous_or_partial_episode", "required"
                        queue.append(item)
        videos.append(record)
    for family, items in high_by_family.items():
        ordered = sorted(items, key=lambda row: hashlib.sha256(row["review_key"].encode()).hexdigest())
        sample_count = min(len(ordered), max(10, math.ceil(len(ordered) * args.high_confidence_sample_rate)))
        for index, item in enumerate(ordered):
            if index < sample_count:
                item["tier"], item["reason"] = "required", "stratified_high_confidence_sample"
            queue.append(item)
    summary = {"status": "complete" if all(row["state"] == "succeeded" for row in videos) else "incomplete", "video_count": len(videos), "succeeded_video_count": sum(row["state"] == "succeeded" for row in videos), "failed_video_count": sum(row["state"] == "failed" for row in videos), "technique_count": sum(row["technique_count"] for row in videos), "episode_count": sum(row["episode_count"] for row in videos), "required_review_count": sum(row["tier"] == "required" for row in queue), "sample_pool_count": sum(row["tier"] == "sample_pool" for row in queue), "videos": videos}
    atomic_json(args.batch_root / "summary.json", summary)
    with (args.batch_root / "review-queue.jsonl").open("w", encoding="utf-8") as handle:
        for item in queue:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    card_rows: list[str] = []
    for row in videos:
        link = (
            f'<a href="{html.escape(row["preview"])}">打开预览</a>'
            if row["preview"]
            else "<span>无预览</span>"
        )
        card_rows.append(
            f'<article><h2>{row["video_index"]:03d} · {html.escape(row["title"])}</h2>'
            f'<p>{html.escape(row["source_id"])} · {row["state"]}/{row["stage"]} · '
            f'技术 {row["technique_count"]} · 动作 {row["episode_count"]}</p>{link}</article>'
        )
    cards = "".join(card_rows)
    page = f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>408 视频解析总览</title><style>body{{font:15px/1.5 system-ui;max-width:1200px;margin:24px auto;background:#f3f5f8}}header,article{{background:white;padding:16px;margin:12px;border-radius:12px;border:1px solid #d8dde6}}h2{{font-size:18px}}</style></head><body><header><h1>教练视频全量解析</h1><p>成功 {summary["succeeded_video_count"]}/{summary["video_count"]}；技术 {summary["technique_count"]}；动作片段 {summary["episode_count"]}；必审 {summary["required_review_count"]}</p></header>{cards}</body></html>'
    (args.batch_root / "preview.html").write_text(page, encoding="utf-8")
    print("SUMMARY", json.dumps({key: summary[key] for key in ("status", "video_count", "succeeded_video_count", "failed_video_count", "technique_count", "episode_count", "required_review_count")}, ensure_ascii=False))


def command_publish(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    video_map = {row["job_id"]: row for row in manifest["videos"]}
    decisions = [json.loads(line) for line in args.decisions.read_text(encoding="utf-8").splitlines() if line.strip()]
    approved = [
        row
        for row in decisions
        if row.get("decision") == "approve"
        and row.get("action")
        and (row.get("episode_id") or row.get("candidate_id"))
    ]
    families: dict[str, list[dict[str, Any]]] = {}
    index: list[dict[str, Any]] = []
    for decision in approved:
        video = video_map[decision["job_id"]]
        lesson = json.loads((video_root(args.batch_root, video) / "lesson-package.json").read_text(encoding="utf-8"))
        technique = next(row for row in lesson["techniques"] if row["action"] == decision["action"])
        episode = next(
            row
            for row in technique["episodes"]
            if (
                row["episode_id"] == decision.get("episode_id")
                if decision.get("episode_id")
                else row["candidate_id"] == decision["candidate_id"]
            )
        )
        lesson_id = f"{video['job_id']}-{technique['action']}-{episode['candidate_id']}"
        complete = (
            episode["classification"] == "continuous_demonstration"
            and episode.get("action_repetitions") == 1
            and len(episode.get("visible_stage_coverage", [])) >= 4
            and not {"no_full_action", "incomplete_sequence"}.intersection(
                episode.get("scope_limitations", [])
            )
        )
        row = {"lesson_id": lesson_id, "source_id": video["source_id"], "lesson_topic": technique["label_zh"], "action": technique["action"], "family_id": technique["family_id"], "taxonomy_path": technique["taxonomy_path"], "semantic_review_status": "agent_reviewed", "completeness": "complete_demonstration" if complete else "partial_demonstration", "review_status": "agent_reviewed", "confidence": episode["confidence"], "teaching_summary": f"人工复核的完整{technique['label_zh']}连续示范；教学仅依据可见的二维动作路线。", "episode": {"start_seconds": episode["action_start_seconds"], "end_seconds": episode["action_end_seconds"], "clip_start_seconds": episode["clip_start_seconds"], "clip_end_seconds": episode["clip_end_seconds"]}, "stages": [{"stage_id": frame["stage_id"], "label": frame["label_zh"], "phase": frame["phase"], "start_seconds": frame["start_seconds"], "anchor_seconds": frame["anchor_seconds"], "end_seconds": frame["end_seconds"], "confidence": episode["confidence"], "teaching_use": frame["teaching_point_zh"], "teaching_points": [frame["teaching_point_zh"]], "visible_facts": ["ordered_public_coach_action_stage_visible"], "limitations": ["ordinary_monocular_video_visibility_boundary"]} for frame in episode["frames"]], "limitations": ["ordinary_monocular_video_does_not_prove_contact_racket_face_force_or_3d_kinematics"]}
        families.setdefault(technique["family_id"], []).append(row)
        index.append({"lesson_id": lesson_id, "source_id": video["source_id"], "action": technique["action"], "family_id": technique["family_id"], "shard": f"video-lessons/{technique['family_id']}.yaml"})
    args.output.mkdir(parents=True, exist_ok=True)
    shard_root = args.output / "video-lessons"
    shard_root.mkdir(exist_ok=True)
    for family, lessons in families.items():
        (shard_root / f"{family}.yaml").write_text(yaml.safe_dump({"version": 1, "lessons": lessons}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (args.output / "video-lessons-index.yaml").write_text(yaml.safe_dump({"version": 1, "lesson_count": len(index), "lessons": index}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("PUBLISH_STAGED", len(index), args.output)


def parser() -> argparse.ArgumentParser:
    main = argparse.ArgumentParser()
    commands = main.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser("inventory")
    inventory.add_argument("--asr-review", type=Path, required=True)
    inventory.add_argument("--source-index", type=Path, required=True)
    inventory.add_argument("--raw-root", type=Path, required=True)
    inventory.add_argument("--output", type=Path, required=True)
    inventory.add_argument("--expected-count", type=int, default=408)
    inventory.set_defaults(func=command_inventory)

    def batch_arguments(command: argparse.ArgumentParser) -> None:
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--batch-root", type=Path, required=True)
        command.add_argument("--start", type=int, default=0)
        command.add_argument("--stop", type=int)
        command.add_argument("--shard", type=int, default=0)
        command.add_argument("--shards", type=int, default=1)
        command.add_argument(
            "--job-id",
            action="append",
            help="process only this manifest job ID; may be repeated",
        )

    prepare = commands.add_parser("prepare")
    batch_arguments(prepare)
    prepare.add_argument("--routing", type=Path, required=True)
    prepare.add_argument("--raw-root", type=Path, required=True)
    prepare.add_argument("--yt-dlp", type=Path, required=True)
    prepare.add_argument("--ffmpeg", type=Path, required=True)
    prepare.add_argument("--source-cache", type=Path)
    prepare.add_argument(
        "--temporal-pose-root",
        type=Path,
        help="optional restored dense-pose artifacts used only to seed wider action candidates",
    )
    prepare.add_argument(
        "--temporal-pose-only",
        action="store_true",
        help="use restored dense-pose candidate seeds only; requires --temporal-pose-root",
    )
    prepare.add_argument("--motion-scan-fps", type=float, default=4.0)
    prepare.add_argument("--focus-seconds", type=float, default=5.0)
    prepare.add_argument("--candidates-per-unit", type=int, default=2)
    prepare.add_argument("--max-candidates-per-video", type=int, default=24)
    prepare.add_argument("--frames-per-candidate", type=int, default=10)
    prepare.add_argument("--force", action="store_true")
    prepare.set_defaults(func=command_prepare)

    gate = commands.add_parser("gate")
    batch_arguments(gate)
    gate.add_argument("--model", type=Path, required=True)
    gate.add_argument("--max-new-tokens", type=int, default=384)
    gate.set_defaults(func=command_gate)

    materialize = commands.add_parser("materialize")
    batch_arguments(materialize)
    materialize.add_argument("--ffmpeg", type=Path, required=True)
    materialize.add_argument("--source-cache", type=Path)
    materialize.add_argument("--max-episodes-per-technique", type=int, default=8)
    materialize.add_argument("--post-roll-seconds", type=float, default=1.5)
    materialize.add_argument(
        "--include-review-candidates",
        action="store_true",
        help="materialize strong partial demonstrations for human review; never auto-publishes them",
    )
    materialize.set_defaults(func=command_materialize)

    summarize = commands.add_parser("summarize")
    summarize.add_argument("--manifest", type=Path, required=True)
    summarize.add_argument("--batch-root", type=Path, required=True)
    summarize.add_argument("--high-confidence-sample-rate", type=float, default=0.2)
    summarize.set_defaults(func=command_summarize)

    publish = commands.add_parser("publish")
    publish.add_argument("--manifest", type=Path, required=True)
    publish.add_argument("--batch-root", type=Path, required=True)
    publish.add_argument("--decisions", type=Path, required=True)
    publish.add_argument("--output", type=Path, required=True)
    publish.set_defaults(func=command_publish)
    return main


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
