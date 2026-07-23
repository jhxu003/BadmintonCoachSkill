from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ..video_evidence.contracts import PHASES, CoachReference, Phase


LEVELS = {"beginner", "intermediate", "advanced", "competitive"}

_PHASE_VISIBLE_FACTS: dict[Phase, frozenset[str]] = {
    "preparation": frozenset(
        {
            "wide_base",
            "staggered_stance",
            "racket_waist_to_shoulder",
            "racket_above_shoulder",
        }
    ),
    "start": frozenset({"wide_base", "staggered_stance", "single_leg_support"}),
    "arrival": frozenset(
        {"lunge", "staggered_stance", "single_leg_support", "airborne"}
    ),
    "top_elbow": frozenset({"arm_raised", "racket_above_shoulder"}),
    "contact_window": frozenset({"arm_raised", "arm_extended", "airborne"}),
    "follow_through": frozenset({"arm_extended", "torso_turned"}),
    "recovery": frozenset(
        {"wide_base", "staggered_stance", "single_leg_support", "neutral_standing"}
    ),
}

_LIMITATION_PENALTIES = {
    "unclear": 8,
    "camera_crop": 5,
    "multiple_people": 3,
    "racket_blurred": 3,
}


@dataclass(frozen=True)
class DemonstrationQuery:
    coach_id: str
    action: str
    phase: Phase
    training_goal: str = ""
    level: str = "beginner"
    framework_id: str = ""
    limit: int = 2

    def __post_init__(self) -> None:
        if not self.coach_id or not self.action:
            raise ValueError("coach_id and action are required")
        if self.phase not in PHASES:
            raise ValueError(f"Unsupported phase: {self.phase}")
        if self.level not in LEVELS:
            raise ValueError(f"Unsupported level: {self.level}")
        if self.limit < 1 or self.limit > 3:
            raise ValueError("limit must be between 1 and 3")


def available_actions(knowledge: dict[str, Any]) -> list[str]:
    actions = {
        str(action)
        for framework in knowledge.get("frameworks", [])
        for action in framework.get("applicable_actions", [])
        if action
    }
    return sorted(actions)


def _framework_score(
    framework: dict[str, Any], query: DemonstrationQuery
) -> tuple[int, int, str]:
    actions = tuple(str(item) for item in framework.get("applicable_actions", []))
    goals = tuple(str(item) for item in framework.get("training_goals", []))
    suitable = framework.get("suitable_for", {}) or {}
    suitable_levels = tuple(str(item) for item in suitable.get("level", []))
    avoid = framework.get("avoid_for", {}) or {}
    avoid_levels = tuple(str(item) for item in avoid.get("level", []))

    score = 0
    if query.framework_id and framework.get("framework_id") == query.framework_id:
        score += 1000
    if query.training_goal and query.training_goal in goals:
        score += 120
    if query.level in suitable_levels:
        score += 30
    if query.level in avoid_levels:
        score -= 500
    score += max(0, 24 - len(actions) * 2)
    confidence = str(framework.get("confidence", ""))
    score += {"source_backed": 8, "inferred": 4, "hypothesis": 0}.get(confidence, 0)
    return score, -len(actions), str(framework.get("framework_id", ""))


def select_teaching_frameworks(
    knowledge: dict[str, Any], query: DemonstrationQuery, limit: int = 3
) -> list[dict[str, object]]:
    candidates = [
        framework
        for framework in knowledge.get("frameworks", [])
        if query.action in framework.get("applicable_actions", [])
        and (
            not query.framework_id
            or framework.get("framework_id") == query.framework_id
        )
    ]
    selected = sorted(
        candidates, key=lambda item: _framework_score(item, query), reverse=True
    )[: max(0, limit)]
    return [
        {
            "framework_id": str(framework.get("framework_id", "")),
            "name": str(framework.get("name", "")),
            "summary": str(framework.get("summary", "")),
            "confidence": str(framework.get("confidence", "")),
            "applicable_actions": [
                str(item) for item in framework.get("applicable_actions", [])
            ],
            "training_goals": [
                str(item) for item in framework.get("training_goals", [])
            ],
            "source_ids": [str(item) for item in framework.get("source_ids", [])],
        }
        for framework in selected
    ]


def _reference_quality(reference: CoachReference, source_ids: set[str]) -> int:
    facts = set(reference.visible_facts)
    score = 0
    score += {
        "agent_reviewed": 100,
        "model_candidate": 0,
        "timestamp_only": -100,
    }[reference.review_status]
    if reference.source_id in source_ids:
        score += 60
    if facts & _PHASE_VISIBLE_FACTS[reference.phase]:
        score += 25
    if "racket_visible" in facts:
        score += 8
    if "person_visible" in facts:
        score += 5
    if "on_screen_text_absent" in facts:
        score += 3
    score += {"high": 8, "medium": 4, "low": 0}[reference.confidence]
    for limitation in reference.limitations:
        score -= _LIMITATION_PENALTIES.get(limitation, 0)
    return score


def select_demonstration_references(
    query: DemonstrationQuery,
    frameworks: Iterable[dict[str, object]],
    references: Iterable[CoachReference],
) -> list[CoachReference]:
    source_ids = {
        str(source_id)
        for framework in frameworks
        for source_id in framework.get("source_ids", [])
    }
    phase_facts = _PHASE_VISIBLE_FACTS[query.phase]
    candidates = [
        reference
        for reference in references
        if reference.coach_id == query.coach_id
        and reference.phase == query.phase
        and reference.availability in {"indexed", "cached"}
        and query.action in reference.actions
        and bool(set(reference.visible_facts) & phase_facts)
    ]
    reviewed_candidates = [
        reference
        for reference in candidates
        if reference.review_status == "agent_reviewed"
    ]
    if reviewed_candidates:
        candidates = reviewed_candidates
    ranked = sorted(
        candidates,
        key=lambda reference: (
            -_reference_quality(reference, source_ids),
            reference.source_id,
            reference.timestamp_ms,
            reference.reference_id,
        ),
    )
    selected: list[CoachReference] = []
    used_sources: set[str] = set()
    for reference in ranked:
        if reference.source_id in used_sources:
            continue
        selected.append(reference)
        used_sources.add(reference.source_id)
        if len(selected) >= query.limit:
            break
    return selected


def build_demonstration_plan(
    query: DemonstrationQuery,
    knowledge: dict[str, Any],
    references: Iterable[CoachReference],
) -> dict[str, object]:
    actions = available_actions(knowledge)
    if query.action not in actions:
        raise ValueError(
            f"Unsupported action {query.action!r}. Available actions: {', '.join(actions)}"
        )
    frameworks = select_teaching_frameworks(knowledge, query)
    if query.framework_id and not frameworks:
        raise ValueError(
            f"Framework {query.framework_id!r} does not support action {query.action!r}"
        )
    selected_references = select_demonstration_references(
        query, frameworks, references
    )
    limitations = [
        "non_official_public_source_research_synthesis",
        "reference_frame_supports_posture_comparison_not_complete_motion",
        "ordinary_monocular_video_does_not_prove_contact_racket_face_force_or_3d_kinematics",
    ]
    if not frameworks:
        limitations.append("no_action_compatible_teaching_framework")
    if not selected_references:
        limitations.append("no_reliable_same_phase_demonstration_frame")
    elif any(
        reference.review_status != "agent_reviewed"
        for reference in selected_references
    ):
        limitations.append("demonstration_timepoint_requires_manual_review")
    return {
        "query": {
            "coach_id": query.coach_id,
            "action": query.action,
            "phase": query.phase,
            "training_goal": query.training_goal,
            "level": query.level,
            "framework_id": query.framework_id,
        },
        "teaching_routes": frameworks,
        "references": selected_references,
        "limitations": limitations,
    }
