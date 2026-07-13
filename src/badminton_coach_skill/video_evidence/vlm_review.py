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
            "A clearly visible athletic badminton practice swing or drill remains plausible even "
            "if no shuttle is visible; do not reject it solely because it is demonstrated for instruction. "
            "For a top_elbow frame, use visible_facts racket_side_frame_collapsed only when the "
            "racket-side preparation frame is visibly collapsed; use racket_side_frame_stable only "
            "when that frame is visibly stable; otherwise omit both. "
            "Use only visible facts. Never infer exact shuttle contact, racket-face angle, grip "
            "pressure, force, intent, true internal rotation, or 3D biomechanics."
        )
        messages = [{"role": "user", "content": [{"type": "image", "path": str(image_path)}, {"type": "text", "text": prompt}]}]
        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._processor(text=[text], images=[str(image_path)], return_tensors="pt", padding=True)
        inputs = inputs.to(self._model.device)
        generated = self._model.generate(
            **inputs, max_new_tokens=self.max_new_tokens, do_sample=False
        )
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
        if not isinstance(payload, dict):
            return self._invalid_response(frame_id)
        required_fields = (
            "camera_view",
            "phase_assessment",
            "confidence",
            "visible_facts",
            "limitations",
        )
        if any(field not in payload for field in required_fields):
            return self._invalid_response(frame_id)
        raw_confidence = payload["confidence"]
        camera_view = payload["camera_view"]
        assessment = payload["phase_assessment"]
        visible_facts = payload["visible_facts"]
        limitations = payload["limitations"]
        if (
            not all(isinstance(value, str) for value in (raw_confidence, camera_view, assessment))
            or not isinstance(visible_facts, list)
            or not isinstance(limitations, list)
            or not all(isinstance(item, str) for item in (*visible_facts, *limitations))
        ):
            return self._invalid_response(frame_id)
        confidence = raw_confidence if raw_confidence in {"low", "medium", "high"} else "low"
        if camera_view not in {"front", "side", "rear_side", "unknown"}:
            camera_view = "unknown"
        if assessment not in {"plausible", "not_action", "unclear"}:
            assessment = "unclear"
        facts = tuple(
            str(item)
            for item in visible_facts[:3]
            if isinstance(item, str)
        )
        limitations = tuple(
            str(item)
            for item in limitations[:3]
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
