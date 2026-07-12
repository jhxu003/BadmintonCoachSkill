from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_evidence_index, write_yaml  # noqa: E402


VLM_ARTIFACT_VERSION = 4
POSE_ARTIFACT_VERSION = 2
_VLM_RUNTIME_CACHE: dict[str, tuple[Any, Any, Any]] = {}
_POSE_MODEL_CACHE: dict[str, Any] = {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run public-video content parsing jobs and emit public-safe timestamp evidence."
    )
    parser.add_argument(
        "--manifest",
        default="data/corpus/video-corpus-manifest.yaml",
        help="Video corpus manifest YAML.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N jobs. 0 means all jobs.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip the first N selected jobs before applying --limit.",
    )
    parser.add_argument(
        "--job-id",
        action="append",
        default=[],
        help="Process only the given job id. Can be passed more than once.",
    )
    parser.add_argument(
        "--stages",
        default="metadata,evidence",
        help=(
            "Comma-separated stages: metadata,audio,download,keyframes,asr,ocr,vlm,pose,evidence. "
            "Unavailable model stages are recorded as skipped rather than faked."
        ),
    )
    parser.add_argument(
        "--evidence-index",
        default="data/corpus/video-evidence-index.tsv",
    )
    parser.add_argument(
        "--skip-public-evidence",
        action="store_true",
        help=(
            "Write only private stage artifacts. Use this on distributed compute nodes, "
            "then rebuild public evidence after all private artifacts are gathered."
        ),
    )
    parser.add_argument(
        "--asr-model",
        default="large-v3-turbo",
        help="faster-whisper model size or local model path.",
    )
    parser.add_argument(
        "--asr-device",
        default="auto",
        help="faster-whisper device: auto, cpu, or cuda.",
    )
    parser.add_argument(
        "--asr-compute-type",
        default="auto",
        help="faster-whisper compute type, for example auto, int8, float16.",
    )
    parser.add_argument(
        "--asr-audio-seconds",
        type=int,
        default=0,
        help="Transcribe only the first N seconds for model-quality pilots. 0 means full audio.",
    )
    parser.add_argument("--metadata-timeout", type=int, default=120)
    parser.add_argument("--audio-timeout", type=int, default=240)
    parser.add_argument("--download-timeout", type=int, default=600)
    parser.add_argument("--yt-dlp-socket-timeout", type=int, default=30)
    parser.add_argument("--yt-dlp-retries", type=int, default=2)
    parser.add_argument(
        "--private-root-override",
        default="",
        help=(
            "Override private artifact root for this run. Use an absolute node-local "
            "path on compute nodes to avoid writing large audio/video artifacts to NFS."
        ),
    )
    parser.add_argument(
        "--video-reuse-root",
        default="",
        help=(
            "Optional node-local root containing <job_id>/source_video.* from an earlier run. "
            "Temporal passes can reuse the visual-pass download without copying it."
        ),
    )
    parser.add_argument("--keyframe-count", type=int, default=6)
    parser.add_argument("--keyframe-start-seconds", type=int, default=8)
    parser.add_argument("--keyframe-interval-seconds", type=int, default=20)
    parser.add_argument(
        "--keyframe-source",
        choices=["fixed", "teaching-windows", "visual-review"],
        default="fixed",
        help=(
            "Choose fixed-interval frames, ASR-derived teaching-window frames, or the "
            "exact planned_frames embedded in a visual pipeline manifest."
        ),
    )
    parser.add_argument(
        "--teaching-windows",
        default="data/corpus/video-asr-teaching-windows-full.yaml",
        help="ASR-derived teaching window YAML used when --keyframe-source=teaching-windows.",
    )
    parser.add_argument(
        "--vlm-model",
        default="Qwen/Qwen2.5-VL-3B-Instruct",
        help="Transformers-compatible VLM checkpoint for private keyframe review.",
    )
    parser.add_argument("--vlm-max-new-tokens", type=int, default=1536)
    parser.add_argument(
        "--vlm-batch-size",
        type=int,
        default=1,
        help="Number of still images per VLM request. One is the quality-first default.",
    )
    parser.add_argument(
        "--pose-model",
        default="yolo11n-pose.pt",
        help="Ultralytics pose checkpoint if ultralytics is installed.",
    )
    return parser.parse_args()


def run_command(
    command: list[str],
    output_path: Path | None = None,
    timeout_seconds: int = 0,
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds or None,
        )
        record = {
            "command": command,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": 124,
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
            "timeout_seconds": timeout_seconds,
        }
    if output_path and result.returncode == 0:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.stdout, encoding="utf-8")
    return record


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def yt_dlp_command() -> list[str] | None:
    if import_available("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    if command_exists("yt-dlp"):
        return ["yt-dlp"]
    return None


def yt_dlp_network_options(args: argparse.Namespace) -> list[str]:
    return [
        "--force-ipv4",
        "--socket-timeout",
        str(args.yt_dlp_socket_timeout),
        "--retries",
        str(args.yt_dlp_retries),
        "--fragment-retries",
        str(args.yt_dlp_retries),
        "--extractor-retries",
        str(args.yt_dlp_retries),
        "--retry-sleep",
        "1",
    ]


def write_private_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_private_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def apply_private_root_override(job: dict[str, Any], private_root: str) -> dict[str, Any]:
    if not private_root:
        return job
    updated = copy.deepcopy(job)
    updated["source_private_paths"] = copy.deepcopy(job.get("private_paths", {}))
    root = Path(private_root).expanduser()
    if not root.is_absolute():
        root = ROOT / root
    job_dir = root / job["job_id"]
    updated["private_paths"] = {
        "job_dir": str(job_dir),
        "metadata_json": str(job_dir / "metadata.json"),
        "video_file": str(job_dir / "source_video"),
        "audio_file": str(job_dir / "audio.m4a"),
        "keyframes_dir": str(job_dir / "keyframes"),
        "asr_json": str(job_dir / "asr.json"),
        "ocr_json": str(job_dir / "ocr.json"),
        "vlm_json": str(job_dir / "vlm.json"),
        "pose_json": str(job_dir / "pose.json"),
        "run_log": str(job_dir / "run.log"),
    }
    return updated


def run_metadata(job: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    path = ROOT / job["private_paths"]["metadata_json"]
    if path.exists() and path.stat().st_size > 0:
        return {"status": "ok", "reason": "metadata already exists"}
    base_command = yt_dlp_command()
    if not base_command:
        return {"status": "skipped", "reason": "yt-dlp not found"}
    record = run_command(
        [
            *base_command,
            *yt_dlp_network_options(args),
            "--dump-json",
            "--no-warnings",
            job["url"],
        ],
        path,
        timeout_seconds=args.metadata_timeout,
    )
    return {"status": "ok" if record["returncode"] == 0 else "failed", "record": record}


def run_download(job: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    path = ROOT / job["private_paths"]["video_file"]
    existing = find_private_video(job, args.video_reuse_root)
    if existing:
        return {
            "status": "ok",
            "reason": "video already exists",
            "video_path": str(existing),
        }
    output_template = str(path) + ".%(ext)s"
    base_command = yt_dlp_command()
    if not base_command:
        return {"status": "skipped", "reason": "yt-dlp not found"}
    ffmpeg_options: list[str] = []
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg_options = ["--ffmpeg-location", get_ffmpeg_exe()]
    except Exception:
        ffmpeg_options = []
    command = [
        *base_command,
        *yt_dlp_network_options(args),
        "--no-playlist",
        *ffmpeg_options,
        "-f",
        "bv*[height<=720]+ba/b[height<=720]/best[height<=720]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        output_template,
        job["url"],
    ]
    record = run_command(command, timeout_seconds=args.download_timeout)
    return {"status": "ok" if record["returncode"] == 0 else "failed", "record": record}


def run_audio(job: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    path = ROOT / job["private_paths"]["audio_file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return {
            "status": "ok",
            "reason": "audio already exists",
            "private_audio_path": str(path),
        }
    base_command = yt_dlp_command()
    if not base_command:
        return {"status": "skipped", "reason": "yt-dlp not found"}
    command = [
        *base_command,
        *yt_dlp_network_options(args),
        "--no-playlist",
        "-f",
        "ba[ext=m4a]/bestaudio[ext=m4a]/bestaudio",
        "-o",
        str(path),
        job["url"],
    ]
    record = run_command(command, timeout_seconds=args.audio_timeout)
    return {
        "status": "ok" if record["returncode"] == 0 and path.exists() else "failed",
        "record": record,
        "private_audio_path": str(path),
    }


def find_private_video(job: dict[str, Any], reuse_root: str = "") -> Path | None:
    bases = [ROOT / job["private_paths"]["video_file"]]
    if reuse_root:
        bases.append(Path(reuse_root).expanduser() / job["job_id"] / "source_video")
    source_path = job.get("source_private_paths", {}).get("video_file")
    if source_path:
        bases.append(ROOT / source_path)
    for base in bases:
        if base.exists() and base.is_file() and base.stat().st_size > 0:
            return base
        candidates = sorted(base.parent.glob(base.name + ".*"))
        for candidate in candidates:
            if candidate.is_file() and candidate.stat().st_size > 0:
                return candidate
    return None


def keyframes_manifest_path(job: dict[str, Any]) -> Path:
    return ROOT / job["private_paths"]["keyframes_dir"] / "manifest.json"


def planned_keyframes(job: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.keyframe_source == "visual-review":
        specs = []
        for frame in job.get("planned_frames", []):
            timestamp_value = round(
                max(float(frame.get("timestamp_seconds") or 0), 0.0), 3
            )
            timestamp = (
                int(timestamp_value)
                if timestamp_value.is_integer()
                else timestamp_value
            )
            source_window_id = frame.get("source_window_id")
            specs.append(
                {
                    "timestamp_seconds": timestamp,
                    "source": "visual_review_manifest",
                    "phase_sample": frame.get("phase_sample"),
                    "source_window_id": source_window_id,
                    "source_window_topic_tags": frame.get("topic_tags", []),
                }
            )
        return specs
    count = max(args.keyframe_count, 0)
    if count <= 0:
        return []
    if args.keyframe_source == "teaching-windows":
        path = ROOT / args.teaching_windows
        if path.exists():
            data = load_yaml(path)
            windows = [
                window
                for window in data.get("windows", [])
                if window.get("source_id") == job.get("source_id")
            ]
            window_specs: list[list[dict[str, Any]]] = []
            seen_timestamps: set[int] = set()
            for window in windows:
                start = float(window.get("start_seconds") or 0)
                end_value = window.get("end_seconds")
                end = float(end_value) if end_value is not None else start
                duration = max(end - start, 0)
                if end > start:
                    offsets = [0.5]
                    if duration >= 8:
                        offsets.extend([0.2, 0.8])
                    elif duration >= 4:
                        offsets.append(0.75)
                    timestamps = [int(round(start + duration * offset)) for offset in offsets]
                else:
                    timestamps = [int(round(start))]
                per_window = []
                for timestamp in timestamps:
                    timestamp = max(timestamp, 0)
                    if timestamp in seen_timestamps:
                        continue
                    seen_timestamps.add(timestamp)
                    per_window.append(
                        {
                            "timestamp_seconds": timestamp,
                            "source": "teaching_windows",
                            "source_window_id": window.get("window_id"),
                            "source_window_topic_tags": window.get("topic_tags", []),
                        }
                    )
                if per_window:
                    window_specs.append(per_window)
            specs = []
            max_points = max((len(items) for items in window_specs), default=0)
            for point_index in range(max_points):
                for per_window in window_specs:
                    if point_index >= len(per_window):
                        continue
                    specs.append(per_window[point_index])
                    if len(specs) >= count:
                        return specs
            if specs:
                return specs
    return [
        {
            "timestamp_seconds": args.keyframe_start_seconds
            + index * args.keyframe_interval_seconds,
            "source": "fixed_interval",
        }
        for index in range(count)
    ]


def load_keyframes(job: dict[str, Any]) -> list[dict[str, Any]]:
    path = keyframes_manifest_path(job)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return list(data.get("frames", []))


def video_duration_seconds(video_path: Path) -> float | None:
    try:
        import cv2
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return None
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        capture.release()
        if fps <= 0 or frame_count <= 0:
            return None
        return frame_count / fps
    except Exception:
        return None


def safe_extraction_timestamp(requested: float, duration: float | None) -> float:
    requested = max(float(requested), 0.0)
    if duration is None or requested < duration:
        return round(requested, 3)
    return round(max(float(duration) - 0.1, 0.0), 3)


def run_keyframes(job: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    output_dir = ROOT / job["private_paths"]["keyframes_dir"]
    manifest_path = keyframes_manifest_path(job)
    frame_specs = planned_keyframes(job, args)
    if not frame_specs:
        result = {
            "status": "failed",
            "stage": "keyframes",
            "reason": "no keyframes were planned for this job",
            "keyframe_source": args.keyframe_source,
            "requested_frame_count": 0,
        }
        write_private_json(manifest_path, result)
        return result
    existing = load_keyframes(job)
    requested_timestamps = [item["timestamp_seconds"] for item in frame_specs]
    existing_timestamps = [item.get("timestamp_seconds") for item in existing]
    if existing and existing_timestamps == requested_timestamps:
        return {
            "status": "ok",
            "stage": "keyframes",
            "reason": "keyframes already exist",
            "keyframe_source": args.keyframe_source,
            "requested_frame_count": len(frame_specs),
            "frame_count": len(existing),
            "failed_frame_count": 0,
            "manifest_path": str(manifest_path),
        }
    video_path = find_private_video(job, args.video_reuse_root)
    if not video_path:
        result = {
            "status": "skipped",
            "stage": "keyframes",
            "reason": "video file missing; run download stage first",
        }
        write_private_json(manifest_path, result)
        return result
    output_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
    except Exception as ffmpeg_exc:
        try:
            import cv2
        except Exception as cv2_exc:
            result = {
                "status": "skipped",
                "stage": "keyframes",
                "reason": (
                    "no keyframe extractor available: "
                    f"imageio_ffmpeg {type(ffmpeg_exc).__name__}; "
                    f"cv2 {type(cv2_exc).__name__}"
                ),
            }
            write_private_json(manifest_path, result)
            return result
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            result = {
                "status": "failed",
                "stage": "keyframes",
                "reason": "OpenCV could not open the downloaded video",
            }
            write_private_json(manifest_path, result)
            return result
        for index, frame_spec in enumerate(frame_specs):
            timestamp = frame_spec["timestamp_seconds"]
            frame_path = output_dir / f"frame-{index + 1:03d}-{timestamp}s.jpg"
            capture.set(cv2.CAP_PROP_POS_MSEC, float(timestamp) * 1000.0)
            ok, frame = capture.read()
            wrote = bool(ok and cv2.imwrite(str(frame_path), frame))
            records.append(
                {
                    "timestamp_seconds": timestamp,
                    "opencv_written": wrote,
                    "source": frame_spec.get("source"),
                    "source_window_id": frame_spec.get("source_window_id"),
                }
            )
            if wrote and frame_path.exists() and frame_path.stat().st_size > 0:
                frames.append(
                    {
                        "frame_id": f"{job['job_id']}-frame-{index + 1:03d}",
                        "timestamp_seconds": timestamp,
                        "path": str(frame_path),
                        "source": frame_spec.get("source"),
                        "source_window_id": frame_spec.get("source_window_id"),
                        "source_window_topic_tags": frame_spec.get(
                            "source_window_topic_tags", []
                        ),
                    }
                )
        capture.release()
    else:
        duration_seconds: float | None = None
        for index, frame_spec in enumerate(frame_specs):
            timestamp = frame_spec["timestamp_seconds"]
            frame_path = output_dir / f"frame-{index + 1:03d}-{timestamp}s.jpg"
            extracted_timestamp = timestamp
            command = [
                get_ffmpeg_exe(),
                "-y",
                "-ss",
                str(timestamp),
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(frame_path),
            ]
            record = run_command(command, timeout_seconds=60)
            extracted = (
                record["returncode"] == 0
                and frame_path.exists()
                and frame_path.stat().st_size > 0
            )
            fallback_used = False
            if not extracted:
                if duration_seconds is None:
                    duration_seconds = video_duration_seconds(video_path)
                fallback_timestamp = safe_extraction_timestamp(timestamp, duration_seconds)
                if fallback_timestamp != timestamp:
                    frame_path.unlink(missing_ok=True)
                    extracted_timestamp = fallback_timestamp
                    fallback_command = command.copy()
                    fallback_command[fallback_command.index("-ss") + 1] = str(
                        fallback_timestamp
                    )
                    fallback_record = run_command(fallback_command, timeout_seconds=60)
                    record = {
                        **fallback_record,
                        "requested_timestamp_seconds": timestamp,
                        "fallback_timestamp_seconds": fallback_timestamp,
                    }
                    fallback_used = True
                    extracted = (
                        fallback_record["returncode"] == 0
                        and frame_path.exists()
                        and frame_path.stat().st_size > 0
                    )
            records.append(
                {
                    "timestamp_seconds": timestamp,
                    "extracted_timestamp_seconds": extracted_timestamp,
                    "end_of_video_fallback": fallback_used,
                    "returncode": record["returncode"],
                    "stderr_tail": record.get("stderr_tail", "")[-800:],
                    "source": frame_spec.get("source"),
                    "source_window_id": frame_spec.get("source_window_id"),
                }
            )
            if extracted:
                frames.append(
                    {
                        "frame_id": f"{job['job_id']}-frame-{index + 1:03d}",
                        "timestamp_seconds": timestamp,
                        "extracted_timestamp_seconds": extracted_timestamp,
                        "path": str(frame_path),
                        "source": frame_spec.get("source"),
                        "source_window_id": frame_spec.get("source_window_id"),
                        "source_window_topic_tags": frame_spec.get(
                            "source_window_topic_tags", []
                        ),
                    }
                )
    result = {
        "status": (
            "ok"
            if len(frames) == len(frame_specs)
            else "partial"
            if frames
            else "failed"
        ),
        "stage": "keyframes",
        "video_path": str(video_path),
        "keyframe_source": args.keyframe_source,
        "requested_frame_count": len(frame_specs),
        "frame_count": len(frames),
        "failed_frame_count": len(frame_specs) - len(frames),
        "frames": frames,
        "records": records,
    }
    write_private_json(manifest_path, result)
    return result


def import_available(module_name: str) -> bool:
    try:
        __import__(module_name)
    except Exception:
        return False
    return True


def run_model_stage(job: dict[str, Any], stage: str, module_name: str) -> dict[str, Any]:
    private_path = ROOT / job["private_paths"][f"{stage}_json"]
    if not import_available(module_name):
        result = {
            "status": "skipped",
            "reason": f"{module_name} is not installed in this Python environment",
            "stage": stage,
        }
        write_private_json(private_path, result)
        return result
    result = {
        "status": "needs_worker",
        "reason": (
            f"{stage} dependency is available, but the heavyweight worker should be "
            "launched on a GPU node with the project-specific model checkpoint."
        ),
        "stage": stage,
    }
    write_private_json(private_path, result)
    return result


def run_ocr(job: dict[str, Any]) -> dict[str, Any]:
    private_path = ROOT / job["private_paths"]["ocr_json"]
    frames = load_keyframes(job)
    if not frames:
        result = {
            "status": "skipped",
            "reason": "keyframes missing; run keyframes stage first",
            "stage": "ocr",
        }
        write_private_json(private_path, result)
        return result
    try:
        from paddleocr import PaddleOCR
    except Exception as exc:
        result = {
            "status": "skipped",
            "reason": f"PaddleOCR import failed: {type(exc).__name__}: {exc}",
            "stage": "ocr",
        }
        write_private_json(private_path, result)
        return result
    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        frame_results = []
        for frame in frames:
            result = ocr.ocr(frame["path"], cls=True)
            texts = []
            for block in result or []:
                for line in block or []:
                    if len(line) >= 2 and isinstance(line[1], (list, tuple)):
                        texts.append(
                            {
                                "text": str(line[1][0]),
                                "confidence": float(line[1][1]),
                            }
                        )
            frame_results.append(
                {
                    "frame_id": frame["frame_id"],
                    "timestamp_seconds": frame["timestamp_seconds"],
                    "text_count": len(texts),
                    "texts": texts[:20],
                }
            )
        result = {
            "status": "ok",
            "stage": "ocr",
            "model": "PaddleOCR",
            "frame_count": len(frame_results),
            "frames": frame_results,
        }
    except Exception as exc:
        result = {
            "status": "failed",
            "stage": "ocr",
            "model": "PaddleOCR",
            "reason": f"{type(exc).__name__}: {exc}",
        }
    write_private_json(private_path, result)
    return result


def load_vlm_runtime(model_name: str) -> tuple[Any, Any, Any]:
    cached = _VLM_RUNTIME_CACHE.get(model_name)
    if cached:
        return cached
    import torch
    from transformers import AutoConfig
    from transformers import AutoProcessor
    config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
    config.base_model_tp_plan = None
    for nested_name in ["text_config", "vision_config"]:
        nested_config = getattr(config, nested_name, None)
        if nested_config is not None and hasattr(nested_config, "base_model_tp_plan"):
            nested_config.base_model_tp_plan = None
    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    torch_dtype = torch.float32
    if torch.cuda.is_available():
        torch_dtype = (
            torch.bfloat16
            if getattr(torch.cuda, "is_bf16_supported", lambda: False)()
            else torch.float16
        )
    model_type = str(getattr(config, "model_type", ""))
    if "qwen3_vl" in model_type:
        from transformers import Qwen3VLForConditionalGeneration as ModelClass
    else:
        try:
            from transformers import Qwen2_5_VLForConditionalGeneration as ModelClass
        except Exception:
            from transformers import AutoModelForVision2Seq as ModelClass
    model = ModelClass.from_pretrained(
        model_name,
        config=config,
        torch_dtype=torch_dtype,
        device_map="auto",
        trust_remote_code=True,
    )
    runtime = (torch, processor, model)
    _VLM_RUNTIME_CACHE[model_name] = runtime
    return runtime


def extract_first_json_value(text: str) -> dict[str, Any] | list[Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, (dict, list)):
            return value
    raise ValueError("VLM response does not contain a complete JSON object or array")


def primary_subject_score(frame: dict[str, Any]) -> tuple[int, int, int, int]:
    body = frame.get("body_configuration", [])
    if isinstance(body, str):
        body = [body]
    action_body_count = sum(
        item not in {"neutral_standing", "unclear"} for item in body
    ) if isinstance(body, list) else 0
    racket_score = {"visible": 2, "unclear": 1}.get(
        frame.get("racket_visibility"), 0
    )
    confidence_score = {"high": 3, "medium": 2, "low": 1}.get(
        frame.get("confidence"), 0
    )
    view_score = int(
        frame.get("primary_subject_view") not in {"unclear", "not_visible", None}
    )
    return (
        int(frame.get("person_visible") is True),
        action_body_count,
        racket_score,
        confidence_score + view_score,
    )


def coerce_vlm_frame_records(
    data: dict[str, Any] | list[Any], expected_count: int
) -> list[Any] | None:
    if isinstance(data, dict) and isinstance(data.get("frames"), list):
        frames = data["frames"]
    elif isinstance(data, dict) and expected_count == 1:
        frames = [data]
    elif isinstance(data, list):
        frames = data
    else:
        return None
    if expected_count == 1 and len(frames) > 1 and all(
        isinstance(frame, dict) for frame in frames
    ):
        selected = dict(max(frames, key=primary_subject_score))
        limits = selected.get("visibility_limits", [])
        if isinstance(limits, list):
            selected["visibility_limits"] = list(
                dict.fromkeys([*limits, "multiple_people"])
            )
        frames = [selected]
    return frames


def parse_vlm_frame_batch(text: str, expected_timestamps: list[int]) -> list[dict[str, Any]]:
    data = extract_first_json_value(text)
    frames = coerce_vlm_frame_records(data, len(expected_timestamps))
    if not isinstance(frames, list) or len(frames) != len(expected_timestamps):
        raise ValueError(
            f"expected {len(expected_timestamps)} frame records, got "
            f"{len(frames) if isinstance(frames, list) else 'non-list'}"
        )
    required = {
        "person_visible",
        "primary_subject_view",
        "body_configuration",
        "racket_visibility",
        "racket_position",
        "on_screen_text_present",
        "visibility_limits",
        "confidence",
    }
    allowed_views = {"front", "back", "side", "oblique", "unclear", "not_visible"}
    allowed_body = {
        "neutral_standing",
        "staggered_stance",
        "wide_base",
        "lunge",
        "single_leg_support",
        "airborne",
        "torso_turned",
        "arm_raised",
        "arm_extended",
        "unclear",
    }
    allowed_racket_visibility = {"visible", "not_visible", "unclear"}
    allowed_racket_positions = {
        "below_waist",
        "waist_to_shoulder",
        "above_shoulder",
        "behind_torso",
        "not_visible",
        "unclear",
    }
    allowed_confidence = {"low", "medium", "high"}
    allowed_limits = {
        "subject_too_small",
        "racket_blurred",
        "racket_occluded",
        "lower_body_occluded",
        "camera_crop",
        "multiple_people",
        "unclear",
    }
    validated: list[dict[str, Any]] = []
    for expected_index, (frame, timestamp) in enumerate(
        zip(frames, expected_timestamps), start=1
    ):
        if not isinstance(frame, dict):
            raise ValueError(f"frame {expected_index} is not an object")
        missing = sorted(required - set(frame))
        if missing:
            raise ValueError(f"frame {expected_index} missing fields: {', '.join(missing)}")
        if not isinstance(frame["person_visible"], bool):
            raise ValueError(f"frame {expected_index} person_visible is not boolean")
        if frame["primary_subject_view"] not in allowed_views:
            raise ValueError(f"frame {expected_index} has unsupported subject view")
        body = frame["body_configuration"]
        if isinstance(body, str):
            body = [body]
        if (
            not isinstance(body, list)
            or not body
            or any(item not in allowed_body for item in body)
        ):
            raise ValueError(f"frame {expected_index} has unsupported body configuration")
        if frame["racket_visibility"] not in allowed_racket_visibility:
            raise ValueError(f"frame {expected_index} has unsupported racket visibility")
        if frame["racket_position"] not in allowed_racket_positions:
            raise ValueError(f"frame {expected_index} has unsupported racket position")
        if not isinstance(frame["on_screen_text_present"], bool):
            raise ValueError(f"frame {expected_index} on_screen_text_present is not boolean")
        limits = frame["visibility_limits"]
        if isinstance(limits, str):
            limits = [limits]
        if (
            not isinstance(limits, list)
            or any(not isinstance(item, str) for item in limits)
            or any(item not in allowed_limits for item in limits)
        ):
            raise ValueError(f"frame {expected_index} visibility_limits is not a string list")
        if frame["confidence"] not in allowed_confidence:
            raise ValueError(f"frame {expected_index} has unsupported confidence")
        normalized = {key: frame[key] for key in required}
        normalized["image_index"] = expected_index
        normalized["timestamp_seconds"] = timestamp
        normalized["body_configuration"] = list(dict.fromkeys(body))
        normalized["visibility_limits"] = list(dict.fromkeys([*limits, "still_frame_no_motion"]))
        validated.append(normalized)
    return validated


def recover_vlm_progress(
    existing: dict[str, Any] | None,
    selected_frames: list[dict[str, Any]],
    *,
    model_name: str,
    batch_size: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    if (
        not existing
        or existing.get("status") != "failed"
        or existing.get("artifact_version") != VLM_ARTIFACT_VERSION
        or existing.get("schema") != "visible_still_frame_v2"
        or existing.get("model") != model_name
    ):
        return [], [], 0
    outputs: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    start_index = 0
    effective_batch_size = max(int(batch_size), 1)
    for raw_record in existing.get("batch_outputs", []):
        if start_index >= len(selected_frames) or not isinstance(raw_record, dict):
            break
        batch_frames = selected_frames[
            start_index : start_index + effective_batch_size
        ]
        expected_timestamps = [frame["timestamp_seconds"] for frame in batch_frames]
        if raw_record.get("timestamps_seconds") != expected_timestamps:
            break
        raw_response = raw_record.get("raw_response")
        if not isinstance(raw_response, str):
            break
        try:
            parsed_frames = parse_vlm_frame_batch(raw_response, expected_timestamps)
        except Exception:
            break
        record = dict(raw_record)
        record["status"] = "validated"
        outputs.append(record)
        for local_index, parsed in enumerate(parsed_frames):
            source_frame = batch_frames[local_index]
            parsed["image_index"] = start_index + local_index + 1
            parsed["frame_id"] = source_frame["frame_id"]
            observations.append(parsed)
        start_index += len(batch_frames)
    return outputs, observations, start_index


def vlm_batch_prompt(timestamps: list[int]) -> str:
    return (
        "Review these ordered badminton coaching still images independently. Report only directly "
        "visible facts in each still; do not infer motion direction, stroke phase, contact, force, "
        "joint rotation, weight transfer, coaching intent, or correctness. For each image choose "
        "one primary coaching subject; if multiple people are visible, still describe only that "
        "primary subject and never output one object per person. Return only one compact "
        f"JSON array with exactly {len(timestamps)} objects in image order. Do not repeat image "
        "indexes or timestamps. Every object must contain exactly: person_visible (boolean), "
        "primary_subject_view (front|back|side|oblique|unclear|not_visible), "
        "body_configuration (non-empty array chosen from neutral_standing|staggered_stance|wide_base|"
        "lunge|single_leg_support|airborne|torso_turned|arm_raised|arm_extended|unclear), "
        "racket_visibility (visible|not_visible|unclear), racket_position (below_waist|"
        "waist_to_shoulder|above_shoulder|behind_torso|not_visible|unclear), "
        "on_screen_text_present (boolean), visibility_limits (array chosen only from subject_too_small|"
        "racket_blurred|racket_occluded|lower_body_occluded|camera_crop|multiple_people|unclear), and "
        "confidence (low|medium|high). Do not use Markdown fences or add commentary."
    )


def run_vlm(
    job: dict[str, Any], model_name: str, max_new_tokens: int, batch_size: int
) -> dict[str, Any]:
    private_path = ROOT / job["private_paths"]["vlm_json"]
    frames = load_keyframes(job)
    if not frames:
        result = {
            "status": "skipped",
            "reason": "keyframes missing; run keyframes stage first",
            "stage": "vlm",
        }
        write_private_json(private_path, result)
        return result
    timestamps = [frame["timestamp_seconds"] for frame in frames[:18]]
    existing = load_private_json(private_path)
    if (
        existing
        and existing.get("status") == "ok"
        and existing.get("artifact_version") == VLM_ARTIFACT_VERSION
        and existing.get("timestamps_seconds") == timestamps
        and existing.get("model") == model_name
    ):
        return existing
    selected_frames = frames[: min(len(frames), 18)]
    effective_batch_size = max(int(batch_size), 1)
    batch_outputs, observations, resume_index = recover_vlm_progress(
        existing,
        selected_frames,
        model_name=model_name,
        batch_size=effective_batch_size,
    )
    if resume_index == len(selected_frames):
        result = {
            "status": "ok",
            "stage": "vlm",
            "artifact_version": VLM_ARTIFACT_VERSION,
            "schema": "visible_still_frame_v2",
            "model": model_name,
            "frame_count": len(selected_frames),
            "batch_count": len(batch_outputs),
            "batch_size": effective_batch_size,
            "frame_ids": [frame["frame_id"] for frame in selected_frames],
            "timestamps_seconds": [frame["timestamp_seconds"] for frame in selected_frames],
            "frames": observations,
            "batch_outputs": batch_outputs,
            "summary": json.dumps(
                {"frames": observations, "sequence_observations": []},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        }
        write_private_json(private_path, result)
        return result
    try:
        from PIL import Image
        torch, processor, model = load_vlm_runtime(model_name)
    except Exception as exc:
        result = {
            "status": "skipped",
            "reason": f"VLM imports failed: {type(exc).__name__}: {exc}",
            "stage": "vlm",
        }
        write_private_json(private_path, result)
        return result

    try:
        for batch_start in range(
            resume_index, len(selected_frames), effective_batch_size
        ):
            batch_frames = selected_frames[batch_start : batch_start + effective_batch_size]
            batch_timestamps = [frame["timestamp_seconds"] for frame in batch_frames]
            images = [Image.open(frame["path"]).convert("RGB") for frame in batch_frames]
            try:
                content = [{"type": "image"} for _ in images]
                content.append({"type": "text", "text": vlm_batch_prompt(batch_timestamps)})
                messages = [{"role": "user", "content": content}]
                text = processor.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                inputs = processor(
                    text=[text],
                    images=images,
                    padding=True,
                    return_tensors="pt",
                )
                inputs = inputs.to(model.device)
                with torch.inference_mode():
                    generated = model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        do_sample=False,
                    )
                trimmed = [
                    output_ids[len(input_ids) :]
                    for input_ids, output_ids in zip(inputs.input_ids, generated)
                ]
                output_text = processor.batch_decode(
                    trimmed,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )[0]
                batch_record = {
                    "batch_index": len(batch_outputs) + 1,
                    "timestamps_seconds": batch_timestamps,
                    "status": "received",
                    "raw_response": output_text.strip(),
                }
                batch_outputs.append(batch_record)
                parsed_frames = parse_vlm_frame_batch(output_text, batch_timestamps)
                for local_index, parsed in enumerate(parsed_frames):
                    source_frame = batch_frames[local_index]
                    parsed["image_index"] = batch_start + local_index + 1
                    parsed["frame_id"] = source_frame["frame_id"]
                    observations.append(parsed)
                batch_record["status"] = "validated"
                del inputs, generated, trimmed
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            finally:
                for image in images:
                    image.close()
        canonical_summary = json.dumps(
            {"frames": observations, "sequence_observations": []},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        result = {
            "status": "ok",
            "stage": "vlm",
            "artifact_version": VLM_ARTIFACT_VERSION,
            "schema": "visible_still_frame_v2",
            "model": model_name,
            "frame_count": len(selected_frames),
            "batch_count": len(batch_outputs),
            "batch_size": effective_batch_size,
            "frame_ids": [frame["frame_id"] for frame in selected_frames],
            "timestamps_seconds": [frame["timestamp_seconds"] for frame in selected_frames],
            "frames": observations,
            "batch_outputs": batch_outputs,
            "summary": canonical_summary,
        }
    except Exception as exc:
        result = {
            "status": "failed",
            "stage": "vlm",
            "artifact_version": VLM_ARTIFACT_VERSION,
            "schema": "visible_still_frame_v2",
            "model": model_name,
            "completed_batches": len(batch_outputs),
            "batch_outputs": batch_outputs,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    write_private_json(private_path, result)
    return result


def run_pose(job: dict[str, Any], pose_model: str) -> dict[str, Any]:
    private_path = ROOT / job["private_paths"]["pose_json"]
    frames = load_keyframes(job)
    if not frames:
        result = {
            "status": "skipped",
            "reason": "keyframes missing; run keyframes stage first",
            "stage": "pose",
        }
        write_private_json(private_path, result)
        return result
    timestamps = [frame["timestamp_seconds"] for frame in frames]
    existing = load_private_json(private_path)
    if (
        existing
        and existing.get("status") == "ok"
        and existing.get("artifact_version") == POSE_ARTIFACT_VERSION
        and existing.get("timestamps_seconds") == timestamps
        and Path(str(existing.get("model") or "")).name == Path(pose_model).name
    ):
        return existing
    try:
        from ultralytics import YOLO
    except Exception as exc:
        result = {
            "status": "skipped",
            "reason": f"ultralytics import failed: {type(exc).__name__}: {exc}",
            "stage": "pose",
        }
        write_private_json(private_path, result)
        return result
    try:
        model = _POSE_MODEL_CACHE.get(pose_model)
        if model is None:
            model = YOLO(pose_model)
            _POSE_MODEL_CACHE[pose_model] = model
        frame_results = []
        for frame in frames:
            predictions = model(frame["path"], verbose=False)
            people = []
            for pred in predictions:
                keypoints = getattr(pred, "keypoints", None)
                if keypoints is None or keypoints.xy is None:
                    continue
                xy = keypoints.xy.cpu().tolist()
                conf = keypoints.conf.cpu().tolist() if keypoints.conf is not None else []
                boxes = getattr(pred, "boxes", None)
                box_xyxy = (
                    boxes.xyxy.cpu().tolist()
                    if boxes is not None and boxes.xyxy is not None
                    else []
                )
                for person_index, points in enumerate(xy):
                    person_confidence = (
                        [round(float(value), 5) for value in conf[person_index]]
                        if conf and person_index < len(conf)
                        else []
                    )
                    people.append(
                        {
                            "person_index": person_index,
                            "keypoint_count": len(points),
                            "keypoints_xy": [
                                [round(float(x), 3), round(float(y), 3)] for x, y in points
                            ],
                            "keypoint_confidence": person_confidence,
                            "bbox_xyxy": (
                                [round(float(value), 3) for value in box_xyxy[person_index]]
                                if person_index < len(box_xyxy)
                                else None
                            ),
                            "mean_confidence": (
                                round(sum(person_confidence) / len(person_confidence), 4)
                                if person_confidence
                                else None
                            ),
                        }
                    )
            frame_results.append(
                {
                    "frame_id": frame["frame_id"],
                    "timestamp_seconds": frame["timestamp_seconds"],
                    "person_count": len(people),
                    "people": people[:4],
                }
            )
        result = {
            "status": "ok",
            "stage": "pose",
            "artifact_version": POSE_ARTIFACT_VERSION,
            "model": pose_model,
            "frame_count": len(frame_results),
            "timestamps_seconds": timestamps,
            "frames": frame_results,
        }
    except Exception as exc:
        result = {
            "status": "failed",
            "stage": "pose",
            "model": pose_model,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    write_private_json(private_path, result)
    return result


def build_asr_input(job: dict[str, Any], audio_path: Path, seconds: int) -> tuple[Path, dict[str, Any]]:
    if seconds <= 0:
        return audio_path, {"audio_scope_seconds": None, "audio_scope": "full"}
    clipped_path = audio_path.with_name(f"asr-preview-{seconds}s.wav")
    if clipped_path.exists():
        return clipped_path, {"audio_scope_seconds": seconds, "audio_scope": "preview"}
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
    except Exception as exc:
        return audio_path, {
            "audio_scope_seconds": None,
            "audio_scope": "full",
            "clip_warning": f"imageio_ffmpeg unavailable: {type(exc).__name__}: {exc}",
        }
    command = [
        get_ffmpeg_exe(),
        "-y",
        "-i",
        str(audio_path),
        "-t",
        str(seconds),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(clipped_path),
    ]
    record = run_command(command)
    if record["returncode"] != 0 or not clipped_path.exists():
        return audio_path, {
            "audio_scope_seconds": None,
            "audio_scope": "full",
            "clip_warning": "ffmpeg clipping failed; full audio was used",
        }
    return clipped_path, {"audio_scope_seconds": seconds, "audio_scope": "preview"}


def run_asr(
    job: dict[str, Any],
    model_size: str,
    device: str,
    compute_type: str,
    audio_seconds: int,
) -> dict[str, Any]:
    private_path = ROOT / job["private_paths"]["asr_json"]
    audio_path = ROOT / job["private_paths"]["audio_file"]
    if not audio_path.exists():
        result = {
            "status": "skipped",
            "reason": "audio file missing; run audio stage first",
            "stage": "asr",
        }
        write_private_json(private_path, result)
        return result
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        result = {
            "status": "skipped",
            "reason": f"faster_whisper import failed: {type(exc).__name__}: {exc}",
            "stage": "asr",
        }
        write_private_json(private_path, result)
        return result

    try:
        asr_input, audio_scope = build_asr_input(job, audio_path, audio_seconds)
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        segments, info = model.transcribe(
            str(asr_input),
            language="zh",
            vad_filter=True,
            word_timestamps=False,
        )
        collected = []
        for segment in segments:
            text = " ".join(segment.text.strip().split())
            if not text:
                continue
            collected.append(
                {
                    "start": round(float(segment.start), 2),
                    "end": round(float(segment.end), 2),
                    "text": text,
                }
            )
        result = {
            "status": "ok",
            "stage": "asr",
            "model": model_size,
            "device": device,
            "compute_type": compute_type,
            **audio_scope,
            "language": info.language,
            "language_probability": round(float(info.language_probability), 4),
            "segment_count": len(collected),
            "segments": collected,
        }
    except Exception as exc:
        result = {
            "status": "failed",
            "stage": "asr",
            "model": model_size,
            "device": device,
            "compute_type": compute_type,
            "audio_scope_seconds": audio_seconds or None,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    write_private_json(private_path, result)
    return result


def summarize_private_stage(job: dict[str, Any], stage: str) -> dict[str, Any]:
    key = f"{stage}_json"
    candidates: list[Path] = []
    for paths_key in ["private_paths", "source_private_paths"]:
        raw_path = job.get(paths_key, {}).get(key)
        if raw_path:
            candidate = ROOT / raw_path
            if candidate not in candidates:
                candidates.append(candidate)
    for path in candidates:
        if not path.exists():
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"status": "unreadable", "reason": str(exc)}
    return {"status": "missing"}


def summarize_keyframes_stage(job: dict[str, Any]) -> dict[str, Any]:
    path = keyframes_manifest_path(job)
    if not path.exists():
        return {"status": "missing"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "unreadable", "reason": str(exc)}
    return data


def summarize_asr_for_public(asr_data: dict[str, Any]) -> str:
    if asr_data.get("status") != "ok":
        return "ASR did not produce usable timestamped content."
    segments = asr_data.get("segments", [])
    if not segments:
        return "ASR ran but produced no usable speech segments."
    early_segments = segments[:6]
    windows = [
        f"{item['start']:.1f}-{item['end']:.1f}s"
        for item in early_segments
        if "start" in item and "end" in item
    ]
    return (
        f"Private ASR produced {len(segments)} timestamped Chinese speech segments. "
        f"Initial reviewed windows for human summarization: {', '.join(windows)}."
    )


def summarize_missing_or_private(stage_name: str, data: dict[str, Any]) -> str:
    if data.get("status") == "ok":
        return f"See private {stage_name} artifact; public summary requires human review."
    return f"No {stage_name.upper()} content was promoted into the public repository."


def sanitize_stage_status(stage: str, data: dict[str, Any]) -> dict[str, Any]:
    status = {"status": data.get("status", "missing")}
    if data.get("reason"):
        status["reason"] = data["reason"]
    if stage == "asr":
        for field in [
            "stage",
            "model",
            "device",
            "compute_type",
            "language",
            "language_probability",
            "segment_count",
        ]:
            if field in data:
                value = data[field]
                if field == "model" and isinstance(value, str) and Path(value).is_absolute():
                    value = Path(value).name
                status[field] = value
        if "audio_scope" in data:
            status["audio_scope"] = data["audio_scope"]
        if "audio_scope_seconds" in data:
            status["audio_scope_seconds"] = data["audio_scope_seconds"]
    if stage in {"keyframes", "ocr", "vlm", "pose"}:
        for field in [
            "stage",
            "model",
            "artifact_version",
            "schema",
            "frame_count",
            "batch_count",
            "batch_size",
        ]:
            if field in data:
                value = data[field]
                if field == "model" and isinstance(value, str) and Path(value).is_absolute():
                    value = Path(value).name
                status[field] = value
    return status


def sanitize_run_status(run_status: dict[str, Any]) -> dict[str, Any]:
    sanitized = {"job_id": run_status.get("job_id"), "stages": {}}
    for stage, value in run_status.get("stages", {}).items():
        if not isinstance(value, dict):
            sanitized["stages"][stage] = {"status": "unknown"}
            continue
        stage_record = {"status": value.get("status", "unknown")}
        if value.get("reason"):
            stage_record["reason"] = value["reason"]
        record = value.get("record")
        if isinstance(record, dict):
            stage_record["returncode"] = record.get("returncode")
        sanitized["stages"][stage] = stage_record
    return sanitized


def build_public_evidence(job: dict[str, Any], run_status: dict[str, Any]) -> Path:
    evidence_path = ROOT / job["public_outputs"]["timestamp_evidence"]
    stage_status = {
        "keyframes": summarize_keyframes_stage(job),
        **{
            stage: summarize_private_stage(job, stage)
            for stage in ["asr", "ocr", "vlm", "pose"]
        },
    }
    has_model_content = any(
        value.get("status") == "ok" for stage, value in stage_status.items() if stage != "keyframes"
    )
    evidence_level = (
        "content_model_candidate" if has_model_content else "needs_content_model_review"
    )
    review_status = "pending_human_review" if has_model_content else "model_not_run"
    segment = {
        "evidence_id": f"{job['job_id']}-seg-001",
        "start_seconds": 0,
        "end_seconds": None,
        "topic_tags": job["priority_topics"],
        "evidence_level": evidence_level,
        "review_status": review_status,
        "promotion_target": "none_until_reviewed",
        "asr_summary": summarize_asr_for_public(stage_status["asr"]),
        "ocr_summary": summarize_missing_or_private("OCR", stage_status["ocr"]),
        "visual_summary": summarize_missing_or_private("VLM", stage_status["vlm"]),
        "teaching_point_candidate": {
            "problem": "pending content-level model review",
            "diagnosis_rule": "not promoted",
            "correction": "not promoted",
            "drill": "not promoted",
        },
    }
    evidence = {
        "source_id": job["source_id"],
        "job_id": job["job_id"],
        "title": job["title"],
        "url": job["url"],
        "platform": job["platform"],
        "authorization_status": job["authorization_status"],
        "public_safety": {
            "raw_video_committed": False,
            "raw_transcript_committed": False,
            "paid_material_committed": False,
            "long_subtitle_excerpt_committed": False,
            "raw_metadata_committed": False,
            "temporary_media_urls_committed": False,
        },
        "run_status": sanitize_run_status(run_status),
        "stage_status": {
            stage: sanitize_stage_status(stage, data)
            for stage, data in stage_status.items()
        },
        "segments": [segment],
    }
    write_yaml(evidence_path, evidence)
    return evidence_path


def process_job(
    job: dict[str, Any], stages: set[str], args: argparse.Namespace
) -> Path | None:
    job_dir = ROOT / job["private_paths"]["job_dir"]
    job_dir.mkdir(parents=True, exist_ok=True)
    run_status: dict[str, Any] = {"job_id": job["job_id"], "stages": {}}
    if "metadata" in stages:
        run_status["stages"]["metadata"] = run_metadata(job, args)
    if "audio" in stages:
        run_status["stages"]["audio"] = run_audio(job, args)
    if "download" in stages:
        run_status["stages"]["download"] = run_download(job, args)
    if {"keyframes", "ocr", "vlm", "pose"} & stages:
        run_status["stages"]["keyframes"] = run_keyframes(job, args)
    if "asr" in stages:
        run_status["stages"]["asr"] = run_asr(
            job,
            model_size=args.asr_model,
            device=args.asr_device,
            compute_type=args.asr_compute_type,
            audio_seconds=args.asr_audio_seconds,
        )
    if "ocr" in stages:
        run_status["stages"]["ocr"] = run_ocr(job)
    if "vlm" in stages:
        run_status["stages"]["vlm"] = run_vlm(
            job,
            model_name=args.vlm_model,
            max_new_tokens=args.vlm_max_new_tokens,
            batch_size=args.vlm_batch_size,
        )
    if "pose" in stages:
        run_status["stages"]["pose"] = run_pose(job, args.pose_model)
    if args.skip_public_evidence:
        write_private_json(ROOT / job["private_paths"]["run_log"], run_status)
        return None
    if "evidence" not in stages:
        stages.add("evidence")
    evidence_path = build_public_evidence(job, run_status)
    write_private_json(ROOT / job["private_paths"]["run_log"], run_status)
    return evidence_path


def main() -> None:
    args = parse_args()
    manifest = load_yaml(ROOT / args.manifest)
    jobs = manifest.get("jobs", [])
    if args.job_id:
        requested = set(args.job_id)
        jobs = [job for job in jobs if job["job_id"] in requested]
    if args.offset:
        jobs = jobs[args.offset :]
    if args.limit:
        jobs = jobs[: args.limit]
    jobs = [apply_private_root_override(job, args.private_root_override) for job in jobs]
    stages = {item.strip() for item in args.stages.split(",") if item.strip()}
    results = [process_job(job, stages, args) for job in jobs]
    evidence_files = [path for path in results if path is not None]
    print(f"processed {len(results)} jobs")
    if args.skip_public_evidence:
        print("skipped public evidence generation")
    else:
        write_evidence_index(ROOT / args.evidence_index, evidence_files)
        print(f"wrote {args.evidence_index}")


if __name__ == "__main__":
    main()
