from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts/build_private_coach_media_inventory.py"
)


def load_inventory_module():
    spec = importlib.util.spec_from_file_location("private_media_inventory_for_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_action_gate_rejection_is_terminal_without_claiming_context_review():
    module = load_inventory_module()
    episode = {
        "automatic_admission": False,
        "review_context_only": False,
        "semantic_assignment_status": "resolved",
    }

    assert not module.context_review_required(episode)
    assert module.action_gate_rejection_reasons(episode) == [
        "action_gate_not_automatic_admission"
    ]


def test_review_only_and_unresolved_candidates_stay_pending_for_context_audit():
    module = load_inventory_module()

    assert module.context_review_required(
        {
            "automatic_admission": False,
            "review_context_only": True,
            "semantic_assignment_status": "resolved",
        }
    )
    assert module.context_review_required(
        {
            "automatic_admission": False,
            "review_context_only": False,
            "semantic_assignment_status": "unresolved",
        }
    )
