from pathlib import Path
import importlib.util
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _load_integrity_module():
    path = ROOT / "scripts" / "check_source_integrity.py"
    spec = importlib.util.spec_from_file_location("check_source_integrity", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_source_integrity_script_passes():
    result = subprocess.run(
        [sys.executable, "scripts/check_source_integrity.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "source_integrity_ok" in result.stdout


def test_source_integrity_scans_complete_skill_references():
    module = _load_integrity_module()
    reference_dir = ROOT / "skills" / "liu-hui-badminton-coach" / "references"
    owners = {
        owner.split(":", 1)[0]
        for owner, _source_id in module._collect_rule_source_ids(reference_dir)
    }

    assert "student-profiles.yaml" in owners
    assert "stroke-taxonomy.yaml" in owners
    assert "training-plans.yaml" in owners
