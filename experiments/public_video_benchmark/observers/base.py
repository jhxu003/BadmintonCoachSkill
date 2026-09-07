from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class SampledClip:
    frames: tuple[Image.Image, ...]
    timestamps_ms: tuple[float, ...]
    source_frame_count: int
    duration_ms: float


def sample_gif(path: Path, sampling_fps: float = 8.0, max_frames: int = 48) -> SampledClip:
    image = Image.open(path)
    frames: list[Image.Image] = []
    timestamps: list[float] = []
    elapsed = 0.0
    index = 0
    while True:
        try:
            image.seek(index)
        except EOFError:
            break
        frames.append(image.convert("RGB").copy())
        timestamps.append(elapsed)
        elapsed += float(image.info.get("duration", 100.0))
        index += 1
    if not frames:
        raise ValueError(f"GIF contains no frames: {path}")
    target_count = min(max_frames, len(frames), max(1, round(elapsed / 1000 * sampling_fps)))
    if len(frames) <= max_frames:
        indices = list(range(len(frames)))
    elif target_count == 1:
        indices = [len(frames) // 2]
    else:
        indices = sorted({round(i * (len(frames) - 1) / (target_count - 1)) for i in range(target_count)})
    return SampledClip(
        frames=tuple(frames[i] for i in indices),
        timestamps_ms=tuple(timestamps[i] for i in indices),
        source_frame_count=len(frames),
        duration_ms=elapsed,
    )


def extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Observer response must be a JSON object")
    return value


class BaseObserver:
    model_id: str

    def __init__(self, model_path: str, *, max_new_tokens: int = 2048) -> None:
        self.model_path = model_path
        self.max_new_tokens = max_new_tokens
        self.model: Any = None
        self.processor: Any = None

    def load(self) -> None:
        raise NotImplementedError

    def generate(self, clip: SampledClip, prompt: str) -> tuple[str, float, str]:
        if self.model is None or self.processor is None:
            self.load()
        import torch
        from qwen_vl_utils import process_vision_info

        content = [{"type": "image", "image": frame} for frame in clip.frames]
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]
        rendered = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[rendered], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt"
        )
        device = next(self.model.parameters()).device
        inputs = inputs.to(device)
        started = time.perf_counter()
        with torch.inference_mode():
            generated = self.model.generate(
                **inputs, max_new_tokens=self.max_new_tokens, do_sample=False, use_cache=True
            )
        runtime = time.perf_counter() - started
        trimmed = [output[len(source) :] for source, output in zip(inputs.input_ids, generated)]
        text = self.processor.batch_decode(trimmed, skip_special_tokens=True)[0]
        return text, runtime, str(device)

    def close(self) -> None:
        self.model = None
        self.processor = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
