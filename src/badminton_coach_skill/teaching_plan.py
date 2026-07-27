"""Structured-observation entry point for the three coach teaching Skills.

Raw learner video is intentionally outside this module.  A human annotator or
an upstream video agent must first provide the bounded observation payload;
this module then selects teaching order, drills, retests, and only verified
continuous coach-video lessons.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .coach_media.video_lessons import (
    VideoLessonPackage,
    VideoLessonQuery,
    build_video_lesson_plan,
    load_video_lessons,
)
from .coach_registry import load_coach_knowledge
from .issue_matcher import match_diagnosis


def _required_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return dict(value)


def _lesson_status(lessons: tuple[VideoLessonPackage, ...]) -> str:
    return "available" if lessons else "no_reliable_video_lesson_package"


def generate_coaching_plan(
    *,
    coach_id: str,
    player_profile: dict[str, Any],
    video_observation: dict[str, Any],
    root: str | Path,
    limit: int = 2,
) -> dict[str, object]:
    """Generate a teaching plan from explicit, structured observations.

    ``_video_lessons`` deliberately keeps typed lesson packages for the web
    worker.  Call :func:`serialize_coaching_plan` before returning the result
    through a CLI or a non-media API.
    """
    project_root = Path(root)
    profile = _required_mapping(player_profile, "player_profile")
    observation = _required_mapping(video_observation, "video_observation")
    action = str(observation.get("action", "")).strip()
    if not coach_id or not action:
        raise ValueError("coach_id and video_observation.action are required")

    knowledge = load_coach_knowledge(coach_id, project_root)
    diagnosis = match_diagnosis(profile, observation, knowledge)
    diagnostic_framework_id = str(diagnosis.get("primary_framework", ""))
    framework_is_action_compatible = any(
        str(framework.get("framework_id", "")) == diagnostic_framework_id
        and action in framework.get("applicable_actions", [])
        for framework in knowledge.get("frameworks", [])
        if isinstance(framework, dict)
    )
    lesson_query = VideoLessonQuery(
        coach_id=coach_id,
        action=action,
        training_goal=str(profile.get("training_goal", "")),
        level=str(profile.get("level", "beginner")),
        # Some tactical diagnosis frameworks intentionally use a wider action
        # label than the course catalog. Keep that diagnosis in the plan, but
        # do not make an incompatible framework id turn a reliable course-gap
        # response into an exception.
        framework_id=diagnostic_framework_id if framework_is_action_compatible else "",
        limit=limit,
    )
    lesson_plan = build_video_lesson_plan(
        lesson_query,
        knowledge,
        load_video_lessons(coach_id, project_root),
    )
    lessons = tuple(lesson_plan.pop("video_lessons", ()))
    if not all(isinstance(lesson, VideoLessonPackage) for lesson in lessons):
        raise RuntimeError("Video lesson catalog returned an invalid lesson package")

    issues = [item for item in diagnosis.get("issues", []) if isinstance(item, dict)]
    teaching_sequence = [
        {
            "rank": index,
            "issue_id": str(issue.get("issue_id", "")),
            "issue": str(issue.get("issue", "")),
            "correction_principle": str(issue.get("correction_principle", "")),
            "drills": list(issue.get("drills", [])),
            "retest_metrics": list(issue.get("retest_metrics", [])),
        }
        for index, issue in enumerate(issues, start=1)
    ]
    limitations = list(lesson_plan.get("limitations", []))
    limitations.append("structured_observation_required_before_coach_diagnosis")
    if diagnostic_framework_id and not framework_is_action_compatible:
        limitations.append(
            "diagnosis_framework_not_action_compatible_for_video_lesson_selection"
        )
    if not issues:
        limitations.append("no_confirmed_coaching_issue_in_structured_observation")

    coach = knowledge.get("coach", {})
    return {
        "report_type": "structured_coaching_plan",
        "coach_id": coach_id,
        "coach_name": str(coach.get("display_name", coach_id)),
        "official_status": str(coach.get("official_status", "non-official research synthesis")),
        "notice": str(coach.get("diagnosis_notice", "")),
        "observation_mode": "structured_observation_from_human_or_video_agent",
        "query": dict(lesson_plan.get("query", {})),
        "diagnosis": diagnosis,
        "teaching_sequence": teaching_sequence,
        "teaching_routes": list(lesson_plan.get("teaching_routes", [])),
        "video_lesson_status": _lesson_status(lessons),
        "limitations": list(dict.fromkeys(str(item) for item in limitations)),
        "_video_lessons": lessons,
    }


def serialize_coaching_plan(plan: dict[str, object]) -> dict[str, object]:
    """Return the public-safe, JSON-serializable shape of a teaching plan."""
    serialized = {key: value for key, value in plan.items() if key != "_video_lessons"}
    lessons = plan.get("_video_lessons", ())
    if not isinstance(lessons, tuple) or not all(
        isinstance(lesson, VideoLessonPackage) for lesson in lessons
    ):
        raise ValueError("Teaching plan has invalid video lesson packages")
    serialized["video_lessons"] = [lesson.to_dict() for lesson in lessons]
    return serialized


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a three-coach badminton teaching plan from a structured observation."
    )
    parser.add_argument("--input", required=True, type=Path, help="JSON with coach_id, player_profile, and video_observation.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--limit", type=int, default=2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input JSON must be an object")
    plan = generate_coaching_plan(
        coach_id=str(payload.get("coach_id", "")),
        player_profile=_required_mapping(payload.get("player_profile"), "player_profile"),
        video_observation=_required_mapping(
            payload.get("video_observation"), "video_observation"
        ),
        root=args.project_root,
        limit=args.limit,
    )
    print(json.dumps(serialize_coaching_plan(plan), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
