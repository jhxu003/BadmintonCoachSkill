#!/usr/bin/env python3
"""Inventory private coach-video clips and staged keyframes without publishing media.

The batch pipeline can assign one physical candidate clip to multiple technique
routes.  This script therefore inventories unique physical assets first, while
retaining every semantic action assignment.  It also reconciles the original
and continuity passes for Li Yuxuan and Zheng Siwei so counts are not inflated.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BATCHES = (
    ("liu_hui", "primary", "liu-hui-context-v1", 30),
    ("li_yuxuan", "primary", "li-yuxuan-v1", 10),
    ("li_yuxuan", "continuity", "li-yuxuan-v1-continuity-v1", 20),
    ("zheng_siwei", "primary", "zheng-siwei-v1", 10),
    ("zheng_siwei", "continuity", "zheng-siwei-v1-continuity-v1", 20),
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_or_absolute(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def approved_for_teaching(episode: dict[str, Any]) -> bool:
    return (
        episode.get("demonstrator_role") == "coach"
        and episode.get("example_polarity") == "correct"
        and episode.get("context_review_status") == "agent_reviewed"
        and episode.get("artifact_role") != "review_context"
        and not episode.get("review_context_only", False)
    )


def context_review_required(episode: dict[str, Any]) -> bool:
    """Whether the context model is expected to produce a decision.

    This exactly mirrors the fail-closed review eligibility used by the batch
    command when ``--include-review-candidates`` is enabled.  A candidate
    which failed only the action gate (while otherwise being a resolved,
    ordinary candidate) has no remaining path to promotion, so it must not
    appear as an indefinitely pending model review in the inventory.
    """
    return (
        episode.get("automatic_admission") is True
        or episode.get("review_context_only") is True
        or episode.get("semantic_assignment_status") != "resolved"
    )


def action_gate_rejection_reasons(episode: dict[str, Any]) -> list[str]:
    """Return terminal reasons for candidates that cannot enter context review."""
    if context_review_required(episode):
        return []
    # The only remaining path is a complete, resolved candidate which the
    # strict action gate did not automatically admit.  Do not call this an
    # agent/context rejection: no context model result exists for it.
    return ["action_gate_not_automatic_admission"]


def quality_rank(row: dict[str, Any]) -> tuple[int, int, int, int, float]:
    return (
        int(row["teaching_approved"]),
        int(row["classification"] == "continuous_demonstration"),
        int(row["confidence"] == "high"),
        int(row["pass_priority"]),
        float(row.get("score") or 0.0),
    )


def interval_iou(left: dict[str, Any], right: dict[str, Any]) -> float:
    start = max(left["action_start_seconds"], right["action_start_seconds"])
    end = min(left["action_end_seconds"], right["action_end_seconds"])
    overlap = max(0.0, end - start)
    union = max(left["action_end_seconds"], right["action_end_seconds"]) - min(
        left["action_start_seconds"], right["action_start_seconds"]
    )
    return overlap / union if union > 0 else 0.0


def reconcile_duplicates(rows: list[dict[str, Any]]) -> None:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["coach"], row["source_id"])].append(row)

    for group in groups.values():
        ordered = sorted(group, key=quality_rank, reverse=True)
        canonicals: list[dict[str, Any]] = []
        for row in ordered:
            duplicate = None
            row_actions = set(row["actions"])
            for canonical in canonicals:
                if not row_actions.intersection(canonical["actions"]):
                    continue
                if interval_iou(row, canonical) >= 0.80:
                    duplicate = canonical
                    break
            if duplicate is None:
                canonicals.append(row)
                continue
            row["duplicate_of"] = duplicate["asset_id"]


def build_inventory(project: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    corpus_root = project / ".runtime" / "full-corpus-processing-v1"
    rows: list[dict[str, Any]] = []
    source_map: dict[tuple[str, str], dict[str, Any]] = {}
    batch_summaries: list[dict[str, Any]] = []

    for coach, pass_name, directory, pass_priority in BATCHES:
        batch_root = corpus_root / directory
        manifest = load_json(batch_root / "manifest.json")
        manifest_videos = manifest["videos"]
        batch_row_start = len(rows)

        for fallback_index, video in enumerate(manifest_videos):
            job_id = video["job_id"]
            source_id = video["source_id"]
            video_root = batch_root / "videos" / job_id
            package_path = video_root / "lesson-package.json"
            source_key = (coach, source_id)
            source = source_map.setdefault(
                source_key,
                {
                    "coach": coach,
                    "source_id": source_id,
                    "title": video["title"],
                    "url": video.get("url", ""),
                    "duration_seconds": video.get("duration_seconds"),
                    "passes": [],
                    "asset_ids": [],
                },
            )
            source["passes"].append(
                {
                    "pass": pass_name,
                    "batch": directory,
                    "job_id": job_id,
                    "video_index": video.get("video_index", fallback_index),
                    "lesson_package_exists": package_path.is_file(),
                }
            )
            if not package_path.is_file():
                continue

            package = load_json(package_path)
            context_results: dict[tuple[str, str], dict[str, Any]] = {}
            context_path = video_root / "context-review.jsonl"
            if context_path.is_file():
                for line in context_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    decision = json.loads(line)
                    context_results[
                        (str(decision.get("action", "")), str(decision.get("episode_id", "")))
                    ] = decision
            physical: dict[str, dict[str, Any]] = {}
            for technique in package.get("techniques", []):
                for episode in technique.get("episodes", []):
                    candidate_id = str(episode.get("candidate_id") or episode["episode_id"])
                    clip_rel = str(episode.get("clip") or "")
                    physical_key = clip_rel or candidate_id
                    item = physical.setdefault(
                        physical_key,
                        {
                            "episode": episode,
                            "actions": set(),
                            "labels_zh": set(),
                            "family_ids": set(),
                            "teaching_summaries_zh": set(),
                            "assignments": [],
                        },
                    )
                    item["actions"].add(technique["action"])
                    item["labels_zh"].add(technique.get("label_zh", technique["action"]))
                    item["family_ids"].add(technique.get("family_id", ""))
                    if technique.get("teaching_summary_zh"):
                        item["teaching_summaries_zh"].add(
                            str(technique["teaching_summary_zh"])
                        )
                    item["assignments"].append(
                        {
                            "action": technique["action"],
                            "episode_id": episode["episode_id"],
                        }
                    )

            for physical_key, item in physical.items():
                episode = item["episode"]
                candidate_id = str(episode.get("candidate_id") or episode["episode_id"])
                clip_rel = str(episode.get("clip") or "")
                clip_path = video_root / clip_rel if clip_rel else video_root / "__missing_clip__"
                frame_paths = [video_root / frame["image"] for frame in episode.get("frames", [])]
                clip_ok = bool(clip_rel) and clip_path.is_file() and clip_path.stat().st_size > 0
                frame_ok = [path.is_file() and path.stat().st_size > 0 for path in frame_paths]
                frames_complete = len(frame_paths) >= 7 and all(frame_ok)
                assets_complete = clip_ok and frames_complete
                decisions = [
                    context_results[(assignment["action"], assignment["episode_id"])]
                    for assignment in item["assignments"]
                    if (assignment["action"], assignment["episode_id"]) in context_results
                ]
                approved_decisions = [
                    decision
                    for decision in decisions
                    if decision.get("decision") == "approve"
                    and decision.get("demonstrator_role") == "coach"
                    and decision.get("example_polarity") == "correct"
                    and decision.get("context_review_status") == "agent_reviewed"
                ]
                primary_decision = approved_decisions[0] if approved_decisions else (
                    decisions[0] if decisions else {}
                )
                reviewed_rejection_reasons = list(
                    primary_decision.get("context_rejection_reasons", [])
                    if isinstance(primary_decision.get("context_rejection_reasons", []), list)
                    else []
                )
                gate_rejection_reasons = action_gate_rejection_reasons(episode)
                terminal_state = (
                    "teaching_ready"
                    if approved_decisions
                    else "reviewed_rejected"
                    if primary_decision.get("decision") == "reject"
                    else "action_gate_rejected"
                    if gate_rejection_reasons
                    else "pending_context_review"
                )
                action_start = float(episode.get("action_start_seconds") or 0.0)
                action_end = float(episode.get("action_end_seconds") or action_start)
                asset_id = f"{directory}:{job_id}:{candidate_id}"
                row = {
                    "asset_id": asset_id,
                    "coach": coach,
                    "pass": pass_name,
                    "pass_priority": pass_priority,
                    "batch": directory,
                    "job_id": job_id,
                    "source_id": source_id,
                    "title": video["title"],
                    "url": video.get("url", ""),
                    "candidate_id": candidate_id,
                    "episode_ids": sorted(
                        {assignment["episode_id"] for assignment in item["assignments"]}
                    ),
                    "actions": sorted(item["actions"]),
                    "labels_zh": sorted(item["labels_zh"]),
                    "family_ids": sorted(value for value in item["family_ids"] if value),
                    "teaching_summaries_zh": sorted(item["teaching_summaries_zh"]),
                    "classification": episode.get("classification", "unknown"),
                    "confidence": episode.get("confidence", "unknown"),
                    "demonstration_purity": episode.get("demonstration_purity", "unknown"),
                    "semantic_compatibility": episode.get("semantic_compatibility", "unknown"),
                    "review_status": episode.get("review_status", "unknown"),
                    "demonstrator_role": primary_decision.get(
                        "demonstrator_role", episode.get("demonstrator_role", "unknown")
                    ),
                    "example_polarity": primary_decision.get(
                        "example_polarity", episode.get("example_polarity", "unknown")
                    ),
                    "context_review_status": primary_decision.get(
                        "context_review_status", episode.get("context_review_status", "unknown")
                    ),
                    "context_decisions": [
                        {
                            key: decision.get(key)
                            for key in (
                                "action",
                                "episode_id",
                                "decision",
                                "demonstrator_role",
                                "example_polarity",
                                "context_review_status",
                                "context_start_seconds",
                                "context_end_seconds",
                                "context_evidence",
                                "context_rejection_reasons",
                            )
                        }
                        for decision in decisions
                    ],
                    "approved_actions": sorted(
                        {
                            str(decision.get("action", ""))
                            for decision in approved_decisions
                            if decision.get("action")
                        }
                    ),
                    "artifact_role": episode.get("artifact_role", "teaching_candidate"),
                    "review_context_only": bool(episode.get("review_context_only", False)),
                    "teaching_approved": bool(approved_decisions),
                    "review_terminal_state": terminal_state,
                    "review_rejection_reasons": (
                        reviewed_rejection_reasons
                        if terminal_state == "reviewed_rejected"
                        else gate_rejection_reasons
                    ),
                    "score": episode.get("score"),
                    "scope_limitations": episode.get("scope_limitations", []),
                    "action_start_seconds": action_start,
                    "action_end_seconds": action_end,
                    "clip_start_seconds": float(episode.get("clip_start_seconds") or action_start),
                    "clip_end_seconds": float(episode.get("clip_end_seconds") or action_end),
                    "clip": relative_or_absolute(clip_path, project),
                    "clip_exists": clip_ok,
                    "clip_bytes": clip_path.stat().st_size if clip_ok else 0,
                    "frames": [relative_or_absolute(path, project) for path in frame_paths],
                    "frame_labels_zh": [
                        str(frame.get("label_zh") or f"阶段 {index:02d}")
                        for index, frame in enumerate(episode.get("frames", []), start=1)
                    ],
                    "frame_anchor_seconds": [
                        float(frame.get("anchor_seconds") or 0.0)
                        for frame in episode.get("frames", [])
                    ],
                    "frame_teaching_points_zh": [
                        str(frame.get("teaching_point_zh") or "")
                        for frame in episode.get("frames", [])
                    ],
                    "expected_frame_count": len(frame_paths),
                    "existing_frame_count": sum(frame_ok),
                    "frames_complete": frames_complete,
                    "assets_complete": assets_complete,
                    "duplicate_of": None,
                }
                rows.append(row)
                source["asset_ids"].append(asset_id)

        batch_rows = rows[batch_row_start:]
        batch_summaries.append(
            {
                "coach": coach,
                "pass": pass_name,
                "batch": directory,
                "video_count": len(manifest_videos),
                "lesson_package_count": sum(
                    (batch_root / "videos" / video["job_id"] / "lesson-package.json").is_file()
                    for video in manifest_videos
                ),
                "unique_asset_count": len(batch_rows),
                "complete_asset_count": sum(row["assets_complete"] for row in batch_rows),
                "missing_asset_count": sum(not row["assets_complete"] for row in batch_rows),
                "teaching_approved_asset_count": sum(row["teaching_approved"] for row in batch_rows),
            }
        )

    reconcile_duplicates(rows)
    asset_lookup = {row["asset_id"]: row for row in rows}
    for row in rows:
        if row["duplicate_of"]:
            row["state"] = "duplicate_existing" if row["assets_complete"] else "duplicate_missing"
        elif row["teaching_approved"]:
            row["state"] = "ready_existing" if row["assets_complete"] else "ready_to_materialize"
        elif row["review_terminal_state"] == "reviewed_rejected":
            row["state"] = (
                "reviewed_rejected_existing"
                if row["assets_complete"]
                else "reviewed_rejected_missing"
            )
        elif row["review_terminal_state"] == "action_gate_rejected":
            row["state"] = (
                "action_gate_rejected_existing"
                if row["assets_complete"]
                else "action_gate_rejected_missing"
            )
        else:
            row["state"] = "candidate_existing" if row["assets_complete"] else "candidate_to_materialize"

    sources = []
    for source in source_map.values():
        source_rows = [asset_lookup[asset_id] for asset_id in source["asset_ids"]]
        canonical_rows = [row for row in source_rows if not row["duplicate_of"]]
        if any(row["state"] == "ready_existing" for row in canonical_rows):
            state = "ready_existing"
        elif any(row["state"] == "ready_to_materialize" for row in canonical_rows):
            state = "ready_to_materialize"
        elif any(row["state"] == "candidate_existing" for row in canonical_rows):
            state = "candidate_existing"
        elif any(row["state"] == "candidate_to_materialize" for row in canonical_rows):
            state = "candidate_to_materialize"
        elif any(row["state"].startswith("reviewed_rejected") for row in canonical_rows):
            state = "reviewed_rejected"
        elif any(row["state"].startswith("action_gate_rejected") for row in canonical_rows):
            state = "action_gate_rejected"
        else:
            state = "no_reliable_episode"
        source["state"] = state
        source["canonical_asset_count"] = len(canonical_rows)
        source["teaching_approved_asset_count"] = sum(row["teaching_approved"] for row in canonical_rows)
        sources.append(source)

    rows.sort(key=lambda row: (row["coach"], row["source_id"], row["action_start_seconds"], row["batch"]))
    sources.sort(key=lambda row: (row["coach"], row["source_id"]))
    state_counts = Counter(row["state"] for row in rows)
    source_state_counts = Counter(row["state"] for row in sources)
    coach_summary = {}
    for coach in sorted({row["coach"] for row in sources}):
        coach_sources = [row for row in sources if row["coach"] == coach]
        coach_assets = [row for row in rows if row["coach"] == coach and not row["duplicate_of"]]
        coach_summary[coach] = {
            "source_count": len(coach_sources),
            "source_states": dict(Counter(row["state"] for row in coach_sources)),
            "canonical_asset_count": len(coach_assets),
            "complete_asset_count": sum(row["assets_complete"] for row in coach_assets),
            "missing_asset_count": sum(not row["assets_complete"] for row in coach_assets),
            "teaching_approved_asset_count": sum(row["teaching_approved"] for row in coach_assets),
            "clip_bytes": sum(row["clip_bytes"] for row in coach_assets),
            "existing_frame_count": sum(row["existing_frame_count"] for row in coach_assets),
        }

    summary = {
        "inventory_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": str(project),
        "privacy": "private_runtime_only_not_for_git_or_public_pages",
        "source_count": len(sources),
        "source_state_counts": dict(source_state_counts),
        "physical_asset_count_including_duplicates": len(rows),
        "duplicate_asset_count": sum(bool(row["duplicate_of"]) for row in rows),
        "canonical_asset_count": sum(not row["duplicate_of"] for row in rows),
        "asset_state_counts": dict(state_counts),
        "complete_canonical_asset_count": sum(
            row["assets_complete"] and not row["duplicate_of"] for row in rows
        ),
        "missing_canonical_asset_count": sum(
            not row["assets_complete"] and not row["duplicate_of"] for row in rows
        ),
        "teaching_approved_canonical_asset_count": sum(
            row["teaching_approved"] and not row["duplicate_of"] for row in rows
        ),
        "existing_canonical_clip_bytes": sum(
            row["clip_bytes"] for row in rows if not row["duplicate_of"]
        ),
        "existing_canonical_frame_count": sum(
            row["existing_frame_count"] for row in rows if not row["duplicate_of"]
        ),
        "batches": batch_summaries,
        "coaches": coach_summary,
        "sources": sources,
    }
    return summary, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    summary, rows = build_inventory(project)
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (output / "assets.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {key: value for key, value in summary.items() if key not in {"sources"}},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
