from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Protocol

from .phases import PhaseCandidate


@dataclass(frozen=True)
class VisualReview:
    frame_id: str
    confidence: str
    camera_view: str
    visible_facts: tuple[str, ...]
    limitations: tuple[str, ...]


class VisualReviewer(Protocol):
    def review(self, candidate: PhaseCandidate, image_path: Path, frame_id: str) -> VisualReview:
        """Return only observable facts for an already selected candidate frame."""


class DisabledVisualReviewer:
    """Conservative default used when a VLM model is not configured."""

    def review(self, candidate: PhaseCandidate, image_path: Path, frame_id: str) -> VisualReview:
        return VisualReview(
            frame_id=frame_id,
            confidence="low",
            camera_view="unknown",
            visible_facts=(candidate.reason,),
            limitations=("visual_model_not_configured", "still_frame_no_motion"),
        )


class QwenLocalVisualReviewer:
    """Local Qwen adapter for schema-constrained still-frame review in a GPU worker."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._processor = None
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from transformers import AutoModelForImageTextToText, AutoProcessor
        except ImportError as error:
            raise RuntimeError("Transformers image-text runtime is unavailable") from error
        self._processor = AutoProcessor.from_pretrained(self.model_path)
        self._model = AutoModelForImageTextToText.from_pretrained(
            self.model_path, device_map="auto"
        )

    def review(self, candidate: PhaseCandidate, image_path: Path, frame_id: str) -> VisualReview:
        self._load()
        assert self._model is not None and self._processor is not None
        prompt = (
            "Inspect only visible facts in this badminton still frame. Return JSON with "
            "camera_view, confidence (low|medium|high), visible_facts (array), and limitations (array). "
            "Do not infer exact shuttle contact, racket-face angle, grip pressure, force, intent, "
            "true shoulder internal rotation, or 3D biomechanics. "
            f"The requested phase proxy is {candidate.phase}."
        )
        messages = [{"role": "user", "content": [{"type": "image", "path": str(image_path)}, {"type": "text", "text": prompt}]}]
        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._processor(text=[text], images=[str(image_path)], return_tensors="pt", padding=True)
        inputs = inputs.to(self._model.device)
        generated = self._model.generate(**inputs, max_new_tokens=180)
        raw = self._processor.batch_decode(generated, skip_special_tokens=True)[0]
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return DisabledVisualReviewer().review(candidate, image_path, frame_id)
        try:
            payload = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return DisabledVisualReviewer().review(candidate, image_path, frame_id)
        confidence = payload.get("confidence") if payload.get("confidence") in {"low", "medium", "high"} else "low"
        facts = tuple(str(item) for item in payload.get("visible_facts", []) if isinstance(item, str))
        limitations = tuple(str(item) for item in payload.get("limitations", []) if isinstance(item, str))
        return VisualReview(
            frame_id=frame_id,
            confidence=confidence,
            camera_view=str(payload.get("camera_view", "unknown")),
            visible_facts=facts,
            limitations=limitations or ("still_frame_no_motion",),
        )
