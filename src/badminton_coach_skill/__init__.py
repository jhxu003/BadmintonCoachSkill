"""Support code for BadmintonCoachSkill."""

from .issue_matcher import match_diagnosis
from .rubric_loader import load_skill_knowledge

__all__ = ["load_skill_knowledge", "match_diagnosis"]

