from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Literal, Protocol

from .phases import PhaseCandidate


@dataclass(frozen=True)
class VisualReview:
    frame_id: str
    confidence: str
    camera_view: str
    visible_facts: tuple[str, ...]
    limitations: tuple[str, ...]
    phase_assessment: Literal["plausible", "not_action", "unclear"] = "unclear"


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
            phase_assessment="unclear",
        )


class QwenLocalVisualReviewer:
    """Local Qwen adapter for schema-constrained still-frame review in a GPU worker."""

    def __init__(self, model_path: str, max_new_tokens: int = 256):
        self.model_path = model_path
        self.max_new_tokens = max(96, max_new_tokens)
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
            "Return exactly one minified JSON object and no markdown. "
            "Schema: {\"camera_view\":\"front|side|rear_side|unknown\","
            "\"phase_assessment\":\"plausible|not_action|unclear\","
            "\"confidence\":\"low|medium|high\","
            "\"visible_facts\":[\"snake_case,max_3\"],"
            "\"limitations\":[\"snake_case,max_3\"]}. "
            f"Assess requested badminton phase {candidate.phase}. "
            "Set not_action when this is a static talking, gesturing, or instruction shot rather "
            "than an athletic swing phase. Set unclear if the still cannot distinguish them. "
            "Use only visible facts. Never infer exact shuttle contact, racket-face angle, grip "
            "pressure, force, intent, true internal rotation, or 3D biomechanics."
        )
        messages = [{"role": "user", "content": [{"type": "image", "path": str(image_path)}, {"type": "text", "text": prompt}]}]
        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._processor(text=[text], images=[str(image_path)], return_tensors="pt", padding=True)
        inputs = inputs.to(self._model.device)
        generated = self._model.generate(**inputs, max_new_tokens=self.max_new_tokens)
        input_length = inputs.input_ids.shape[1]
        raw = self._processor.batch_decode(
            generated[:, input_length:], skip_special_tokens=True
        )[0].strip()
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return self._invalid_response(frame_id)
        try:
            payload = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return self._invalid_response(frame_id)
        confidence = payload.get("confidence") if payload.get("confidence") in {"low", "medium", "high"} else "low"
        camera_view = payload.get("camera_view")
        if camera_view not in {"front", "side", "rear_side", "unknown"}:
            camera_view = "unknown"
        assessment = payload.get("phase_assessment")
        if assessment not in {"plausible", "not_action", "unclear"}:
            assessment = "unclear"
        facts = tuple(
            str(item)
            for item in payload.get("visible_facts", [])[:3]
            if isinstance(item, str)
        )
        limitations = tuple(
            str(item)
            for item in payload.get("limitations", [])[:3]
            if isinstance(item, str)
        )
        return VisualReview(
            frame_id=frame_id,
            confidence=confidence,
            camera_view=camera_view,
            visible_facts=facts,
            limitations=limitations or ("still_frame_no_motion",),
            phase_assessment=assessment,
        )

    @staticmethod
    def _invalid_response(frame_id: str) -> VisualReview:
        return VisualReview(
            frame_id=frame_id,
            confidence="low",
            camera_view="unknown",
            visible_facts=(),
            limitations=("visual_model_invalid_response", "still_frame_no_motion"),
            phase_assessment="unclear",
        )
