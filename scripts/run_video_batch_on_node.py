from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_evidence_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run video content parsing jobs sequentially on a compute node. "
            "Each job gets its own timeout and log so one bad source does not block the batch."
        )
    )
    parser.add_argument("--manifest", default="data/corpus/video-pilot-manifest.yaml")
    parser.add_argument("--job-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--stages", default="audio,asr,evidence")
    parser.add_argument("--asr-model", default="small")
    parser.add_argument("--asr-device", default="cuda")
    parser.add_argument("--asr-compute-type", default="float16")
    parser.add_argument("--asr-audio-seconds", type=int, default=180)
    parser.add_argument("--per-job-timeout", type=int, default=900)
    parser.add_argument("--metadata-timeout", type=int, default=120)
    parser.add_argument("--audio-timeout", type=int, default=240)
    parser.add_argument("--download-timeout", type=int, default=600)
    parser.add_argument("--yt-dlp-socket-timeout", type=int, default=30)
    parser.add_argument("--yt-dlp-retries", type=int, default=2)
    parser.add_argument(
        "--node-local-private-root",
        default="",
        help=(
            "Optional compute-node-local private root, for example /tmp/jhxu-video-corpus. "
            "Large audio/video intermediates stay there; small JSON artifacts are copied back."
        ),
    )
    parser.add_argument(
        "--no-copy-back-json",
        action="store_true",
        help="Do not copy small private JSON/log artifacts back to manifest private paths.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to use for child pipeline runs. Defaults to current interpreter.",
    )
    parser.add_argument(
        "--cuda-visible-devices",
        default=os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        help="GPU ids for child jobs. Empty keeps the inherited setting.",
    )
    parser.add_argument(
        "--hf-home",
        default=os.environ.get("HF_HOME", ""),
        help="Hugging Face cache for child jobs. Empty keeps the inherited setting.",
    )
    parser.add_argument(
        "--hf-online",
        action="store_true",
        help="Allow Hugging Face network access. Default is offline to avoid stalled node jobs.",
    )
    parser.add_argument(
        "--batch-id",
        default="",
        help="Stable batch id. Defaults to UTC timestamp.",
    )
    parser.add_argument(
        "--log-dir",
        default="data/raw-private/video-corpus/batch-runs",
        help="Private log directory. Must remain git-ignored.",
    )
    parser.add_argument(
        "--evidence-index",
        default="data/corpus/video-evidence-index.tsv",
    )
    parser.add_argument(
        "--skip-ok-asr",
        action="store_true",
        help="Skip jobs whose private ASR JSON already has status ok.",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_jobs(args: argparse.Namespace) -> list[dict[str, Any]]:
    manifest = load_yaml(ROOT / args.manifest)
    jobs = list(manifest.get("jobs", []))
    if args.job_id:
        requested = set(args.job_id)
        jobs = [job for job in jobs if job["job_id"] in requested]
    if args.offset:
        jobs = jobs[args.offset :]
    if args.limit:
        jobs = jobs[: args.limit]
    return jobs


def asr_already_ok(job: dict[str, Any]) -> bool:
    path = ROOT / job["private_paths"]["asr_json"]
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return data.get("status") == "ok"


def child_env(args: argparse.Namespace) -> dict[str, str]:
    env = os.environ.copy()
    if args.cuda_visible_devices:
        env["CUDA_VISIBLE_DEVICES"] = args.cuda_visible_devices
    if args.hf_home:
        env["HF_HOME"] = args.hf_home
    if not args.hf_online:
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def local_private_root(args: argparse.Namespace) -> Path | None:
    if not args.node_local_private_root:
        return None
    root = Path(args.node_local_private_root).expanduser()
    if not root.is_absolute():
        root = ROOT / root
    return root


def copy_back_private_artifacts(
    job: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, str]:
    root = local_private_root(args)
    if not root or args.no_copy_back_json:
        return {}
    copied: dict[str, str] = {}
    source_dir = root / job["job_id"]
    for key in ["metadata_json", "asr_json", "ocr_json", "vlm_json", "pose_json", "run_log"]:
        source = source_dir / Path(job["private_paths"][key]).name
        if not source.exists():
            continue
        destination = ROOT / job["private_paths"][key]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied[key] = str(destination.relative_to(ROOT))
    return copied


def run_one_job(
    job: dict[str, Any],
    args: argparse.Namespace,
    run_dir: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    started_at = utc_now()
    log_path = run_dir / f"{job['job_id']}.log"
    command = [
        args.python,
        "scripts/run_video_content_pipeline.py",
        "--manifest",
        args.manifest,
        "--job-id",
        job["job_id"],
        "--stages",
        args.stages,
        "--asr-model",
        args.asr_model,
        "--asr-device",
        args.asr_device,
        "--asr-compute-type",
        args.asr_compute_type,
        "--asr-audio-seconds",
        str(args.asr_audio_seconds),
        "--metadata-timeout",
        str(args.metadata_timeout),
        "--audio-timeout",
        str(args.audio_timeout),
        "--download-timeout",
        str(args.download_timeout),
        "--yt-dlp-socket-timeout",
        str(args.yt_dlp_socket_timeout),
        "--yt-dlp-retries",
        str(args.yt_dlp_retries),
    ]
    if args.node_local_private_root:
        command.extend(["--private-root-override", args.node_local_private_root])
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"started_at: {started_at}\n")
        log.write(f"job_id: {job['job_id']}\n")
        log.write(f"command: {' '.join(command)}\n")
        log.write(f"HF_HOME: {env.get('HF_HOME', '')}\n")
        log.write(f"HF_HUB_OFFLINE: {env.get('HF_HUB_OFFLINE', '')}\n")
        log.write(f"CUDA_VISIBLE_DEVICES: {env.get('CUDA_VISIBLE_DEVICES', '')}\n\n")
        log.flush()
        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                timeout=args.per_job_timeout,
            )
            returncode = result.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            returncode = 124
            timed_out = True
            log.write(f"\nTIMEOUT after {args.per_job_timeout}s\n")

    copied_back = copy_back_private_artifacts(job, args)
    asr_path = ROOT / job["private_paths"]["asr_json"]
    asr_status = "missing"
    asr_segment_count = None
    if asr_path.exists():
        try:
            asr_data = json.loads(asr_path.read_text(encoding="utf-8"))
            asr_status = asr_data.get("status", "unknown")
            asr_segment_count = asr_data.get("segment_count")
        except Exception as exc:
            asr_status = f"unreadable:{type(exc).__name__}"
    return {
        "job_id": job["job_id"],
        "source_id": job["source_id"],
        "title": job["title"],
        "started_at": started_at,
        "finished_at": utc_now(),
        "returncode": returncode,
        "timed_out": timed_out,
        "asr_status": asr_status,
        "asr_segment_count": asr_segment_count,
        "log_path": str(log_path.relative_to(ROOT)),
        "copied_back": copied_back,
    }


def rebuild_index(path: str) -> int:
    evidence_files = sorted((ROOT / "data/corpus/video-evidence").glob("*.yaml"))
    write_evidence_index(ROOT / path, evidence_files)
    return len(evidence_files)


def main() -> None:
    args = parse_args()
    jobs = load_jobs(args)
    batch_id = args.batch_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = ROOT / args.log_dir / batch_id
    run_dir.mkdir(parents=True, exist_ok=True)
    env = child_env(args)
    summary = {
        "batch_id": batch_id,
        "started_at": utc_now(),
        "manifest": args.manifest,
        "stages": args.stages,
        "asr_model": args.asr_model,
        "asr_device": args.asr_device,
        "asr_compute_type": args.asr_compute_type,
        "asr_audio_seconds": args.asr_audio_seconds,
        "per_job_timeout": args.per_job_timeout,
        "metadata_timeout": args.metadata_timeout,
        "audio_timeout": args.audio_timeout,
        "download_timeout": args.download_timeout,
        "yt_dlp_socket_timeout": args.yt_dlp_socket_timeout,
        "yt_dlp_retries": args.yt_dlp_retries,
        "node_local_private_root": args.node_local_private_root,
        "hf_home": env.get("HF_HOME", ""),
        "hf_hub_offline": env.get("HF_HUB_OFFLINE", ""),
        "cuda_visible_devices": env.get("CUDA_VISIBLE_DEVICES", ""),
        "jobs_requested": len(jobs),
        "results": [],
    }
    summary_path = run_dir / "summary.json"
    for job in jobs:
        if args.skip_ok_asr and asr_already_ok(job):
            result = {
                "job_id": job["job_id"],
                "source_id": job["source_id"],
                "title": job["title"],
                "started_at": utc_now(),
                "finished_at": utc_now(),
                "returncode": 0,
                "timed_out": False,
                "asr_status": "ok",
                "asr_segment_count": None,
                "log_path": "",
                "skipped": "private ASR already ok",
            }
        else:
            result = run_one_job(job, args, run_dir, env)
        summary["results"].append(result)
        summary["evidence_files_indexed"] = rebuild_index(args.evidence_index)
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            f"{job['job_id']}\treturncode={result['returncode']}\t"
            f"asr={result['asr_status']}\tsegments={result['asr_segment_count']}",
            flush=True,
        )
    summary["finished_at"] = utc_now()
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {summary_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
