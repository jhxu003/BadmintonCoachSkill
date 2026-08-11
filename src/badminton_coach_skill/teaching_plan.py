"""Structured-observation entry point for the three coach teaching Skills.

Raw learner video is intentionally outside this module. A human annotator or
an upstream video agent must first provide a bounded observation payload. This
module chooses a teaching *lens*, then one confirmed bottleneck and a small
practice queue. It never treats an ordinary monocular recording as proof of
contact, racket-face angle, force, grip pressure, joint rotation, 3D motion,
or opponent intent.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from .coach_media.video_lessons import (
    VideoLessonPackage,
    VideoLessonQuery,
    build_video_lesson_plan,
    load_video_lessons,
)
from .coach_registry import available_coach_actions, available_coaches, load_coach_knowledge
from .issue_matcher import match_diagnosis
from .student_plan_presenter import present_focus_item, validate_presentation_coverage


@lru_cache(maxsize=12)
def _load_plan_knowledge(coach_id: str, root_text: str) -> dict[str, Any]:
    """Cache immutable-on-disk Skill knowledge for focused-plan requests.

    The evidence maps are intentionally detailed and YAML parsing is expensive.
    A running service can safely reuse them; deployment changes restart the
    worker. Video lesson media is deliberately *not* cached here because its
    staging root can be changed independently.
    """
    return load_coach_knowledge(coach_id, Path(root_text))


def _required_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return dict(value)


def _lesson_status(lessons: tuple[VideoLessonPackage, ...]) -> str:
    return "available" if lessons else "no_reliable_video_lesson_package"


def _topic_candidates(
    *, issue: dict[str, Any], framework_id: str, knowledge: dict[str, Any]
) -> list[dict[str, Any]]:
    units_payload = knowledge.get("topic_teaching_units", {})
    if not isinstance(units_payload, dict):
        return []
    issue_id = str(issue.get("issue_id", ""))
    issue_sources = {str(item) for item in issue.get("source_ids", []) if item}
    candidates: list[dict[str, Any]] = []
    for raw_unit in units_payload.get("units", []):
        if not isinstance(raw_unit, dict):
            continue
        unit = dict(raw_unit)
        unit_rules = {str(item) for item in unit.get("rule_ids", []) if item}
        unit_sources = {str(item) for item in unit.get("source_ids", []) if item}
        unit_frameworks = {str(item) for item in unit.get("framework_ids", []) if item}
        if issue_id in unit_rules or issue_sources & unit_sources or framework_id in unit_frameworks:
            candidates.append(unit)
    return candidates


def _indexed_topic_ids(issue: dict[str, Any], knowledge: dict[str, Any]) -> set[str]:
    index = knowledge.get("source_topic_index", {})
    if not isinstance(index, dict):
        return set()
    issue_sources = {str(item) for item in issue.get("source_ids", []) if item}
    topic_ids: set[str] = set()
    for source in index.get("sources", []):
        if not isinstance(source, dict) or str(source.get("source_id", "")) not in issue_sources:
            continue
        for topic in source.get("topics", []):
            if isinstance(topic, dict) and topic.get("id"):
                topic_ids.add(str(topic["id"]))
    return topic_ids


def _select_topic_unit(
    *, issue: dict[str, Any], framework_id: str, knowledge: dict[str, Any]
) -> dict[str, Any] | None:
    """Select one defensible topic unit; title routes cannot fabricate media.

    An exact rule binding is stronger than a source-topic index.  Source IDs
    are often reused across a long coach episode (including match-context
    labels), so allowing an indexed source hit to outrank the diagnosed rule
    can route a visible swing fault to an unrelated tactics topic.  The unit
    must still be related to the same rule, source or framework, and
    non-fallback units win over broad title fallbacks. The stable topic id
    tie-break makes this reproducible rather than dependent on JSON file
    order.
    """
    candidates = _topic_candidates(issue=issue, framework_id=framework_id, knowledge=knowledge)
    if not candidates:
        return None
    indexed = _indexed_topic_ids(issue, knowledge)
    issue_sources = {str(item) for item in issue.get("source_ids", []) if item}
    issue_id = str(issue.get("issue_id", ""))

    def key(unit: dict[str, Any]) -> tuple[int, int, int, int, int]:
        topic_id = str(unit.get("topic_id", ""))
        unit_sources = {str(item) for item in unit.get("source_ids", []) if item}
        unit_rules = {str(item) for item in unit.get("rule_ids", []) if item}
        unit_frameworks = {str(item) for item in unit.get("framework_ids", []) if item}
        return (
            1 if issue_id in unit_rules else 0,
            1 if topic_id in indexed else 0,
            1 if not topic_id.endswith("-title-fallback") else 0,
            len(issue_sources & unit_sources),
            1 if framework_id in unit_frameworks else 0,
        )

    ranked = sorted(candidates, key=lambda unit: str(unit.get("topic_id", "")))
    return max(ranked, key=key)


def _is_publishable_topic_lesson(lesson: VideoLessonPackage, reviewed_ids: set[str]) -> bool:
    return bool(
        lesson.lesson_id in reviewed_ids
        and lesson.completeness == "complete_demonstration"
        and lesson.review_status == "agent_reviewed"
        and lesson.semantic_review_status == "agent_reviewed"
        and lesson.demonstrator_role == "coach"
        and lesson.example_polarity == "correct"
        and lesson.context_review_status == "agent_reviewed"
        and lesson.context_evidence
    )


def _select_topic_lessons(
    *, coach_id: str, root: Path, unit: dict[str, Any] | None, limit: int
) -> tuple[VideoLessonPackage, ...]:
    if not unit or str(unit.get("media_status", "")) != "teaching_ready":
        return ()
    # Course IDs describe knowledge coverage; only this explicit private
    # lesson allow-list can authorize learner-facing media.
    reviewed_ids = {str(item) for item in unit.get("reviewed_lesson_ids", []) if item}
    if not reviewed_ids:
        return ()
    lessons = [
        lesson
        for lesson in load_video_lessons(coach_id, root)
        if _is_publishable_topic_lesson(lesson, reviewed_ids)
    ]
    lessons.sort(key=lambda lesson: (lesson.source_id, lesson.episode_start_ms, lesson.lesson_id))
    return tuple(lessons[:limit])


def _focus_from_issues(
    *, issues: list[dict[str, Any]], framework_id: str, knowledge: dict[str, Any]
) -> dict[str, Any] | None:
    if not issues:
        return None
    now_issue = issues[0]
    now_unit = _select_topic_unit(issue=now_issue, framework_id=framework_id, knowledge=knowledge)
    now = present_focus_item(now_issue, now_unit)
    next_items: list[dict[str, Any]] = []
    drill_ids = {
        str(now.get("drill", {}).get("drill_id", ""))
        if isinstance(now.get("drill"), dict)
        else ""
    }
    for issue in issues[1:]:
        unit = _select_topic_unit(issue=issue, framework_id=framework_id, knowledge=knowledge)
        item = present_focus_item(issue, unit)
        drill = item.get("drill")
        drill_id = str(drill.get("drill_id", "")) if isinstance(drill, dict) else ""
        if drill_id and drill_id in drill_ids:
            continue
        if drill_id:
            drill_ids.add(drill_id)
        next_items.append(item)
        if len(next_items) == 2:
            break
    return {"now": now, "next": next_items}


def _retake_guidance(missing_evidence: list[str]) -> str:
    if not missing_evidence:
        return "当前没有匹配到已确认的瓶颈；请用同机位补拍完整准备、移动、击球后回收的连续过程。"
    return "当前证据不足，先补拍完整连续动作：准备、移动到位、可见击球窗、收拍与回位。缺失环节不作推断。"


def _single_coaching_plan(
    *,
    coach_id: str,
    player_profile: dict[str, Any],
    video_observation: dict[str, Any],
    root: Path,
    limit: int,
) -> dict[str, object]:
    action = str(video_observation.get("action", "")).strip()
    if action not in available_coach_actions(coach_id, root):
        raise ValueError(f"Unsupported action {action!r} for coach {coach_id!r}")

    knowledge = _load_plan_knowledge(coach_id, str(root.resolve()))
    validate_presentation_coverage(knowledge)
    diagnosis = match_diagnosis(player_profile, video_observation, knowledge)
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
        training_goal=str(player_profile.get("training_goal", "")),
        level=str(player_profile.get("level", "beginner")),
        framework_id=diagnostic_framework_id if framework_is_action_compatible else "",
        limit=limit,
    )
    # The existing catalog selector is used only for compatible framework
    # routes. Passing no lessons prevents action-level retrieval from leaking
    # an otherwise reviewed but wrong-topic lesson into this plan.
    route_plan = build_video_lesson_plan(lesson_query, knowledge, [])

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
    lesson_focus = _focus_from_issues(
        issues=issues, framework_id=diagnostic_framework_id, knowledge=knowledge
    )
    selected_unit = (
        lesson_focus.get("now", {}).get("topic_unit")
        if isinstance(lesson_focus, dict) and isinstance(lesson_focus.get("now"), dict)
        else None
    )
    # Use the raw unit only for exact reviewed-course filtering. The public
    # response carries the safe Chinese projection stored in lesson_focus.
    raw_unit = _select_topic_unit(
        issue=issues[0], framework_id=diagnostic_framework_id, knowledge=knowledge
    ) if issues else None
    lessons = _select_topic_lessons(coach_id=coach_id, root=root, unit=raw_unit, limit=limit)
    if not lessons and isinstance(lesson_focus, dict):
        now = lesson_focus.get("now")
        topic = now.get("topic_unit") if isinstance(now, dict) else None
        if isinstance(topic, dict) and topic.get("media_status") == "reviewed_media_available":
            # A catalog declaration alone is not enough: the exact reviewed
            # package must be present and publishable in this deployment.
            topic["media_status"] = "reviewed_media_unavailable"
            topic["media_notice_zh"] = "该主题列有审核绑定课程，但当前服务没有可用的完整示范；不拿其他动作或片段替代。"

    limitations = [
        item
        for item in route_plan.get("limitations", [])
        if item != "no_reliable_video_lesson_package"
    ]
    limitations.append("structured_observation_required_before_coach_diagnosis")
    if diagnostic_framework_id and not framework_is_action_compatible:
        limitations.append("diagnosis_framework_not_action_compatible_for_video_lesson_selection")
    if not issues:
        limitations.append("no_confirmed_coaching_issue_in_structured_observation")
    if not lessons:
        limitations.append("no_reliable_topic_bound_video_lesson")

    coach = knowledge.get("coach", {})
    return {
        "report_type": "structured_coaching_plan",
        "coach_id": coach_id,
        "coach_name": str(coach.get("display_name", coach_id)),
        "official_status": str(coach.get("official_status", "non-official research synthesis")),
        "notice": str(coach.get("diagnosis_notice", "")),
        "observation_mode": "structured_observation_from_human_or_video_agent",
        "query": dict(route_plan.get("query", {})),
        "diagnosis": diagnosis,
        # Retained as an audit trace for the caller. Learner UI uses only
        # lesson_focus, which never renders these raw source strings.
        "teaching_sequence": teaching_sequence,
        "lesson_focus": lesson_focus,
        "retake_guidance_zh": _retake_guidance(list(diagnosis.get("missing_evidence", []))) if not issues else None,
        "selected_topic_unit": selected_unit,
        "teaching_routes": list(route_plan.get("teaching_routes", [])),
        "video_lesson_status": _lesson_status(lessons),
        "limitations": list(dict.fromkeys(str(item) for item in limitations)),
        "_video_lessons": lessons,
    }


def _confidence_rank(value: object) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(str(value), 0)


def _lens_summary(plan: dict[str, object], *, selected: bool) -> dict[str, object]:
    focus = plan.get("lesson_focus")
    now = focus.get("now") if isinstance(focus, dict) else None
    topic = now.get("topic_unit") if isinstance(now, dict) else None
    if isinstance(now, dict):
        topic_name = str(topic.get("topic_name_zh", "")) if isinstance(topic, dict) else "当前动作链"
        reason = f"当前观察已确认“{now.get('title_zh', '一个可见环节')}”；可先用“{topic_name}”组织练习。"
    else:
        reason = "这个视角与当前动作兼容，但现有观察不足以确认先练什么；请先补拍连续过程。"
    return {
        "coach_id": str(plan.get("coach_id", "")),
        "coach_name": str(plan.get("coach_name", "")),
        "selected": selected,
        "confidence": str(plan.get("diagnosis", {}).get("confidence", "low")) if isinstance(plan.get("diagnosis"), dict) else "low",
        "first_issue_id": str(now.get("issue_id", "")) if isinstance(now, dict) else None,
        "reason_zh": reason,
    }


def _rank_auto_plan(plan: dict[str, object]) -> tuple[int, int, int, str]:
    diagnosis = plan.get("diagnosis", {})
    confidence = _confidence_rank(diagnosis.get("confidence")) if isinstance(diagnosis, dict) else 0
    focus = plan.get("lesson_focus")
    now = focus.get("now") if isinstance(focus, dict) else None
    has_issue = 1 if isinstance(now, dict) else 0
    has_topic = 1 if isinstance(now, dict) and now.get("topic_unit") else 0
    # Coach id is handled by the caller's stable ascending sort.
    return confidence, has_issue, has_topic, str(plan.get("coach_id", ""))


def generate_coaching_plan(
    *,
    coach_id: str,
    player_profile: dict[str, Any],
    video_observation: dict[str, Any],
    root: str | Path,
    limit: int = 2,
) -> dict[str, object]:
    """Generate a focused plan from explicit, structured observations.

    ``coach_id="auto"`` recommends a teaching lens among only the coaches
    compatible with the requested action. An explicit coach always wins; all
    compatible lenses are still returned as switch options. ``_video_lessons``
    keeps typed packages for the worker and must not be serialized directly.
    """
    project_root = Path(root)
    profile = _required_mapping(player_profile, "player_profile")
    observation = _required_mapping(video_observation, "video_observation")
    action = str(observation.get("action", "")).strip()
    if not coach_id or not action:
        raise ValueError("coach_id and video_observation.action are required")

    compatible_coaches = [
        candidate
        for candidate in available_coaches(project_root)
        if action in available_coach_actions(candidate, project_root)
    ]
    if not compatible_coaches:
        raise ValueError(f"Unsupported action {action!r} for all configured coaches")
    if coach_id != "auto" and coach_id not in compatible_coaches:
        raise ValueError(f"Unsupported coach_id or action combination: {coach_id!r}, {action!r}")

    candidate_plans = {
        candidate: _single_coaching_plan(
            coach_id=candidate,
            player_profile=profile,
            video_observation=observation,
            root=project_root,
            limit=limit,
        )
        for candidate in compatible_coaches
    }
    if coach_id == "auto":
        # Stable ascending coach id is the final tie-break; media availability
        # is intentionally absent from the score.
        selected_id = sorted(
            candidate_plans,
            key=lambda candidate: (
                -_rank_auto_plan(candidate_plans[candidate])[0],
                -_rank_auto_plan(candidate_plans[candidate])[1],
                -_rank_auto_plan(candidate_plans[candidate])[2],
                candidate,
            ),
        )[0]
        recommendation_mode = "auto_recommended_teaching_lens"
    else:
        selected_id = coach_id
        recommendation_mode = "explicit_coach_selection"

    selected = candidate_plans[selected_id]
    selected["requested_coach_id"] = coach_id
    selected["recommendation_mode"] = recommendation_mode
    selected["coach_lenses"] = [
        _lens_summary(candidate_plans[candidate], selected=candidate == selected_id)
        for candidate in sorted(candidate_plans)
    ]
    return selected


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
