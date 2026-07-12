from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml  # noqa: E402


ALLOWED_TOPICS = {
    "student_fit",
    "diagnosis_flow",
    "high_clear",
    "smash",
    "racket_preparation",
    "top_elbow",
    "hip_rotation",
    "internal_rotation",
    "wrist",
    "contact_point",
    "footwork",
    "drop",
    "drive",
    "serve_receive",
    "doubles",
    "match_transfer",
    "training_plan",
    "safety",
    "equipment",
}
ALLOWED_CLAIM_TYPES = {
    "technical_principle",
    "common_error",
    "correction_sequence",
    "drill",
    "student_fit",
    "tactical_context",
    "safety_constraint",
    "diagnosis_rule",
    "training_progression",
    "match_transfer",
}
CLAIM_TYPE_ALIASES = {
    "diagnosis_flow": "diagnosis_rule",
    "training_plan": "training_progression",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Use a local instruction model to distill private ASR teaching windows into "
            "private, structured coaching-claim candidates."
        )
    )
    parser.add_argument(
        "--manifest",
        default="data/coaches/li-yuxuan/corpus/video-corpus-manifest.yaml",
    )
    parser.add_argument(
        "--windows",
        default="data/raw-private/li-yuxuan/asr-teaching-windows-progress.yaml",
    )
    parser.add_argument(
        "--output-root",
        default="data/raw-private/li-yuxuan/semantic-claims",
    )
    parser.add_argument(
        "--model",
        default="/tmp/jhxu-qwen3vl8b-modelscope",
        help="Local Transformers-compatible instruction model.",
    )
    parser.add_argument("--max-new-tokens", type=int, default=1400)
    parser.add_argument("--max-windows-per-source", type=int, default=8)
    parser.add_argument("--max-window-characters", type=int, default=5000)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--job-id", action="append", default=[])
    parser.add_argument("--skip-ok", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def select_jobs(manifest: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    jobs = list(manifest.get("jobs", []))
    if args.job_id:
        requested = set(args.job_id)
        jobs = [job for job in jobs if job["job_id"] in requested]
    if args.offset:
        jobs = jobs[args.offset :]
    if args.limit:
        jobs = jobs[: args.limit]
    return jobs


def windows_by_job(windows_doc: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for window in windows_doc.get("windows", []):
        if not isinstance(window, dict):
            continue
        job_id = str(window.get("job_id", ""))
        if not job_id:
            window_id = str(window.get("window_id", ""))
            job_id = window_id.rsplit("-w", 1)[0] if "-w" in window_id else ""
        if job_id:
            grouped.setdefault(job_id, []).append(window)
    return grouped


def transcript_for_window(asr: dict[str, Any], window: dict[str, Any]) -> str:
    start = float(window.get("start_seconds", 0))
    end = float(window.get("end_seconds", start))
    parts = [
        str(segment.get("text", "")).strip()
        for segment in asr.get("segments", [])
        if isinstance(segment, dict)
        and float(segment.get("end", 0)) >= start
        and float(segment.get("start", 0)) <= end
        and str(segment.get("text", "")).strip()
    ]
    return " ".join(parts)


def selected_window_inputs(
    asr: dict[str, Any],
    windows: list[dict[str, Any]],
    max_windows: int,
    max_characters: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for window in windows[:max_windows]:
        transcript = transcript_for_window(asr, window)
        if not transcript:
            continue
        selected.append(
            {
                "window_id": str(window["window_id"]),
                "start_seconds": window.get("start_seconds"),
                "end_seconds": window.get("end_seconds"),
                "topic_tags": [
                    str(topic)
                    for topic in window.get("topic_tags", [])
                    if str(topic) in ALLOWED_TOPICS
                ],
                "transcript": transcript[:max_characters],
            }
        )
    return selected


def extraction_prompt(job: dict[str, Any], windows: list[dict[str, Any]]) -> str:
    payload = [
        {
            "window_id": window["window_id"],
            "time": f"{window['start_seconds']}-{window['end_seconds']}s",
            "candidate_topics": window["topic_tags"],
            "asr": window["transcript"],
        }
        for window in windows
    ]
    allowed_topics = ", ".join(sorted(ALLOWED_TOPICS))
    allowed_types = ", ".join(sorted(ALLOWED_CLAIM_TYPES))
    return (
        "你是羽毛球公开教学语料的审阅器。请从下面的私有 ASR 时间窗中提炼候选教学主张。"
        "输出严格 JSON 对象，字段仅为 topic_tags 和 claims。topic_tags 只可使用："
        f"{allowed_topics}。claims 最多 4 项；每项只可包含 claim_type（只可使用：{allowed_types}）、"
        "normalized_statement、observation_preconditions（字符串数组）、support_window_ids（字符串数组）和 "
        "visual_confirmation_required（布尔值）。每条 claim 的 normalized_statement 不超过 100 个中文字符，"
        "observation_preconditions 最多 3 条。每条 claim 还必须给出 support_window_ids（字符串数组），"
        "只能填写本次输入中实际存在的 window_id。"
        "normalized_statement 必须是简洁、原创、非逐字的概括，不能将 ASR 连续原句复制出来，不能声称教练本人审阅了任何人，"
        "不能把语音内容当作对动作视觉细节、力量、内旋或拍面角度的证明。涉及动作、接触、关节时序、力或器材实测时，"
        "visual_confirmation_required 必须为 true。证据不足时不要输出该项。\n"
        f"来源标题：{job['title']}\n时间窗：\n"
        + json.dumps(payload, ensure_ascii=False)
    )


def first_json_value(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return value if isinstance(value, dict) else None
    return None


def require_json_payload(text: str) -> dict[str, Any]:
    payload = first_json_value(text)
    if payload is None:
        raise ValueError("model response does not contain a complete JSON object")
    return payload


def normalized_text(value: object, maximum: int = 480) -> str:
    return " ".join(str(value or "").split())[:maximum]


def normalize_claim_payload(
    raw: object,
    *,
    allowed_topics: set[str] = ALLOWED_TOPICS,
    allowed_window_ids: set[str] | None = None,
) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    topic_tags = list(
        dict.fromkeys(
            str(topic)
            for topic in raw.get("topic_tags", [])
            if str(topic) in allowed_topics
        )
    )
    claims: list[dict[str, Any]] = []
    for item in raw.get("claims", []):
        if not isinstance(item, dict):
            continue
        claim_type = CLAIM_TYPE_ALIASES.get(
            str(item.get("claim_type", "")), str(item.get("claim_type", ""))
        )
        statement = normalized_text(item.get("normalized_statement"))
        if claim_type not in ALLOWED_CLAIM_TYPES or len(statement) < 12:
            continue
        preconditions = item.get("observation_preconditions", [])
        if isinstance(preconditions, str):
            preconditions = [preconditions]
        if not isinstance(preconditions, list):
            preconditions = []
        support_window_ids = item.get("support_window_ids", [])
        if isinstance(support_window_ids, str):
            support_window_ids = [support_window_ids]
        if not isinstance(support_window_ids, list):
            support_window_ids = []
        support_window_ids = list(
            dict.fromkeys(str(value) for value in support_window_ids)
        )
        if allowed_window_ids is not None:
            support_window_ids = [
                value for value in support_window_ids if value in allowed_window_ids
            ]
        if not support_window_ids:
            continue
        claims.append(
            {
                "claim_type": claim_type,
                "normalized_statement": statement,
                "observation_preconditions": [
                    normalized_text(value, maximum=220)
                    for value in preconditions
                    if normalized_text(value, maximum=220)
                ][:5],
                "support_window_ids": support_window_ids,
                "visual_confirmation_required": True,
                "evidence_level": "semantic_model_candidate_private",
            }
        )
    return {"topic_tags": topic_tags, "claims": claims[:8]}


def public_claim_summary(private: dict[str, Any]) -> dict[str, Any]:
    claims = []
    for claim in private.get("claims", []):
        if not isinstance(claim, dict):
            continue
        claims.append(
            {
                "claim_id": claim.get("claim_id"),
                "claim_type": claim.get("claim_type"),
                "normalized_statement": claim.get("normalized_statement"),
                "observation_preconditions": claim.get("observation_preconditions", []),
                "support_window_ids": claim.get("support_window_ids", []),
                "visual_confirmation_required": True,
                "evidence_level": claim.get(
                    "evidence_level", "semantic_model_candidate_private"
                ),
                "promotion_status": "requires_cross_source_and_visual_review",
            }
        )
    return {
        "job_id": private.get("job_id"),
        "source_id": private.get("source_id"),
        "title": private.get("title"),
        "status": private.get("status"),
        "topic_tags": private.get("topic_tags", []),
        "windows": [
            {
                "window_id": window.get("window_id"),
                "start_seconds": window.get("start_seconds"),
                "end_seconds": window.get("end_seconds"),
            }
            for window in private.get("windows", [])
            if isinstance(window, dict)
        ],
        "claims": claims,
        "boundary": (
            "This is a public-safe projection of a private semantic-model candidate. "
            "It is not a quote, a human coach review, or proof of visual biomechanics."
        ),
    }


def load_text_runtime(model_name: str) -> tuple[Any, Any, Any]:
    import torch
    from transformers import AutoConfig, AutoProcessor, Qwen3VLForConditionalGeneration

    config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
    config.base_model_tp_plan = None
    for nested_name in ["text_config", "vision_config"]:
        nested = getattr(config, nested_name, None)
        if nested is not None and hasattr(nested, "base_model_tp_plan"):
            nested.base_model_tp_plan = None
    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_name,
        config=config,
        torch_dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
    )
    return torch, processor, model


def infer_claims(
    runtime: tuple[Any, Any, Any], prompt: str, max_new_tokens: int
) -> str:
    torch, processor, model = runtime
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], padding=True, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    trimmed = [
        output_ids[len(input_ids) :]
        for input_ids, output_ids in zip(inputs.input_ids, generated)
    ]
    return processor.batch_decode(trimmed, skip_special_tokens=True)[0]


def main() -> None:
    args = parse_args()
    manifest = load_yaml(ROOT / args.manifest)
    windows_doc = load_yaml(ROOT / args.windows)
    grouped_windows = windows_by_job(windows_doc)
    output_root = ROOT / args.output_root
    runtime: tuple[Any, Any, Any] | None = None
    for job in select_jobs(manifest, args):
        output_path = output_root / f"{job['job_id']}.json"
        existing = read_json(output_path)
        if args.skip_ok and existing and existing.get("status") == "ok":
            print(f"{job['job_id']}\tskipped=ok", flush=True)
            continue
        asr = read_json(ROOT / job["private_paths"]["asr_json"])
        windows = selected_window_inputs(
            asr or {},
            grouped_windows.get(job["job_id"], []),
            args.max_windows_per_source,
            args.max_window_characters,
        )
        if not asr or asr.get("status") != "ok" or not windows:
            write_json(
                output_path,
                {
                    "status": "skipped",
                    "job_id": job["job_id"],
                    "source_id": job["source_id"],
                    "title": job["title"],
                    "reason": "missing_ok_asr_or_selected_teaching_windows",
                    "windows": [],
                    "claims": [],
                },
            )
            print(f"{job['job_id']}\tskipped=missing_inputs", flush=True)
            continue
        if runtime is None:
            runtime = load_text_runtime(args.model)
        prompt = extraction_prompt(job, windows)
        try:
            raw_response = infer_claims(runtime, prompt, args.max_new_tokens)
            normalized = normalize_claim_payload(
                require_json_payload(raw_response),
                allowed_window_ids={window["window_id"] for window in windows},
            )
            claims = [
                {"claim_id": f"{job['job_id']}-claim-{index:03d}", **claim}
                for index, claim in enumerate(normalized["claims"], start=1)
            ]
            output = {
                "status": "ok",
                "job_id": job["job_id"],
                "source_id": job["source_id"],
                "title": job["title"],
                "model": Path(args.model).name,
                "topic_tags": normalized["topic_tags"],
                "windows": windows,
                "claims": claims,
                "raw_prompt": prompt,
                "raw_model_response": raw_response,
            }
        except Exception as exc:
            output = {
                "status": "failed",
                "job_id": job["job_id"],
                "source_id": job["source_id"],
                "title": job["title"],
                "reason": f"{type(exc).__name__}: {exc}",
                "windows": windows,
                "claims": [],
            }
        write_json(output_path, output)
        print(
            f"{job['job_id']}\tstatus={output['status']}\tclaims={len(output['claims'])}",
            flush=True,
        )


if __name__ == "__main__":
    main()
