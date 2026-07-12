from __future__ import annotations

from typing import Any


MISSING_VALUES = {None, "", "missing", "unknown", "not_visible"}
ACTION_TOPIC_ALIASES = {
    "rear_footwork": "footwork",
    "front_footwork": "footwork",
}


def _get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _is_missing(observation: dict[str, Any], path: str) -> bool:
    explicit = set(observation.get("missing_observations", []))
    if path in explicit:
        return True
    root = path.split(".", 1)[0]
    if root in explicit:
        return True
    return _get_path(observation, path) in MISSING_VALUES


def _condition_matches(observation: dict[str, Any], condition: dict[str, Any]) -> bool:
    actual = _get_path(observation, condition["path"])
    if "equals" in condition:
        return actual == condition["equals"]
    if "in" in condition:
        return actual in set(condition["in"])
    raise ValueError(f"Unsupported condition: {condition}")


def _framework_score(
    profile: dict[str, Any],
    observation: dict[str, Any],
    framework: dict[str, Any],
) -> int:
    suitable = framework.get("suitable_for", {})
    avoid = framework.get("avoid_for", {})
    if not isinstance(avoid, dict):
        avoid = {}
    score = 0

    for field, accepted in suitable.items():
        value = profile.get(field)
        if isinstance(value, list):
            score += len(set(value) & set(accepted))
        elif value in accepted:
            score += 1

    for field, rejected in avoid.items():
        value = profile.get(field)
        if isinstance(value, list) and set(value) & set(rejected):
            score -= 3
        elif value in rejected:
            score -= 3

    action = observation.get("action")
    applicable_actions = set(framework.get("applicable_actions", []))
    if applicable_actions:
        if action in applicable_actions:
            score += 4
            score += max(0, 4 - len(applicable_actions))
        else:
            score -= 2

    training_goal = profile.get("training_goal")
    training_goals = set(framework.get("training_goals", []))
    if training_goals and training_goal in training_goals:
        score += 8
        score += max(0, 4 - len(training_goals))

    for trigger in framework.get("observation_triggers", []):
        if _condition_matches(observation, trigger):
            score += int(trigger.get("weight", 4))

    return score


def _select_framework(
    profile: dict[str, Any], observation: dict[str, Any], frameworks: list[dict[str, Any]]
) -> dict[str, Any]:
    return max(
        frameworks,
        key=lambda item: (
            _framework_score(profile, observation, item),
            -frameworks.index(item),
        ),
    )


def _select_corpus_evidence(
    framework_id: str,
    action: str,
    sources: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    action_topics = {action, ACTION_TOPIC_ALIASES.get(action, action)}
    candidates: list[tuple[int, dict[str, Any]]] = []
    for source in sources:
        if framework_id not in source.get("framework_ids", []):
            continue
        topics = set(source.get("topic_tags", []))
        score = 100 + 20 * len(action_topics & topics)
        score += 5 if source.get("temporal_sequence_refs") else 0
        score += min(len(source.get("visual_timestamp_refs", [])), 3)
        candidates.append((score, source))
    candidates.sort(
        key=lambda item: (-item[0], str(item[1].get("source_id", "")))
    )
    selected: list[dict[str, Any]] = []
    for _, source in candidates[: max(limit, 0)]:
        windows = source.get("asr_timestamp_refs", [])
        relevant_windows = [
            window
            for window in windows
            if action_topics & set(window.get("topic_tags", []))
        ]
        window = (relevant_windows or windows or [None])[0]
        visual_timestamps = list(source.get("visual_timestamp_refs", []))
        if window:
            in_window = [
                timestamp
                for timestamp in visual_timestamps
                if float(window["start_seconds"])
                <= float(timestamp)
                <= float(window["end_seconds"])
            ]
            visual_timestamps = in_window or visual_timestamps
        visual_observations = list(source.get("visual_observation_refs", []))
        if window:
            in_window_observations = [
                observation
                for observation in visual_observations
                if float(window["start_seconds"])
                <= float(observation.get("timestamp_seconds", -1))
                <= float(window["end_seconds"])
            ]
            visual_observations = in_window_observations or visual_observations
        sequences = [
            sequence
            for sequence in source.get("temporal_sequence_refs", [])
            if action_topics & set(sequence.get("topic_tags", []))
        ]
        if not sequences:
            sequences = list(source.get("temporal_sequence_refs", []))
        selected.append(
            {
                "source_id": source.get("source_id"),
                "title": source.get("title"),
                "framework_id": framework_id,
                "asr_window": window,
                "visual_timestamps": visual_timestamps[:3],
                "visual_observations": visual_observations[:3],
                "temporal_sequences": sequences[:1],
                "evidence_levels": source.get("evidence_levels", []),
                "confidence_boundary": source.get("confidence_boundary", ""),
            }
        )
    return selected


def _rule_applies_to_action(rule: dict[str, Any], action: str) -> bool:
    return action in set(rule.get("applicable_actions", []))


def _collect_rule_match(
    rule: dict[str, Any], observation: dict[str, Any], drill_map: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any] | None, list[str]]:
    evidence = [
        condition["label"]
        for condition in rule.get("observable_evidence", [])
        if not _is_missing(observation, condition["path"])
        and _condition_matches(observation, condition)
    ]
    missing = [
        required
        for required in rule.get("required_observations", [])
        if _is_missing(observation, required)
    ]
    if missing:
        return None, missing if evidence else []

    if len(evidence) < int(rule.get("min_evidence_count", 1)):
        return None, []

    drills = [drill_map[drill_id] for drill_id in rule.get("drills", []) if drill_id in drill_map]
    issue = {
        "issue_id": rule["rule_id"],
        "issue": rule["issue"],
        "category": rule["category"],
        "priority": rule["priority"],
        "evidence": evidence,
        "likely_effect": rule.get("likely_effect", []),
        "correction_principle": rule.get("correction_principle", ""),
        "drills": drills,
        "retest_metrics": rule.get("retest_metrics", []),
        "source_ids": rule.get("source_ids", []),
        "confidence": rule.get("confidence", "hypothesis"),
    }
    return issue, []


def match_diagnosis(
    player_profile: dict[str, Any],
    video_observation: dict[str, Any],
    knowledge: dict[str, Any],
) -> dict[str, Any]:
    """Match profile and video observations against the skill's rubric."""
    framework = _select_framework(
        player_profile, video_observation, knowledge["frameworks"]
    )
    missing_evidence: list[str] = list(video_observation.get("missing_observations", []))
    issues: list[dict[str, Any]] = []

    for rule in knowledge["rules"]:
        if not _rule_applies_to_action(rule, video_observation.get("action", "unknown")):
            continue
        issue, missing = _collect_rule_match(
            rule, video_observation, knowledge["drill_map"]
        )
        missing_evidence.extend(item for item in missing if item not in missing_evidence)
        if issue:
            issues.append(issue)

    framework_priority = {
        issue_id: index
        for index, issue_id in enumerate(framework.get("priority", []))
    }
    issues.sort(
        key=lambda issue: (
            issue["priority"],
            framework_priority.get(issue["issue_id"], 999),
            issue["issue_id"],
        )
    )

    all_evidence = [
        evidence for issue in issues for evidence in issue.get("evidence", [])
    ]
    retest_metrics = []
    training_plan = []
    for issue in issues:
        retest_metrics.extend(issue.get("retest_metrics", []))
        if issue.get("drills"):
            training_plan.append(
                {
                    "issue_id": issue["issue_id"],
                    "drill_id": issue["drills"][0]["drill_id"],
                    "drill_name": issue["drills"][0]["name"],
                    "dosage": issue["drills"][0]["dosage"],
                }
            )

    coach = knowledge.get("coach", {})
    safety_notes = [
        str(
            coach.get(
                "diagnosis_notice",
                "This is a non-official research badminton diagnosis.",
            )
        )
    ]
    if player_profile.get("injury_risk"):
        safety_notes.append(
            "Pain or injury risk is present; reduce intensity and consult a qualified professional if symptoms persist."
        )

    confidence = "high" if issues and not missing_evidence else "medium" if issues else "low"
    corpus_sources = knowledge.get("multimodal_evidence", {}).get("sources", [])
    corpus_evidence = _select_corpus_evidence(
        framework["framework_id"],
        str(video_observation.get("action", "unknown")),
        corpus_sources,
    )

    return {
        "coach_id": coach.get("coach_id", "custom"),
        "coach_name": coach.get("display_name", "Custom"),
        "primary_framework": framework["framework_id"],
        "issues": issues,
        "evidence": all_evidence,
        "confidence": confidence,
        "priority_order": [issue["issue_id"] for issue in issues],
        "training_plan": training_plan,
        "retest_metrics": list(dict.fromkeys(retest_metrics)),
        "missing_evidence": list(dict.fromkeys(missing_evidence)),
        "safety_notes": safety_notes,
        "corpus_evidence": corpus_evidence,
    }
