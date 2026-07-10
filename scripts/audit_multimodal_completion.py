from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit every completion gate for the full Liu Hui multimodal Skill build."
    )
    parser.add_argument(
        "--visual-manifest", default="data/corpus/video-visual-pipeline-manifest.yaml"
    )
    parser.add_argument(
        "--visual-review", default="data/corpus/video-visual-review-manifest.yaml"
    )
    parser.add_argument(
        "--temporal-manifest", default="data/corpus/video-temporal-review-manifest.yaml"
    )
    parser.add_argument(
        "--temporal-summary", default="data/corpus/video-temporal-pose-summary.yaml"
    )
    parser.add_argument(
        "--evidence-map",
        default="skills/liu-hui-badminton-coach/references/multimodal-evidence-map.yaml",
    )
    parser.add_argument(
        "--output", default="data/corpus/multimodal-completion-status.yaml"
    )
    parser.add_argument("--no-fail", action="store_true")
    return parser.parse_args()


def rounded_timestamps(values: list[Any]) -> list[float | int]:
    output: list[float | int] = []
    for value in values:
        rounded = round(float(value), 3)
        output.append(int(rounded) if rounded.is_integer() else rounded)
    return output


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def validate_keyframe_artifact(
    data: dict[str, Any] | None, expected_timestamps: list[Any]
) -> list[str]:
    if not data:
        return ["artifact_missing_or_unreadable"]
    errors: list[str] = []
    expected = rounded_timestamps(expected_timestamps)
    frames = data.get("frames", [])
    if data.get("status") != "ok":
        errors.append(f"status_{data.get('status', 'missing')}")
    if int(data.get("frame_count") or 0) != len(expected):
        errors.append("frame_count_mismatch")
    actual = rounded_timestamps(
        [frame.get("timestamp_seconds") for frame in frames]
    ) if isinstance(frames, list) else []
    if actual != expected:
        errors.append("timestamps_mismatch")
    return errors


def validate_vlm_artifact(
    data: dict[str, Any] | None, expected_timestamps: list[Any]
) -> list[str]:
    if not data:
        return ["artifact_missing_or_unreadable"]
    errors: list[str] = []
    expected = rounded_timestamps(expected_timestamps)
    frames = data.get("frames", [])
    if data.get("status") != "ok":
        errors.append(f"status_{data.get('status', 'missing')}")
    if data.get("artifact_version") != 4:
        errors.append("artifact_version_mismatch")
    if data.get("schema") != "visible_still_frame_v2":
        errors.append("schema_mismatch")
    if int(data.get("frame_count") or 0) != len(expected):
        errors.append("frame_count_mismatch")
    if not isinstance(frames, list) or len(frames) != len(expected):
        errors.append("frames_length_mismatch")
        return errors
    actual = rounded_timestamps([frame.get("timestamp_seconds") for frame in frames])
    if actual != expected:
        errors.append("timestamps_mismatch")
    if [frame.get("image_index") for frame in frames] != list(range(1, len(frames) + 1)):
        errors.append("image_index_mismatch")
    return errors


def validate_pose_artifact(
    data: dict[str, Any] | None, expected_timestamps: list[Any]
) -> list[str]:
    if not data:
        return ["artifact_missing_or_unreadable"]
    errors: list[str] = []
    expected = rounded_timestamps(expected_timestamps)
    frames = data.get("frames", [])
    if data.get("status") != "ok":
        errors.append(f"status_{data.get('status', 'missing')}")
    if data.get("artifact_version") != 2:
        errors.append("artifact_version_mismatch")
    if int(data.get("frame_count") or 0) != len(expected):
        errors.append("frame_count_mismatch")
    if not isinstance(frames, list) or len(frames) != len(expected):
        errors.append("frames_length_mismatch")
        return errors
    actual = rounded_timestamps([frame.get("timestamp_seconds") for frame in frames])
    if actual != expected:
        errors.append("timestamps_mismatch")
    return errors


def artifact_paths(job: dict[str, Any]) -> tuple[Path, Path, Path]:
    private = job["private_paths"]
    return (
        ROOT / private["keyframes_dir"] / "manifest.json",
        ROOT / private["vlm_json"],
        ROOT / private["pose_json"],
    )


def audit_visual(manifest: dict[str, Any]) -> dict[str, Any]:
    jobs = manifest.get("jobs", [])
    summary = manifest.get("summary", {})
    issues: list[dict[str, Any]] = []
    complete = 0
    planned_frames = 0
    for job in jobs:
        expected = [frame["timestamp_seconds"] for frame in job.get("planned_frames", [])]
        planned_frames += len(expected)
        keyframe_path, vlm_path, pose_path = artifact_paths(job)
        errors = {
            "keyframes": validate_keyframe_artifact(read_json(keyframe_path), expected),
            "vlm": validate_vlm_artifact(read_json(vlm_path), expected),
            "pose": validate_pose_artifact(read_json(pose_path), expected),
        }
        errors = {stage: values for stage, values in errors.items() if values}
        if errors:
            issues.append({"job_id": job["job_id"], "errors": errors})
        else:
            complete += 1
    declared_review_jobs = int(summary.get("review_jobs") or 0)
    declared_pipeline_jobs = int(summary.get("pipeline_jobs") or 0)
    declared_planned_frames = int(summary.get("planned_frames") or 0)
    shape_matches = (
        declared_review_jobs == len(jobs)
        and declared_pipeline_jobs == len(jobs)
        and declared_planned_frames == planned_frames
        and int(summary.get("missing_source_jobs") or 0) == 0
    )
    return {
        "passed": bool(jobs) and shape_matches and complete == len(jobs),
        "total_jobs": len(jobs),
        "planned_frames": planned_frames,
        "declared_review_jobs": declared_review_jobs,
        "declared_pipeline_jobs": declared_pipeline_jobs,
        "declared_planned_frames": declared_planned_frames,
        "manifest_shape_matches": shape_matches,
        "complete_jobs": complete,
        "incomplete_jobs": len(issues),
        "issues": issues[:100],
    }


def audit_temporal(
    manifest: dict[str, Any], summary: dict[str, Any] | None
) -> dict[str, Any]:
    jobs = manifest.get("jobs", [])
    manifest_summary = manifest.get("summary", {})
    issues: list[dict[str, Any]] = []
    complete_artifacts = 0
    planned_frames = sum(len(job.get("planned_frames", [])) for job in jobs)
    planned_sequences = sum(len(job.get("temporal_sequences", [])) for job in jobs)
    for job in jobs:
        expected = [frame["timestamp_seconds"] for frame in job.get("planned_frames", [])]
        keyframe_path, _, pose_path = artifact_paths(job)
        errors = {
            "keyframes": validate_keyframe_artifact(read_json(keyframe_path), expected),
            "pose": validate_pose_artifact(read_json(pose_path), expected),
        }
        errors = {stage: values for stage, values in errors.items() if values}
        if errors:
            issues.append({"job_id": job["job_id"], "errors": errors})
        else:
            complete_artifacts += 1
    summary_sources = summary.get("sources", []) if summary else []
    complete_summaries = sum(item.get("complete") is True for item in summary_sources)
    declared_sources = int(manifest_summary.get("critical_sources") or 0)
    declared_sequences = int(manifest_summary.get("planned_sequences") or 0)
    declared_frames = int(manifest_summary.get("planned_dense_frames") or 0)
    shape_matches = (
        declared_sources == len(jobs)
        and declared_sequences == planned_sequences
        and declared_frames == planned_frames
    )
    passed = (
        bool(jobs)
        and shape_matches
        and complete_artifacts == len(jobs)
        and len(summary_sources) == len(jobs)
        and complete_summaries == len(jobs)
    )
    return {
        "passed": passed,
        "total_sources": len(jobs),
        "planned_sequences": planned_sequences,
        "planned_frames": planned_frames,
        "declared_sources": declared_sources,
        "declared_sequences": declared_sequences,
        "declared_frames": declared_frames,
        "manifest_shape_matches": shape_matches,
        "complete_artifact_sources": complete_artifacts,
        "summary_sources": len(summary_sources),
        "complete_summary_sources": complete_summaries,
        "issues": issues[:100],
    }


def audit_evidence_map(
    path: Path,
    expected_sources: int,
    visual_source_ids: set[str],
    asr_only_source_ids: set[str],
    temporal_source_ids: set[str],
) -> dict[str, Any]:
    if not path.exists():
        return {"passed": False, "reason": "evidence_map_missing", "source_count": 0}
    try:
        data = load_yaml(path)
    except Exception as exc:
        return {"passed": False, "reason": f"evidence_map_unreadable:{exc}", "source_count": 0}
    sources = data.get("sources", [])
    required = {
        "source_id",
        "framework_ids",
        "asr_timestamp_refs",
        "visual_timestamp_refs",
        "visual_observation_refs",
        "evidence_levels",
        "confidence_boundary",
    }
    incomplete = []
    seen_source_ids: set[str] = set()
    for item in sources:
        source_id = str(item.get("source_id", "unknown"))
        seen_source_ids.add(source_id)
        levels = set(item.get("evidence_levels", []))
        base_incomplete = (
            not required.issubset(item)
            or not item.get("framework_ids")
            or not item.get("asr_timestamp_refs")
            or "asr_timestamp_reviewed_public_safe" not in levels
        )
        visual_incomplete = source_id in visual_source_ids and (
            not item.get("visual_timestamp_refs")
            or not item.get("visual_observation_refs")
            or "visual_model_structured_candidate_public_safe" not in levels
        )
        asr_only_incomplete = source_id in asr_only_source_ids and (
            item.get("visual_timestamp_refs")
            or item.get("visual_observation_refs")
            or "asr_only_conceptual_public_safe" not in levels
        )
        scope_incomplete = (
            source_id not in visual_source_ids and source_id not in asr_only_source_ids
        )
        temporal_incomplete = source_id in temporal_source_ids and (
            not item.get("temporal_sequence_refs")
            or "temporal_pose_proxy_public_safe" not in levels
        )
        if (
            base_incomplete
            or visual_incomplete
            or asr_only_incomplete
            or scope_incomplete
            or temporal_incomplete
        ):
            incomplete.append(source_id)
    expected_source_ids = visual_source_ids | asr_only_source_ids
    return {
        "passed": (
            len(sources) == expected_sources
            and len(seen_source_ids) == len(sources)
            and seen_source_ids == expected_source_ids
            and not incomplete
        ),
        "source_count": len(sources),
        "incomplete_sources": incomplete[:100],
        "missing_source_ids": sorted(expected_source_ids - seen_source_ids)[:100],
        "unexpected_source_ids": sorted(seen_source_ids - expected_source_ids)[:100],
        "required_visual_sources": len(visual_source_ids),
        "required_asr_only_sources": len(asr_only_source_ids),
        "required_temporal_sources": len(temporal_source_ids),
    }


def audit_source_accounting(
    source_index_path: Path,
    manifest_paths: list[Path],
    asr_review_path: Path,
    visual_review_path: Path,
) -> dict[str, Any]:
    with source_index_path.open(encoding="utf-8", newline="") as handle:
        indexed_rows = [
            row
            for row in csv.DictReader(handle, delimiter="\t")
            if str(row.get("platform", "")).casefold() == "bilibili"
        ]
    discovery_types = {"playlist", "search"}
    discovery_rows = [
        row for row in indexed_rows if row.get("source_type") in discovery_types
    ]

    jobs_by_source: dict[str, dict[str, Any]] = {}
    for path in manifest_paths:
        manifest = load_yaml(path)
        for job in manifest.get("jobs", []):
            jobs_by_source[str(job["source_id"]).casefold()] = job

    indexed_video_ids = {
        str(row["source_id"]).casefold()
        for row in indexed_rows
        if row.get("source_type") not in discovery_types
    }
    missing_manifest_source_ids = sorted(indexed_video_ids - set(jobs_by_source))
    extra_manifest_source_ids = sorted(set(jobs_by_source) - indexed_video_ids)

    unavailable_source_ids = [
        source_key
        for source_key, job in jobs_by_source.items()
        if job.get("processing_status") == "unavailable"
    ]

    asr_review = load_yaml(asr_review_path)
    reviewed_asr_ids = {
        str(window["source_id"]).casefold()
        for window in asr_review.get("windows", [])
    }
    accessible_ids = set(jobs_by_source) - set(unavailable_source_ids)
    missing_accessible_asr_ids = sorted(accessible_ids - reviewed_asr_ids)
    unexpected_asr_ids = sorted(reviewed_asr_ids - accessible_ids)

    visual_review = load_yaml(visual_review_path)
    visual_ids = {
        str(job["source_id"]).casefold() for job in visual_review.get("jobs", [])
    }
    asr_only_ids = {
        str(item["source_id"]).casefold()
        for item in visual_review.get("asr_only_sources", [])
    }
    visually_accounted_ids = visual_ids | asr_only_ids
    missing_visual_accounting_ids = sorted(reviewed_asr_ids - visually_accounted_ids)
    unexpected_visual_accounting_ids = sorted(visually_accounted_ids - reviewed_asr_ids)

    passed = (
        len(indexed_rows) == 411
        and len(discovery_rows) == 2
        and len(jobs_by_source) == 409
        and not missing_manifest_source_ids
        and not extra_manifest_source_ids
        and len(unavailable_source_ids) == 1
        and len(accessible_ids) == 408
        and reviewed_asr_ids == accessible_ids
        and visually_accounted_ids == reviewed_asr_ids
    )
    return {
        "passed": passed,
        "indexed_bilibili_rows": len(indexed_rows),
        "discovery_rows": len(discovery_rows),
        "video_jobs": len(jobs_by_source),
        "unavailable_video_jobs": len(unavailable_source_ids),
        "accessible_video_jobs": len(accessible_ids),
        "reviewed_asr_sources": len(reviewed_asr_ids),
        "visual_action_sources": len(visual_ids),
        "asr_only_sources": len(asr_only_ids),
        "missing_accessible_asr_sources": len(missing_accessible_asr_ids),
        "missing_manifest_source_ids": missing_manifest_source_ids,
        "extra_manifest_source_ids": extra_manifest_source_ids,
        "unavailable_source_ids": sorted(unavailable_source_ids),
        "missing_accessible_asr_source_ids": missing_accessible_asr_ids,
        "unexpected_asr_source_ids": unexpected_asr_ids,
        "missing_visual_accounting_source_ids": missing_visual_accounting_ids,
        "unexpected_visual_accounting_source_ids": unexpected_visual_accounting_ids,
    }


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    paths = [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
    return [path for path in paths if (ROOT / path).exists()]


def audit_publication_safety() -> dict[str, Any]:
    files = tracked_files()
    forbidden_extensions = {
        ".mp4", ".mov", ".mkv", ".webm", ".mp3", ".m4a", ".wav", ".jpg",
        ".jpeg", ".png", ".pt", ".pth", ".safetensors", ".bin",
    }
    forbidden_paths = [
        path
        for path in files
        if (path.startswith("data/raw-private/") and not path.endswith("/.gitkeep"))
        or Path(path).suffix.lower() in forbidden_extensions
        or any(part.lower() in {"test", "tests", "eval", "evals"} for part in Path(path).parts)
    ]
    secret_pattern = re.compile(
        r"(?:github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|\bsk-[A-Za-z0-9]{16,})"
    )
    absolute_path_pattern = re.compile(
        r"(?:/dataStor/home/[^/\s]+|/tmp/jhxu-(?:badminton|qwen|conda))"
    )
    secret_hits: list[str] = []
    absolute_path_hits: list[str] = []
    for raw_path in files:
        path = ROOT / raw_path
        try:
            if path.stat().st_size > 25_000_000:
                continue
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if secret_pattern.search(text):
            secret_hits.append(raw_path)
        if (
            raw_path.startswith(("data/corpus/", "skills/", "docs/", "README"))
            and absolute_path_pattern.search(text)
        ):
            absolute_path_hits.append(raw_path)
    return {
        "passed": not forbidden_paths and not secret_hits and not absolute_path_hits,
        "forbidden_tracked_files": forbidden_paths,
        "secret_pattern_hits": secret_hits,
        "absolute_path_hits": absolute_path_hits,
    }


def run_check(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": [
            Path(value).name if Path(value).is_absolute() else value
            for value in command
        ],
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-1200:],
        "stderr_tail": result.stderr[-1200:],
    }


def audit_yaml() -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    count = 0
    for raw_path in tracked_files():
        if Path(raw_path).suffix.lower() not in {".yaml", ".yml"}:
            continue
        count += 1
        try:
            load_yaml(ROOT / raw_path)
        except Exception as exc:
            reason = str(exc).replace(str(ROOT), ".")
            failures.append({"path": raw_path, "reason": reason})
    return {"passed": not failures, "parsed_files": count, "failures": failures}


def duplicate_ids(items: list[dict[str, Any]], field: str) -> list[str]:
    counts = Counter(str(item.get(field) or "") for item in items)
    return sorted(item_id for item_id, count in counts.items() if item_id and count > 1)


def audit_knowledge_integrity() -> dict[str, Any]:
    reference_dir = ROOT / "skills/liu-hui-badminton-coach/references"
    frameworks = load_yaml(reference_dir / "frameworks.yaml")
    drills = load_yaml(reference_dir / "drills.yaml")
    training_plans = load_yaml(reference_dir / "training-plans.yaml")
    rules: list[dict[str, Any]] = []
    for path in sorted(reference_dir.glob("*-rubric.yaml")):
        rules.extend(load_yaml(path))

    framework_ids = {str(item["framework_id"]) for item in frameworks}
    rule_ids = {str(item["rule_id"]) for item in rules}
    drill_ids = {str(item["drill_id"]) for item in drills}
    missing_framework_priorities = [
        {"framework_id": item["framework_id"], "rule_id": rule_id}
        for item in frameworks
        for rule_id in item.get("priority", [])
        if rule_id not in rule_ids
    ]
    missing_rule_drills = [
        {"rule_id": item["rule_id"], "drill_id": drill_id}
        for item in rules
        for drill_id in item.get("drills", [])
        if drill_id not in drill_ids
    ]
    missing_drill_targets = [
        {"drill_id": item["drill_id"], "rule_id": rule_id}
        for item in drills
        for rule_id in item.get("target_issues", [])
        if rule_id not in rule_ids
    ]

    evidence_map = load_yaml(reference_dir / "multimodal-evidence-map.yaml")
    mapped_framework_ids = {
        str(framework_id)
        for source in evidence_map.get("sources", [])
        for framework_id in source.get("framework_ids", [])
    }
    unmapped_framework_ids = sorted(framework_ids - mapped_framework_ids)
    duplicate_framework_ids = duplicate_ids(frameworks, "framework_id")
    duplicate_rule_ids = duplicate_ids(rules, "rule_id")
    duplicate_drill_ids = duplicate_ids(drills, "drill_id")
    duplicate_plan_ids = duplicate_ids(training_plans, "plan_id")
    passed = not any(
        [
            missing_framework_priorities,
            missing_rule_drills,
            missing_drill_targets,
            unmapped_framework_ids,
            duplicate_framework_ids,
            duplicate_rule_ids,
            duplicate_drill_ids,
            duplicate_plan_ids,
        ]
    )
    return {
        "passed": passed,
        "framework_count": len(frameworks),
        "rule_count": len(rules),
        "drill_count": len(drills),
        "training_plan_count": len(training_plans),
        "missing_framework_priorities": missing_framework_priorities,
        "missing_rule_drills": missing_rule_drills,
        "missing_drill_targets": missing_drill_targets,
        "unmapped_framework_ids": unmapped_framework_ids,
        "duplicate_framework_ids": duplicate_framework_ids,
        "duplicate_rule_ids": duplicate_rule_ids,
        "duplicate_drill_ids": duplicate_drill_ids,
        "duplicate_plan_ids": duplicate_plan_ids,
    }


def audit_skill_integration() -> dict[str, Any]:
    skill_path = ROOT / "skills/liu-hui-badminton-coach/SKILL.md"
    text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""
    required = [
        "multimodal-evidence-map.yaml",
        "asr_only_conceptual_public_safe",
        "visual_model_structured_candidate_public_safe",
        "temporal_pose_proxy_public_safe",
        "asr_timestamp_reviewed_public_safe",
    ]
    missing = [item for item in required if item not in text]
    return {"passed": not missing, "missing_references": missing}


def main() -> None:
    args = parse_args()
    visual_manifest = load_yaml(ROOT / args.visual_manifest)
    visual_review = load_yaml(ROOT / args.visual_review)
    temporal_manifest = load_yaml(ROOT / args.temporal_manifest)
    temporal_summary_path = ROOT / args.temporal_summary
    temporal_summary = (
        load_yaml(temporal_summary_path) if temporal_summary_path.exists() else None
    )
    gates = {
        "source_accounting": audit_source_accounting(
            ROOT / "data/source-index.tsv",
            [ROOT / "data/corpus/video-corpus-manifest.yaml"],
            ROOT / "data/corpus/video-asr-timestamp-review.yaml",
            ROOT / "data/corpus/video-visual-review-manifest.yaml",
        ),
        "visual_corpus": audit_visual(visual_manifest),
        "temporal_corpus": audit_temporal(temporal_manifest, temporal_summary),
        "explainability_chain": audit_evidence_map(
            ROOT / args.evidence_map,
            len(visual_manifest.get("jobs", []))
            + len(visual_review.get("asr_only_sources", [])),
            {str(job["source_id"]) for job in visual_manifest.get("jobs", [])},
            {
                str(item["source_id"])
                for item in visual_review.get("asr_only_sources", [])
            },
            {str(job["source_id"]) for job in temporal_manifest.get("jobs", [])},
        ),
        "knowledge_integrity": audit_knowledge_integrity(),
        "skill_integration": audit_skill_integration(),
        "publication_safety": audit_publication_safety(),
        "yaml_integrity": audit_yaml(),
    }
    executable_checks = [
        run_check([sys.executable, "-m", "compileall", "-q", "scripts", "src", "examples"]),
        run_check([sys.executable, "scripts/check_source_integrity.py"]),
        run_check([sys.executable, "examples/run_usage_case.py"]),
        run_check([sys.executable, "examples/run_full_system_cases.py"]),
    ]
    gates["runtime_behavior"] = {
        "passed": all(item["passed"] for item in executable_checks),
        "checks": executable_checks,
    }
    complete = all(gate.get("passed") is True for gate in gates.values())
    output = {
        "multimodal_completion_audit": {
            "run_id": f"multimodal_completion_{date.today().strftime('%Y%m%d')}",
            "created_at": date.today().isoformat(),
            "complete": complete,
            "gate_count": len(gates),
            "passed_gate_count": sum(gate.get("passed") is True for gate in gates.values()),
        },
        "gates": gates,
    }
    write_yaml(ROOT / args.output, output)
    print(f"wrote {args.output}")
    print(f"complete {str(complete).lower()}")
    for name, gate in gates.items():
        print(f"{name} {'pass' if gate.get('passed') else 'fail'}")
    if not complete and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
