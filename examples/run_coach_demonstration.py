from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.coach_media.catalog import build_source_catalog
from badminton_coach_skill.coach_media.demonstrations import (
    DemonstrationQuery,
    build_demonstration_plan,
)
from badminton_coach_skill.coach_media.ingestion import ensure_demonstration_media
from badminton_coach_skill.coach_media.links import source_timestamp_url
from badminton_coach_skill.coach_registry import load_coach_knowledge


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query a coach teaching route and same-phase public-video demonstration."
    )
    parser.add_argument("--coach", default="liu-hui")
    parser.add_argument("--action", default="high_clear")
    parser.add_argument("--phase", default="top_elbow")
    parser.add_argument("--level", default="beginner")
    parser.add_argument("--training-goal", default="racket_frame")
    parser.add_argument("--framework-id", default="")
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument(
        "--materialize",
        action="store_true",
        help="Download selected public sources and extract private frame/clip cache. Run this on a worker or compute node.",
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=ROOT / ".runtime" / "coach-media",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    knowledge = load_coach_knowledge(args.coach, ROOT)
    catalog = build_source_catalog(args.coach, ROOT, knowledge=knowledge)
    plan = build_demonstration_plan(
        DemonstrationQuery(
            coach_id=args.coach,
            action=args.action,
            phase=args.phase,
            training_goal=args.training_goal,
            level=args.level,
            framework_id=args.framework_id,
            limit=args.limit,
        ),
        knowledge,
        catalog,
    )
    references = list(plan.pop("references"))
    if args.materialize:
        references = [
            ensure_demonstration_media(reference, args.cache_root)
            for reference in references
        ]
    payload = {
        "report_type": "coach_demonstration",
        **plan,
        "coach_references": [
            {
                **reference.to_dict(),
                "source_jump_url": source_timestamp_url(
                    reference.source_url, reference.timestamp_ms
                ),
            }
            for reference in references
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
