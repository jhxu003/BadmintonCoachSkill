from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a public-safe retry manifest from video batch summaries."
    )
    parser.add_argument("--base-manifest", required=True)
    parser.add_argument("--summary", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--retry-status",
        action="append",
        default=["skipped", "failed", "missing", "unreadable"],
        help="ASR status to retry. Can be passed more than once.",
    )
    parser.add_argument(
        "--include-returncode-failures",
        action="store_true",
        help="Retry jobs whose returncode is non-zero even if ASR status is not listed.",
    )
    return parser.parse_args()


def load_retry_records(
    summary_paths: list[str],
    retry_statuses: set[str],
    include_returncode_failures: bool,
) -> dict[str, dict[str, Any]]:
    retry: dict[str, dict[str, Any]] = {}
    for raw_path in summary_paths:
        path = ROOT / raw_path
        data = json.loads(path.read_text(encoding="utf-8"))
        for result in data.get("results", []):
            status = str(result.get("asr_status", "missing"))
            returncode = result.get("returncode")
            should_retry = status in retry_statuses
            if include_returncode_failures and returncode not in (0, None):
                should_retry = True
            if should_retry:
                retry[result["job_id"]] = {
                    "batch_id": data.get("batch_id"),
                    "asr_status": status,
                    "returncode": returncode,
                    "timed_out": bool(result.get("timed_out")),
                    "log_path": result.get("log_path", ""),
                }
    return retry


def main() -> None:
    args = parse_args()
    base = load_yaml(ROOT / args.base_manifest)
    retry_records = load_retry_records(
        args.summary,
        set(args.retry_status),
        args.include_returncode_failures,
    )
    jobs = []
    missing_from_base = sorted(set(retry_records))
    for job in base.get("jobs", []):
        record = retry_records.get(job["job_id"])
        if not record:
            continue
        updated = dict(job)
        updated["retry_reason"] = record
        updated["processing_status"] = "retry_pending"
        updated["review_status"] = "not_started"
        jobs.append(updated)
        missing_from_base.remove(job["job_id"])

    status_counts = Counter(record["asr_status"] for record in retry_records.values())
    retry_manifest = {
        "manifest_id": f"video_retry_manifest_{date.today().strftime('%Y%m%d')}",
        "created_at": date.today().isoformat(),
        "base_manifest": args.base_manifest,
        "source_summaries": args.summary,
        "summary": {
            "retry_jobs": len(jobs),
            "missing_from_base_manifest": len(missing_from_base),
            "retry_status_counts": dict(sorted(status_counts.items())),
        },
        "jobs": jobs,
    }
    write_yaml(ROOT / args.output, retry_manifest)
    print(f"wrote {args.output}")
    print(f"retry_jobs {len(jobs)}")
    print(f"missing_from_base_manifest {len(missing_from_base)}")
    for status, count in sorted(status_counts.items()):
        print(f"{status} {count}")


if __name__ == "__main__":
    main()
