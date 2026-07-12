"""Support code for BadmintonCoachSkill."""

from .issue_matcher import match_diagnosis
from .rubric_loader import load_skill_knowledge

__all__ = ["load_skill_knowledge", "match_diagnosis"]
from .coach_registry import available_coaches, load_coach_config, load_coach_knowledge

__all__ = ["available_coaches", "load_coach_config", "load_coach_knowledge"]
