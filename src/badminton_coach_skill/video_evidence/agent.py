"""Bounded orchestration contracts for learner-video coaching agents.

The visual models in this module never diagnose a learner in free text. They
only propose action windows and fill a whitelisted observation payload. The
existing deterministic Coach Skill remains the only component that turns an
accepted observation into a teaching plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .contracts import ActionPackageSegment, FrameRef
from .worker import VideoEvidenceResult


ROUTABLE_ACTIONS = frozenset(
    {
        "high_clear",
        "smash",
        "drop",
        "drive",
        "net",
        "rear_footwork",
        "front_footwork",
        "backhand",
        "serve_receive",
        "doubles",
        "match_transfer",
    }
)
MISSING_VALUES = frozenset({"", "unknown", "not_visible", "missing", None})
UNSAFE_VISUAL_PATH_PARTS = frozenset(
    {
        "contact",
        "racket_face",
        "grip",
        "force",
        "intent",
        "decision",
        "tactical",
        "opponent",
        "internal_rotation",
        "3d",
    }
)
# These are conservative two-dimensional proxies that can be assessed across
# a continuous, full-body sequence.  The wider coach rubrics also include
# declarations about pain, equipment, tactics, pressure, grip, contact, and
# internal mechanics; they remain useful to the deterministic Skill but are
# not an input vocabulary for a monocular VLM.
VISIBLE_AGENT_PROXY_PATHS = frozenset(
    {
        "elbow_height_before_hit",
        "racket_side_structure",
        "follow_through",
        "footwork_observations.arrival",
        "footwork_observations.confirmation_step",
        "footwork_observations.first_step",
        "footwork_observations.landing",
        "footwork_observations.rear_turn",
        "footwork_observations.recovery",
        "phase_observations.arm_path",
        "phase_observations.deceleration",
        "phase_observations.elbow_track",
        "phase_observations.landing_recovery",
        "phase_observations.preparation_time",
        "phase_observations.swing_path",
    }
)
REQUIRED_ROOT_FIELDS = (
    "contact_point",
    "elbow_height_before_hit",
    "wrist_elbow_sequence",
    "hip_shoulder_sequence",
    "racket_side_structure",
    "follow_through",
)


@dataclass(frozen=True)
class ActionRoute:
    """A low-cost routing proposal; not yet eligible for coaching."""

    unit_id: str
    action: str
    start_ms: int
    end_ms: int
    confidence: float
    decision: str = "candidate"
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not self.unit_id
            or Path(self.unit_id).name != self.unit_id
            or self.unit_id in {".", ".."}
            or self.action not in ROUTABLE_ACTIONS
        ):
            raise ValueError("Action routes require a supported action and stable unit_id")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("Action routes require a positive ordered time window")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Action-route confidence must be within [0, 1]")
        if self.decision not in {"candidate", "not_action", "unclear"}:
            raise ValueError("Action-route decision must be candidate, not_action, or unclear")

    def to_dict(self) -> dict[str, object]:
        return {
            "segment_id": self.unit_id,
            "action": self.action,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "routing_confidence": self.confidence,
            "decision": self.decision,
            "reasons": list(self.reasons),
        }


class ActionRouter(Protocol):
    def route(self, video_path: Path, output_dir: Path) -> tuple[ActionRoute, ...]:
        """Return non-overlapping candidate routes from a normalized upload."""

    def close(self) -> None:
        """Release optional GPU model state before another tier is loaded."""


class SegmentObserver(Protocol):
    def observe(
        self,
        *,
        action: str,
        image_paths: tuple[Path, ...],
        base_observation: dict[str, object],
        allowed_values: dict[str, tuple[str, ...]],
    ) -> dict[str, object]:
        """Return a JSON-like observation, never a diagnosis or free-text plan."""

    def close(self) -> None:
        """Release optional GPU model state before another tier is loaded."""


class DisabledActionRouter:
    """Fail closed when the local routing model has not been installed."""

    def route(self, video_path: Path, output_dir: Path) -> tuple[ActionRoute, ...]:
        return ()

    def close(self) -> None:
        return None


class DisabledSegmentObserver:
    """Fail closed when the local observation model has not been installed."""

    def observe(
        self,
        *,
        action: str,
        image_paths: tuple[Path, ...],
        base_observation: dict[str, object],
        allowed_values: dict[str, tuple[str, ...]],
    ) -> dict[str, object]:
        return {"confidence": "low", "limitations": ["segment_observer_not_configured"]}

    def close(self) -> None:
        return None


@dataclass(frozen=True)
class ObservationValidation:
    observation: dict[str, object]
    accepted: bool
    confidence: str
    rejection_reasons: tuple[str, ...]


def _path_get(payload: dict[str, object], path: str) -> object:
    current: object = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _path_set(payload: dict[str, object], path: str, value: object) -> None:
    parts = path.split(".")
    current: dict[str, object] = payload
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def _safe_visual_path(path: str) -> bool:
    """Keep monocular-video observations inside the published evidence boundary."""
    return not any(part in path.lower() for part in UNSAFE_VISUAL_PATH_PARTS)


def _rule_value_whitelist(knowledge_sets: list[dict[str, Any]], action: str) -> dict[str, set[str]]:
    allowed: dict[str, set[str]] = {}
    for knowledge in knowledge_sets:
        for rule in knowledge.get("rules", []):
            if not isinstance(rule, dict) or action not in set(rule.get("applicable_actions", [])):
                continue
            for condition in rule.get("observable_evidence", []):
                if not isinstance(condition, dict) or not isinstance(condition.get("path"), str):
                    continue
                path = str(condition["path"])
                if not _safe_visual_path(path):
                    continue
                values = allowed.setdefault(path, set())
                if isinstance(condition.get("equals"), str):
                    values.add(str(condition["equals"]))
                for value in condition.get("in", []):
                    if isinstance(value, str):
                        values.add(value)
    return allowed


def observation_value_whitelist(
    knowledge_sets: list[dict[str, Any]], action: str
) -> dict[str, tuple[str, ...]]:
    """Expose a stable prompt vocabulary derived only from registered rules."""
    return {
        path: tuple(sorted(values))
        for path, values in sorted(_rule_value_whitelist(knowledge_sets, action).items())
        if values and path in VISIBLE_AGENT_PROXY_PATHS
    }


def _required_paths(knowledge_sets: list[dict[str, Any]], action: str) -> set[str]:
    paths = set(REQUIRED_ROOT_FIELDS)
    for knowledge in knowledge_sets:
        for rule in knowledge.get("rules", []):
            if isinstance(rule, dict) and action in set(rule.get("applicable_actions", [])):
                paths.update(
                    str(path)
                    for path in rule.get("required_observations", [])
                    if isinstance(path, str)
                )
    return paths


def select_eligible_routes(
    routes: tuple[ActionRoute, ...], *, minimum_confidence: float, maximum_units: int
) -> tuple[ActionRoute, ...]:
    """Make routing conservative even when an injected adapter is malformed.

    The VLM adapter already removes overlaps, but this boundary is deliberately
    repeated at orchestration time so a future provider cannot create two
    teaching plans from the same seconds of learner footage.
    """
    eligible: list[ActionRoute] = []
    for route in sorted(routes, key=lambda item: (-item.confidence, item.start_ms, item.unit_id)):
        if route.decision != "candidate" or route.confidence < minimum_confidence:
            continue
        if any(route.unit_id == kept.unit_id for kept in eligible):
            continue
        if any(
            not (route.end_ms <= kept.start_ms or route.start_ms >= kept.end_ms)
            for kept in eligible
        ):
            continue
        eligible.append(route)
        if len(eligible) == max(1, maximum_units):
            break
    return tuple(sorted(eligible, key=lambda item: (item.start_ms, item.unit_id)))


def validate_agent_observation(
    *,
    action: str,
    raw_observation: dict[str, object],
    base_observation: dict[str, object],
    knowledge_sets: list[dict[str, Any]],
    minimum_confidence: str = "high",
) -> ObservationValidation:
    """Allow only rubric-backed visual fields and make missing evidence explicit."""
    whitelist = _rule_value_whitelist(knowledge_sets, action)
    required_paths = _required_paths(knowledge_sets, action)
    observation: dict[str, object] = {
        "action": action,
        "camera_view": str(base_observation.get("camera_view", "unknown")),
        "fps_quality": str(base_observation.get("fps_quality", "derived_from_video_pipeline")),
        "phase_observations": {},
        "contact_point": "unknown",
        "elbow_height_before_hit": "unknown",
        "wrist_elbow_sequence": "unknown",
        "hip_shoulder_sequence": "unknown",
        "racket_side_structure": "unknown",
        "follow_through": "unknown",
        "footwork_observations": {},
        "keyframes": list(base_observation.get("keyframes", [])),
    }
    # Pose-derived values remain acceptable only when they are also in the
    # deterministic rubric vocabulary. Everything else is ignored.
    merged_sources = (base_observation, raw_observation)
    for path, values in whitelist.items():
        for source in merged_sources:
            candidate = _path_get(source, path)
            if isinstance(candidate, str) and candidate in values:
                _path_set(observation, path, candidate)
    for root_field in REQUIRED_ROOT_FIELDS:
        if root_field not in whitelist:
            candidate = raw_observation.get(root_field, base_observation.get(root_field))
            if isinstance(candidate, str) and candidate in {"unknown", "not_visible", "missing"}:
                observation[root_field] = candidate

    missing = {
        str(item)
        for item in base_observation.get("missing_observations", [])
        if isinstance(item, str)
    }
    for path in sorted(required_paths):
        if _path_get(observation, path) in MISSING_VALUES:
            missing.add(path)
    observation["missing_observations"] = sorted(missing)

    raw_confidence = str(raw_observation.get("confidence", "low"))
    confidence = raw_confidence if raw_confidence in {"low", "medium", "high"} else "low"
    reasons: list[str] = []
    if confidence != minimum_confidence:
        reasons.append("segment_observation_confidence_below_high")
    if not observation["keyframes"]:
        reasons.append("no_visible_phase_keyframes")
    return ObservationValidation(
        observation=observation,
        accepted=not reasons,
        confidence=confidence,
        rejection_reasons=tuple(reasons),
    )


def has_complete_action_package(result: VideoEvidenceResult) -> tuple[bool, tuple[str, ...]]:
    expected = {
        "preparation",
        "start",
        "arrival",
        "top_elbow",
        "contact_window",
        "follow_through",
        "recovery",
    }
    present = {segment.phase for segment in result.action_package if segment.media_key}
    missing = tuple(sorted(expected.difference(present)))
    return not missing, tuple(f"action_package.{phase}" for phase in missing)


def prefix_evidence(
    result: VideoEvidenceResult, unit_id: str, relative_root: Path
) -> VideoEvidenceResult:
    """Make independently processed unit media and ids safe to persist together."""
    from dataclasses import replace

    def media_key(value: str) -> str:
        return str(relative_root / value) if value else ""

    frame_map: dict[str, str] = {}
    frames: list[FrameRef] = []
    for frame in result.frames:
        frame_id = f"{unit_id}-{frame.frame_id}"
        frame_map[frame.frame_id] = frame_id
        frames.append(replace(frame, frame_id=frame_id, media_key=media_key(frame.media_key)))
    packages = tuple(
        replace(
            segment,
            segment_id=f"{unit_id}-{segment.segment_id}",
            media_key=media_key(segment.media_key),
        )
        for segment in result.action_package
    )
    observation = dict(result.observation)
    keys: list[dict[str, object]] = []
    for item in observation.get("keyframes", []):
        if not isinstance(item, dict):
            continue
        copied = dict(item)
        source_id = copied.get("frame_id")
        if isinstance(source_id, str) and source_id in frame_map:
            copied["frame_id"] = frame_map[source_id]
        source_key = copied.get("media_key")
        if isinstance(source_key, str):
            copied["media_key"] = media_key(source_key)
        keys.append(copied)
    observation["keyframes"] = keys
    return VideoEvidenceResult(
        observation=observation,
        frames=tuple(frames),
        candidates=result.candidates,
        action_package=packages,
        multiplayer=result.multiplayer,
    )


@dataclass(frozen=True)
class AgentUnitEvidence:
    route: ActionRoute
    status: str
    routing_reasons: tuple[str, ...]
    observation: dict[str, object] | None = None
    observation_confidence: str = "low"
    frames: tuple[FrameRef, ...] = ()
    action_package: tuple[ActionPackageSegment, ...] = ()
    coaching_plan: dict[str, object] | None = None

    def public_payload(self) -> dict[str, object]:
        payload = self.route.to_dict()
        payload.update(
            {
                "status": self.status,
                "reasons": list(self.routing_reasons),
                "observation_confidence": self.observation_confidence,
                "missing_observations": (
                    list(self.observation.get("missing_observations", []))
                    if isinstance(self.observation, dict)
                    else []
                ),
            }
        )
        return payload
