#!/usr/bin/env python3
"""Validate the Liu Hui teaching-demonstration contract and a staged lesson set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml


REQUIRED_SKILL_PHRASES = (
    "Teaching demonstration",
    "Structured diagnosis",
    "video-lesson-contract.md",
    "continuous pure-action episode",
    "full episode boundary",
    "demonstrator_role=coach",
    "example_polarity=correct",
)
FORBIDDEN_PUBLISHED_MARKERS = (
    "data/raw-private",
    ".runtime",
    ".downloads",
    "private asr",
    "model_output",
    "access_token",
    "api_key",
    "password",
    "secret",
)
PHASE_ORDER = (
    "preparation",
    "start",
    "arrival",
    "top_elbow",
    "contact_window",
    "follow_through",
    "recovery",
)
MIN_CONTEXT_SIDE_SECONDS = 20.0


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate_skill(repo: Path) -> dict[str, int]:
    skill = (repo / "skills/liu-hui-badminton-coach/SKILL.md").read_text(
        encoding="utf-8"
    )
    missing = [phrase for phrase in REQUIRED_SKILL_PHRASES if phrase not in skill]
    if missing:
        raise ValueError(f"skill is missing required contract phrases: {missing}")

    references = repo / "skills/liu-hui-badminton-coach/references"
    contract = (references / "video-lesson-contract.md").read_text(encoding="utf-8")
    if "no_reliable_action_episode" not in contract:
        raise ValueError("video lesson contract lacks the reliable-action gap rule")
    routes = load_yaml(references / "video-lesson-routing.yaml")
    route_actions = [route["action"] for route in routes["routes"]]
    if len(route_actions) != len(set(route_actions)):
        raise ValueError("video lesson routes contain duplicate action ids")
    catalog = load_yaml(references / "video-lessons.yaml")
    if not catalog.get("lessons"):
        raise ValueError("fallback video lesson catalog is empty")
    return {
        "route_count": len(route_actions),
        "fallback_lesson_count": len(catalog["lessons"]),
    }


def validate_staged_lessons(repo: Path, lesson_root: Path) -> dict[str, int]:
    schema = json.loads(
        (repo / "schemas/video-lesson-package.schema.json").read_text(encoding="utf-8")
    )
    index_path = lesson_root / "video-lessons-index.yaml"
    index = load_yaml(index_path)
    if index.get("version") != 1:
        raise ValueError("lesson index must declare version 1")
    lessons: list[dict[str, Any]] = []
    for item in index.get("lessons", []):
        shard = lesson_root / item["shard"]
        if not shard.is_file():
            raise ValueError(f"missing indexed shard: {shard}")
    for shard in sorted((lesson_root / "video-lessons").glob("*.yaml")):
        document = load_yaml(shard)
        lessons.extend(document.get("lessons", []))
    if len(lessons) != index.get("lesson_count"):
        raise ValueError("lesson index count does not equal shard content")
    if len({lesson["lesson_id"] for lesson in lessons}) != len(lessons):
        raise ValueError("lesson ids must be unique")
    if {lesson["lesson_id"] for lesson in lessons} != {
        item["lesson_id"] for item in index.get("lessons", [])
    }:
        raise ValueError("lesson index and shard ids differ")

    for lesson in lessons:
        jsonschema.validate(instance=lesson, schema=schema)
        if lesson["semantic_review_status"] != "agent_reviewed":
            raise ValueError(f"unreviewed lesson: {lesson['lesson_id']}")
        if lesson["review_status"] != "agent_reviewed":
            raise ValueError(f"unreviewed package: {lesson['lesson_id']}")
        if lesson["completeness"] != "complete_demonstration":
            raise ValueError(f"non-complete lesson staged: {lesson['lesson_id']}")
        if lesson.get("demonstrator_role") != "coach":
            raise ValueError(f"non-coach demonstrator staged: {lesson['lesson_id']}")
        if lesson.get("example_polarity") != "correct":
            raise ValueError(f"non-correct example staged: {lesson['lesson_id']}")
        if lesson.get("context_review_status") != "agent_reviewed":
            raise ValueError(f"unreviewed lesson context: {lesson['lesson_id']}")
        if not lesson.get("context_evidence"):
            raise ValueError(f"missing context evidence: {lesson['lesson_id']}")
        episode = lesson["episode"]
        if not (
            episode["start_seconds"] <= episode["end_seconds"]
            <= episode["clip_end_seconds"]
        ):
            raise ValueError(f"invalid episode boundary: {lesson['lesson_id']}")
        if (
            episode["start_seconds"] - lesson["context_start_seconds"]
            < MIN_CONTEXT_SIDE_SECONDS
            or lesson["context_end_seconds"] - episode["end_seconds"]
            < MIN_CONTEXT_SIDE_SECONDS
        ):
            raise ValueError(
                "lesson context requires at least 20 seconds before and after: "
                f"{lesson['lesson_id']}"
            )
        phases = [stage["phase"] for stage in lesson["stages"]]
        anchors = [stage["anchor_seconds"] for stage in lesson["stages"]]
        phase_positions = [PHASE_ORDER.index(phase) for phase in phases]
        if not (
            7 <= len(phases) <= 9
            and phases[0] == "preparation"
            and phases[-1] == "recovery"
            and phase_positions == sorted(phase_positions)
            and {"start", "contact_window", "follow_through"}.issubset(phases)
        ):
            raise ValueError(f"unexpected stage order: {lesson['lesson_id']}")
        if len(set(anchors)) != len(anchors) or anchors != sorted(anchors):
            raise ValueError(f"non-distinct ordered stage anchors: {lesson['lesson_id']}")
        if any(
            not (
                episode["start_seconds"] <= stage["start_seconds"]
                <= stage["anchor_seconds"]
                <= stage["end_seconds"]
                <= episode["end_seconds"]
            )
            for stage in lesson["stages"]
        ):
            raise ValueError(f"stage outside strict action boundary: {lesson['lesson_id']}")

    published_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [index_path, *sorted((lesson_root / "video-lessons").glob("*.yaml"))]
    ).lower()
    hits = [marker for marker in FORBIDDEN_PUBLISHED_MARKERS if marker in published_text]
    if hits:
        raise ValueError(f"private or internal material in staged package: {hits}")
    return {"staged_lesson_count": len(lessons), "staged_shard_count": len(set(item["shard"] for item in index["lessons"]))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--lesson-root", type=Path)
    args = parser.parse_args()
    repo = (args.repo or Path(__file__).resolve().parents[3]).resolve()
    result = validate_skill(repo)
    if args.lesson_root:
        result.update(validate_staged_lessons(repo, args.lesson_root.resolve()))
    print("LIU_HUI_SKILL_VALIDATION_OK", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
