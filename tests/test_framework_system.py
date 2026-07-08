from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.issue_matcher import match_diagnosis
from badminton_coach_skill.rubric_loader import load_skill_knowledge


REFERENCES = ROOT / "skills" / "liu-hui-badminton-coach" / "references"


def _base_profile(training_goal: str) -> dict[str, object]:
    return {
        "level": "intermediate",
        "age_band": "adult",
        "strength": "average",
        "mobility": "normal",
        "coordination": "balanced",
        "injury_risk": [],
        "training_goal": training_goal,
        "dominant_hand": "right",
        "available_training_time": "20min_per_day",
    }


def _base_observation(action: str) -> dict[str, object]:
    return {
        "action": action,
        "camera_view": "rear_side",
        "fps_quality": "good",
        "phase_observations": {},
        "contact_point": "front_high",
        "elbow_height_before_hit": "near_shoulder",
        "wrist_elbow_sequence": "elbow_before_wrist",
        "hip_shoulder_sequence": "hip_before_arm",
        "racket_side_structure": "stable",
        "follow_through": "complete",
        "footwork_observations": {"arrival_timing": "on_time", "recovery": "normal"},
        "missing_observations": [],
        "keyframes": [{"label": "contact", "time_ms": 1000}],
    }


def test_runtime_framework_library_covers_full_liu_hui_system():
    frameworks = yaml.safe_load((REFERENCES / "frameworks.yaml").read_text("utf-8"))
    framework_ids = {framework["framework_id"] for framework in frameworks}

    required = {
        "learner-fit-sequence-frame",
        "match-transfer-frame",
        "mobility-safe-frame",
        "stable-overhead-frame",
        "high-clear-base-power-frame",
        "high-clear-action-change-frame",
        "contact-window-frame",
        "top-elbow-frame",
        "static-lock-racket-frame",
        "standard-ready-racket-frame",
        "racket-face-control-frame",
        "wrist-position-frame",
        "whip-release-frame",
        "internal-rotation-frame",
        "grip-finger-power-frame",
        "hip-trunk-power-frame",
        "concentrated-power-frame",
        "flash-power-frame",
        "relaxed-follow-through-frame",
        "tension-observation-frame",
        "left-side-balance-frame",
        "shoulder-extension-frame",
        "heavy-smash-frame",
        "fast-smash-frame",
        "simple-smash-sequence-frame",
        "smash-angle-frame",
        "bawang-smash-frame",
        "low-loaded-smash-frame",
        "point-smash-frame",
        "jump-smash-airtime-frame",
        "slice-smash-frame",
        "passive-rear-transition-frame",
        "half-side-attack-frame",
        "rear-court-overhead-frame",
        "slice-drop-slide-frame",
        "light-drop-frame",
        "heavy-slice-drop-frame",
        "deceptive-drop-frame",
        "cut-shot-frame",
        "start-position-recovery-frame",
        "lazy-legs-recovery-frame",
        "front-court-arrival-frame",
        "elastic-footwork-frame",
        "backhand-passive-frame",
        "backhand-corner-choice-frame",
        "backhand-whip-frame",
        "body-jammed-drive-frame",
        "push-drive-power-frame",
        "receive-smash-defense-frame",
        "serve-high-clear-frame",
        "doubles-rear-continuity-frame",
        "doubles-fast-exchange-frame",
        "singles-tactical-core-frame",
        "tactical-observation-frame",
        "compact-frontcourt-receive-frame",
    }

    assert len(frameworks) >= 45
    assert required.issubset(framework_ids)
    for framework in frameworks:
        assert framework["source_ids"]
        assert framework["priority"]
        assert framework["confidence"] in {"source_backed", "inferred", "hypothesis"}


def test_framework_selector_reaches_specific_liu_hui_frameworks():
    knowledge = load_skill_knowledge(REFERENCES)
    cases = [
        ("bawang_smash", "smash", {}, "bawang-smash-frame"),
        ("backhand_defense", "backhand", {}, "backhand-passive-frame"),
        ("doubles_positioning", "doubles", {}, "doubles-rear-continuity-frame"),
        ("contact_window", "high_clear", {}, "contact-window-frame"),
        ("grip_power", "high_clear", {}, "grip-finger-power-frame"),
        ("smash_angle", "smash", {}, "smash-angle-frame"),
        (
            "slice_drop",
            "smash",
            {"phase_observations": {"shot_intent": "slice_drop"}},
            "slice-drop-slide-frame",
        ),
        (
            "light_drop",
            "drop",
            {"phase_observations": {"shot_intent": "light_drop"}},
            "light-drop-frame",
        ),
        (
            "body_jammed_drive",
            "drive",
            {"phase_observations": {"pressure_state": "body_jammed"}},
            "body-jammed-drive-frame",
        ),
        (
            "serve_receive_stability",
            "serve_receive",
            {"phase_observations": {"preparation_size": "large"}},
            "compact-frontcourt-receive-frame",
        ),
    ]

    for training_goal, action, observation_updates, expected in cases:
        observation = _base_observation(action)
        observation.update(observation_updates)
        diagnosis = match_diagnosis(
            _base_profile(training_goal),
            observation,
            knowledge,
        )

        assert diagnosis["primary_framework"] == expected
