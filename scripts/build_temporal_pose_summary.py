from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reduce private dense Pose coordinates to public-safe temporal geometry proxies."
    )
    parser.add_argument(
        "--manifest", default="data/corpus/video-temporal-review-manifest.yaml"
    )
    parser.add_argument(
        "--output", default="data/corpus/video-temporal-pose-summary.yaml"
    )
    return parser.parse_args()


def point(person: dict[str, Any], index: int, threshold: float = 0.25) -> tuple[float, float] | None:
    points = person.get("keypoints_xy", [])
    confidence = person.get("keypoint_confidence", [])
    if index >= len(points) or index >= len(confidence):
        return None
    if float(confidence[index]) < threshold:
        return None
    raw = points[index]
    if not isinstance(raw, list) or len(raw) != 2:
        return None
    return float(raw[0]), float(raw[1])


def midpoint(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def line_angle(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def normalize_axial_angle(angle: float) -> float:
    """Map an undirected line angle to [-90, 90) to remove 180-degree wrap."""
    return round(((float(angle) + 90.0) % 180.0) - 90.0, 2)


def joint_angle(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> float | None:
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    denominator = math.hypot(*ba) * math.hypot(*bc)
    if denominator == 0:
        return None
    cosine = max(-1.0, min(1.0, (ba[0] * bc[0] + ba[1] * bc[1]) / denominator))
    return math.degrees(math.acos(cosine))


def frame_geometry(person: dict[str, Any]) -> dict[str, Any]:
    left_shoulder, right_shoulder = point(person, 5), point(person, 6)
    left_elbow, right_elbow = point(person, 7), point(person, 8)
    left_wrist, right_wrist = point(person, 9), point(person, 10)
    left_hip, right_hip = point(person, 11), point(person, 12)
    left_knee, right_knee = point(person, 13), point(person, 14)
    left_ankle, right_ankle = point(person, 15), point(person, 16)
    result: dict[str, Any] = {
        "mean_keypoint_confidence": person.get("mean_confidence"),
        "visible_keypoint_count": sum(
            float(value) >= 0.25 for value in person.get("keypoint_confidence", [])
        ),
    }
    bbox = person.get("bbox_xyxy") or [0, 0, 0, 0]
    bbox_width = (
        max(float(bbox[2]) - float(bbox[0]), 0.0)
        if isinstance(bbox, list) and len(bbox) >= 4
        else 0.0
    )
    shoulder_width = None
    if left_shoulder and right_shoulder:
        shoulder_width = distance(left_shoulder, right_shoulder)
        result["shoulder_angle_deg"] = normalize_axial_angle(
            line_angle(left_shoulder, right_shoulder)
        )
    if left_hip and right_hip:
        result["hip_angle_deg"] = normalize_axial_angle(
            line_angle(left_hip, right_hip)
        )
    if left_shoulder and right_shoulder and left_hip and right_hip:
        shoulder_mid = midpoint(left_shoulder, right_shoulder)
        hip_mid = midpoint(left_hip, right_hip)
        result["trunk_lean_deg"] = round(
            math.degrees(
                math.atan2(shoulder_mid[0] - hip_mid[0], hip_mid[1] - shoulder_mid[1])
            ),
            2,
        )
    if left_shoulder and left_elbow:
        result["left_elbow_above_shoulder"] = left_elbow[1] < left_shoulder[1]
    if right_shoulder and right_elbow:
        result["right_elbow_above_shoulder"] = right_elbow[1] < right_shoulder[1]
    if left_shoulder and left_elbow and left_wrist:
        angle = joint_angle(left_shoulder, left_elbow, left_wrist)
        if angle is not None:
            result["left_elbow_angle_deg"] = round(angle, 2)
    if right_shoulder and right_elbow and right_wrist:
        angle = joint_angle(right_shoulder, right_elbow, right_wrist)
        if angle is not None:
            result["right_elbow_angle_deg"] = round(angle, 2)
    if left_hip and left_knee and left_ankle:
        angle = joint_angle(left_hip, left_knee, left_ankle)
        if angle is not None:
            result["left_knee_angle_deg"] = round(angle, 2)
    if right_hip and right_knee and right_ankle:
        angle = joint_angle(right_hip, right_knee, right_ankle)
        if angle is not None:
            result["right_knee_angle_deg"] = round(angle, 2)
    shoulder_scale_valid = shoulder_width and shoulder_width >= max(8.0, bbox_width * 0.08)
    if shoulder_scale_valid and left_ankle and right_ankle:
        stance_ratio = abs(right_ankle[0] - left_ankle[0]) / shoulder_width
        if stance_ratio <= 5.0:
            result["stance_width_shoulder_ratio"] = round(stance_ratio, 2)
    return result


def primary_person(frame: dict[str, Any]) -> dict[str, Any] | None:
    people = frame.get("people", [])
    if not people:
        return None
    def score(person: dict[str, Any]) -> float:
        box = person.get("bbox_xyxy") or [0, 0, 0, 0]
        area = max(float(box[2]) - float(box[0]), 0.0) * max(
            float(box[3]) - float(box[1]), 0.0
        )
        return area * max(float(person.get("mean_confidence") or 0), 0.05)
    return max(
        people,
        key=score,
    )


def metric_summary(
    geometries: list[dict[str, Any]], field: str
) -> dict[str, float | int] | None:
    values = [float(item[field]) for item in geometries if item.get(field) is not None]
    if not values:
        return None
    if len(values) >= 2:
        deciles = statistics.quantiles(values, n=10, method="inclusive")
        p10, p90 = deciles[0], deciles[-1]
    else:
        p10 = p90 = values[0]
    return {
        "observed_min": round(min(values), 2),
        "observed_max": round(max(values), 2),
        "p10": round(p10, 2),
        "p90": round(p90, 2),
        "robust_range": round(p90 - p10, 2),
        "median": round(float(statistics.median(values)), 2),
        "sample_count": len(values),
    }


def load_pose(job: dict[str, Any]) -> dict[str, Any] | None:
    path = ROOT / job["private_paths"]["pose_json"]
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if data.get("status") != "ok" or data.get("artifact_version") != 2:
        return None
    return data


def summarize_sequence(
    sequence: dict[str, Any], pose_frames: dict[float, dict[str, Any]]
) -> dict[str, Any]:
    timestamps = [float(item["timestamp_seconds"]) for item in sequence["planned_frames"]]
    geometries: list[dict[str, Any]] = []
    frames_with_person = 0
    for timestamp in timestamps:
        frame = pose_frames.get(round(timestamp, 3))
        if not frame:
            continue
        person = primary_person(frame)
        if not person:
            continue
        frames_with_person += 1
        geometry = frame_geometry(person)
        geometry["timestamp_seconds"] = timestamp
        geometries.append(geometry)
    metrics = {}
    for field in [
        "shoulder_angle_deg",
        "hip_angle_deg",
        "trunk_lean_deg",
        "left_elbow_angle_deg",
        "right_elbow_angle_deg",
        "left_knee_angle_deg",
        "right_knee_angle_deg",
        "stance_width_shoulder_ratio",
    ]:
        summary = metric_summary(geometries, field)
        if summary:
            metrics[field] = summary
    return {
        "sequence_id": sequence["sequence_id"],
        "source_window_id": sequence["source_window_id"],
        "anchor_timestamp_seconds": sequence["anchor_timestamp_seconds"],
        "start_seconds": min(timestamps),
        "end_seconds": max(timestamps),
        "topic_tags": sequence.get("topic_tags", []),
        "planned_frame_count": len(timestamps),
        "frames_with_primary_person": frames_with_person,
        "geometry_valid_frame_count": len(geometries),
        "left_elbow_above_shoulder_frames": sum(
            item.get("left_elbow_above_shoulder") is True for item in geometries
        ),
        "right_elbow_above_shoulder_frames": sum(
            item.get("right_elbow_above_shoulder") is True for item in geometries
        ),
        "metric_ranges": metrics,
        "evidence_level": "temporal_pose_proxy_public_safe",
        "allowed_use": [
            "Coarse body-geometry change and visibility checks across a dense monocular sequence.",
            "Timestamp routing for later human video review.",
        ],
        "blocked_use": [
            "No racket-face, shuttle-contact, grip-pressure, force, or true internal-rotation claim.",
            "Do not assign the left or right elbow to the racket arm without visual confirmation.",
            "Do not treat 2D angle changes as calibrated 3D joint kinematics.",
        ],
    }


def main() -> None:
    args = parse_args()
    manifest = load_yaml(ROOT / args.manifest)
    sources: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    for job in manifest.get("jobs", []):
        pose = load_pose(job)
        if not pose:
            status_counts["pose_missing_or_incomplete"] += 1
            continue
        pose_frames = {
            round(float(frame["timestamp_seconds"]), 3): frame
            for frame in pose.get("frames", [])
        }
        sequences = [
            summarize_sequence(sequence, pose_frames)
            for sequence in job.get("temporal_sequences", [])
        ]
        complete = all(
            item["frames_with_primary_person"] > 0 for item in sequences
        ) and bool(sequences)
        status_counts["complete" if complete else "insufficient_pose_visibility"] += 1
        sources.append(
            {
                "job_id": job["job_id"],
                "source_id": job["source_id"],
                "title": job["title"],
                "platform": job["platform"],
                "complete": complete,
                "sequences": sequences,
            }
        )
    output = {
        "temporal_pose_summary_run": {
            "run_id": f"temporal_pose_summary_{date.today().strftime('%Y%m%d')}",
            "created_at": date.today().isoformat(),
            "manifest": args.manifest,
            "summary": {
                "manifest_sources": len(manifest.get("jobs", [])),
                "sources_with_pose_artifacts": len(sources),
                "status_counts": dict(status_counts),
                "sequence_count": sum(len(item["sequences"]) for item in sources),
            },
            "publication_safety": {
                "raw_keypoints_published": False,
                "raw_frames_published": False,
                "raw_video_published": False,
            },
        },
        "sources": sources,
    }
    write_yaml(ROOT / args.output, output)
    print(f"wrote {args.output}")
    print(f"sources_with_pose_artifacts {len(sources)}")
    print(f"sequence_count {sum(len(item['sequences']) for item in sources)}")


if __name__ == "__main__":
    main()
