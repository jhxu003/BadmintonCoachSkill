from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_source_integrity_script_passes():
    result = subprocess.run(
        [sys.executable, "scripts/check_source_integrity.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "source_integrity_ok" in result.stdout
