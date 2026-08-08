#!/usr/bin/env python3
"""Build safe, source-linked teaching units for every routed coach topic.

The committed output contains only public source IDs and existing Skill
references.  It deliberately does not read media, ASR, model output, clips,
frames, private paths, or runtime decisions.  A topic unit is therefore
knowledge-only until the private evidence audit binds an exact reviewed asset.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


REFERENCE_DIRS = {
    "liu-hui": "skills/liu-hui-badminton-coach/references",
    "li-yuxuan": "skills/li-yuxuan-badminton-coach/references",
    "zheng-siwei": "skills/zheng-siwei-badminton-coach/references",
}

# This table is deliberately explicit rather than a title-keyword heuristic.
# A topic may inherit only the parent curriculum node's already-reviewed
# frameworks, rules, drills and retest metrics; it never manufactures a new
# deterministic rule from a source title.
PARENT_TECHNIQUE_BY_SYSTEM = {
    "liu-hui": {
        "overhead_power_chain": "overhead-base-chain",
        "smash_variant_system": "smash",
        "rear_court_base_and_high_clear": "high-clear",
        "drop_slice_slide_variation": "drop-variation-route",
        "footwork_arrival_recovery": "rear-court-footwork",
        "backhand_and_rear_corner_choice": "passive-backhand",
        "drive_receive_and_front_exchange": "drive",
        "doubles_singles_tactics_and_match_transfer": "doubles-continuity",
        "safety_equipment_and_load_selection": "match-transfer",
        "student_fit_and_diagnosis": "match-transfer",
    },
    "li-yuxuan": {
        "learner_fit": "rally-transfer",
        "equipment_safety": "rally-transfer",
        "backhand_time_budget": "backhand-early-choice",
        "serve_receive": "doubles-first-two-shots",
        "drop_drive": "overhead-variation",
        "smash": "smash-progression",
        "high_clear": "high-clear",
        "footwork": "rear-court-time-budget",
        "release": "high-clear",
        "match_transfer": "rally-transfer",
    },
    "zheng-siwei": {
        "serve_opening": "serve-third-shot-plan",
        "receive_opening_exchange": "receive-cut-waist",
        "frontcourt_pressure": "net-drop",
        "defense_transition": "rear-pressure-retreat",
        "pair_rotation_two_lanes": "pair-rotation-two-lanes",
        "rear_attack_continuity": "rear-attack-footwork",
        "reset_match_transfer": "reset-match-transfer",
    },
}

# Narrow title routes occasionally split one coach-system branch more finely
# than the parent-system default.  These overrides are restricted to existing
# curriculum nodes and are used only for source+topic+course exact matching.
PARENT_TECHNIQUE_BY_TOPIC = {
    "liu-hui": {
        "liu-slide-drop": "slice-drop",
        "liu-light-drop": "slice-drop",
        "liu-serve-receive": "high-serve",
    },
    "li-yuxuan": {
        "lyx-drive": "drive",
        "lyx-recovery": "net-lunge",
    },
    "zheng-siwei": {
        "zsw-left-receive": "left-receive-route",
        "zsw-backhand-low-transition": "backhand-low-transition",
    },
}


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid YAML mapping: {path}")
    return payload


def build_units(project: Path, coach_id: str) -> dict[str, Any]:
    reference_dir = project / REFERENCE_DIRS[coach_id]
    source_index = json.loads((reference_dir / "source-topic-index.json").read_text(encoding="utf-8"))
    catalog = load_yaml(reference_dir / "technique-courses.yaml")
    techniques = {
        str(item["technique_id"]): item
        for item in catalog.get("techniques", [])
        if isinstance(item, dict) and item.get("technique_id")
    }
    systems = {
        str(item["system_id"]): item
        for item in catalog.get("systems", [])
        if isinstance(item, dict) and item.get("system_id")
    }
    reviewed_courses_by_source_and_technique: dict[tuple[str, str], list[str]] = defaultdict(list)
    for course in catalog.get("courses", []):
        if not isinstance(course, dict) or course.get("status") != "teaching_ready":
            continue
        source = course.get("source", {})
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("source_id", ""))
        technique_id = str(course.get("technique_id", ""))
        course_id = str(course.get("course_id", ""))
        if source_id and technique_id and course_id:
            reviewed_courses_by_source_and_technique[(source_id, technique_id)].append(course_id)
    grouped: dict[str, dict[str, Any]] = {}
    for source in source_index.get("sources", []):
        if not isinstance(source, dict):
            continue
        fallback_system = source.get("system", {})
        fallback_system_id = str(fallback_system.get("id", "")) if isinstance(fallback_system, dict) else ""
        source_id = str(source.get("source_id", ""))
        for topic in source.get("topics", []):
            if not isinstance(topic, dict):
                continue
            topic_id = str(topic.get("id", ""))
            if not topic_id or not source_id:
                continue
            system_id = str(topic.get("system_id", fallback_system_id))
            current = grouped.setdefault(
                topic_id,
                {
                    "topic_id": topic_id,
                    "topic_name_zh": str(topic.get("name", "")),
                    "coach_system_id": system_id,
                    "source_ids": [],
                },
            )
            if current["coach_system_id"] != system_id:
                raise ValueError(f"topic has conflicting coach systems: {coach_id}:{topic_id}")
            current["source_ids"].append(source_id)

    units: list[dict[str, Any]] = []
    for topic_id, raw in sorted(grouped.items()):
        parent_id = PARENT_TECHNIQUE_BY_TOPIC.get(coach_id, {}).get(topic_id) or PARENT_TECHNIQUE_BY_SYSTEM.get(
            coach_id, {}
        ).get(raw["coach_system_id"])
        parent = techniques.get(parent_id or "")
        if parent is None:
            units.append(
                {
                    **raw,
                    "source_ids": sorted(set(raw["source_ids"])),
                    "knowledge_status": "source_context_only",
                    "media_status": "no_reliable_topic_bound_media",
                    "reviewed_course_ids": [],
                    "learning_goal_zh": "该来源标题可用于定位主题，但尚无可复用的体系内教学单元。",
                    "framework_ids": [],
                    "rule_ids": [],
                    "drill_ids": [],
                    "retest_metrics": [],
                    "prerequisite_topic_ids": [],
                    "next_topic_ids": [],
                }
            )
            continue
        reviewed_course_ids = sorted(
            {
                course_id
                for source_id in raw["source_ids"]
                for course_id in reviewed_courses_by_source_and_technique.get(
                    (source_id, parent_id), []
                )
            }
        )
        units.append(
            {
                **raw,
                "source_ids": sorted(set(raw["source_ids"])),
                "knowledge_status": "parent_curriculum_bound",
                "parent_technique_id": parent_id,
                # Exact topic media must be separately reviewed; a parent
                # technique's public course cannot be borrowed as a topic clip.
                "media_status": (
                    "teaching_ready" if reviewed_course_ids else "no_reliable_topic_bound_media"
                ),
                "reviewed_course_ids": reviewed_course_ids,
                "learning_goal_zh": (
                    f"围绕“{raw['topic_name_zh']}”学习：{parent['summary_zh']}"
                ),
                "framework_ids": list(parent["framework_ids"]),
                "rule_ids": list(parent["rule_ids"]),
                "drill_ids": list(parent["drill_ids"]),
                "retest_metrics": list(parent["retest_metrics"]),
                "prerequisite_topic_ids": [],
                "next_topic_ids": [],
            }
        )

    by_parent: dict[str, list[str]] = defaultdict(list)
    for unit in units:
        if unit.get("parent_technique_id"):
            by_parent[str(unit["parent_technique_id"])].append(str(unit["topic_id"]))
    for unit in units:
        parent = techniques.get(str(unit.get("parent_technique_id", "")))
        if not parent:
            continue
        prerequisite = [
            topic
            for technique_id in parent.get("prerequisite_technique_ids", [])
            for topic in by_parent.get(str(technique_id), [])
        ]
        following = [
            topic
            for technique_id in parent.get("next_technique_ids", [])
            for topic in by_parent.get(str(technique_id), [])
        ]
        unit["prerequisite_topic_ids"] = sorted(set(prerequisite))
        unit["next_topic_ids"] = sorted(set(following))

    return {
        "schema_version": "coach-topic-teaching-unit/v1",
        "coach_id": coach_id,
        "unit_count": len(units),
        "publication_boundary": "public source IDs and existing Skill references only; no media, frames, clips, ASR, private paths, runtime decisions, or model output",
        "usage_boundary": "topic units are knowledge-only until a same-source, same-topic private evidence audit binds an approved continuous coach demonstration",
        "evidence_boundary": "ordinary monocular video cannot prove exact contact, racket-face angle, true internal rotation, grip pressure, force, calibrated 3D kinematics, or opponent intent",
        "systems": sorted(
            {
                unit["coach_system_id"]
                for unit in units
                if unit["coach_system_id"] in systems
            }
        ),
        "units": units,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    args = parser.parse_args()
    project = args.project.resolve()
    for coach_id, relative in REFERENCE_DIRS.items():
        output = project / relative / "topic-teaching-units.json"
        payload = build_units(project, coach_id)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"TOPIC_UNITS {coach_id} {payload['unit_count']} {output}")


if __name__ == "__main__":
    main()
