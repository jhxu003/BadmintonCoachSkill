#!/usr/bin/env python3
"""Audit private source/topic/candidate closure without exposing media.

This command consumes a private media inventory and the committed public
source/topic maps.  Its JSON report stays under ``.runtime``: it is an
operational acceptance record, not a Pages or Git artifact.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


COACH_KEYS = {
    "liu-hui": "liu_hui",
    "li-yuxuan": "li_yuxuan",
    "zheng-siwei": "zheng_siwei",
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [
        row
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
        if isinstance(row, dict)
    ]


def build_audit(project: Path, inventory_dir: Path) -> dict[str, Any]:
    summary = load_json(inventory_dir / "summary.json")
    rows = load_rows(inventory_dir / "assets.jsonl")
    canonical = [row for row in rows if not row.get("duplicate_of")]
    source_states = {
        (str(source["coach"]), str(source["source_id"])): str(source["state"])
        for source in summary.get("sources", [])
        if isinstance(source, dict)
    }
    terminal_asset_states = {
        "ready_existing",
        "reviewed_rejected_existing",
        "action_gate_rejected_existing",
    }
    coaches: dict[str, Any] = {}
    pending_asset_ids: list[str] = []
    missing_sources: list[str] = []

    for coach_id, inventory_coach in COACH_KEYS.items():
        reference_dir = project / "skills" / f"{coach_id}-badminton-coach" / "references"
        source_index = load_json(reference_dir / "source-topic-index.json")
        topic_units = load_json(reference_dir / "topic-teaching-units.json")
        course_catalog = yaml.safe_load((reference_dir / "technique-courses.yaml").read_text(encoding="utf-8"))
        techniques = {
            str(item["technique_id"]): set(str(action) for action in item.get("applicable_actions", []))
            for item in course_catalog.get("techniques", [])
            if isinstance(item, dict) and item.get("technique_id")
        }
        expected_sources = {
            str(item["source_id"])
            for item in source_index.get("sources", [])
            if isinstance(item, dict)
        }
        inventory_sources = {
            source_id
            for candidate_coach, source_id in source_states
            if candidate_coach == inventory_coach
        }
        absent = sorted(expected_sources - inventory_sources)
        missing_sources.extend(f"{coach_id}:{item}" for item in absent)
        coach_assets = [row for row in canonical if row.get("coach") == inventory_coach]
        pending = [row for row in coach_assets if row.get("state") not in terminal_asset_states]
        pending_asset_ids.extend(str(row.get("asset_id", "")) for row in pending)
        topic_source_ids = {
            source_id
            for unit in topic_units.get("units", [])
            if isinstance(unit, dict)
            for source_id in unit.get("source_ids", [])
            if isinstance(source_id, str)
        }
        approved_topic_media_bindings = []
        for unit in topic_units.get("units", []):
            if not isinstance(unit, dict) or not unit.get("parent_technique_id"):
                continue
            allowed_actions = techniques.get(str(unit["parent_technique_id"]), set())
            for asset in coach_assets:
                if (
                    asset.get("state") != "ready_existing"
                    or asset.get("source_id") not in unit.get("source_ids", [])
                ):
                    continue
                actions = sorted(set(asset.get("approved_actions", [])) & allowed_actions)
                if actions:
                    approved_topic_media_bindings.append(
                        {
                            "topic_id": unit["topic_id"],
                            "source_id": asset["source_id"],
                            "asset_id": asset["asset_id"],
                            "actions": actions,
                        }
                    )
        coaches[coach_id] = {
            "source_count": len(expected_sources),
            "topic_unit_count": int(topic_units.get("unit_count", 0)),
            "missing_inventory_sources": absent,
            "source_without_topic_unit": sorted(expected_sources - topic_source_ids),
            "source_terminal_states": dict(
                Counter(
                    state
                    for (candidate_coach, _), state in source_states.items()
                    if candidate_coach == inventory_coach
                )
            ),
            "canonical_asset_count": len(coach_assets),
            "asset_terminal_states": dict(Counter(str(row.get("state", "")) for row in coach_assets)),
            "pending_asset_count": len(pending),
            "teaching_ready_asset_count": sum(
                row.get("state") == "ready_existing" for row in coach_assets
            ),
            "reviewed_rejected_asset_count": sum(
                row.get("state") == "reviewed_rejected_existing" for row in coach_assets
            ),
            "action_gate_rejected_asset_count": sum(
                row.get("state") == "action_gate_rejected_existing" for row in coach_assets
            ),
            "approved_topic_media_binding_count": len(approved_topic_media_bindings),
            "approved_topic_media_bindings": approved_topic_media_bindings,
        }

    terminal_source_states = {
        "ready_existing",
        "reviewed_rejected",
        "action_gate_rejected",
        "no_reliable_episode",
    }
    nonterminal_sources = sorted(
        f"{coach}:{source_id}"
        for (coach, source_id), state in source_states.items()
        if state not in terminal_source_states
    )
    return {
        "audit_version": 1,
        "privacy": "private_runtime_only_not_for_git_or_public_pages",
        "source_count": int(summary.get("source_count", 0)),
        "canonical_asset_count": len(canonical),
        "coaches": coaches,
        "missing_inventory_source_count": len(missing_sources),
        "missing_inventory_sources": missing_sources,
        "nonterminal_source_count": len(nonterminal_sources),
        "nonterminal_sources": nonterminal_sources,
        "pending_canonical_asset_count": len(pending_asset_ids),
        "pending_canonical_asset_ids": pending_asset_ids,
        "status": "complete"
        if not missing_sources and not nonterminal_sources and not pending_asset_ids
        else "incomplete",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-terminal", action="store_true")
    args = parser.parse_args()
    audit = build_audit(args.project.resolve(), args.inventory.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if not key.endswith("sources") and not key.endswith("ids")}, ensure_ascii=False, indent=2))
    if args.require_terminal and audit["status"] != "complete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
