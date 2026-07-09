from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import write_evidence_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild the public-safe video evidence index from evidence YAML files."
    )
    parser.add_argument(
        "--evidence-dir",
        default="data/corpus/video-evidence",
        help="Directory containing public timestamp-evidence YAML files.",
    )
    parser.add_argument(
        "--output",
        default="data/corpus/video-evidence-index.tsv",
        help="TSV index path to write.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evidence_dir = ROOT / args.evidence_dir
    evidence_files = sorted(evidence_dir.glob("*.yaml"))
    write_evidence_index(ROOT / args.output, evidence_files)
    print(f"indexed {len(evidence_files)} evidence files")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
