from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_full_system_examples_run():
    result = subprocess.run(
        [sys.executable, "examples/run_full_system_cases.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    expected = {
        "high_clear: late-arrival",
        "smash: low-elbow",
        "rear_footwork: late-arrival",
        "front_footwork: late-front-arrival",
        "backhand: backhand-low-contact",
        "serve_receive: receive-large-preparation",
        "doubles: doubles-watch-after-hit",
    }
    for line in expected:
        assert line in result.stdout
