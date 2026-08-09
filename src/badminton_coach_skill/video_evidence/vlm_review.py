from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any, Literal, Protocol

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
        # Pin the checkpoint's original processor path.  Newer Transformers
        # versions silently select a fast processor by default, which can
        # change visual-token preprocessing and make the same reviewed frame
        # yield different conservative gate results across deployments.
        self._processor = AutoProcessor.from_pretrained(self.model_path, use_fast=False)
        model_options: dict[str, object] = {
            "device_map": "auto",
            "low_cpu_mem_usage": True,
        }
        # Qwen-VL weights need not be materialized in float32 on a CUDA
        # worker.  Keeping the model in BF16 (or FP16 on older cards) leaves
        # room for pose inference and image-generation activations, while the
        # review prompt and its conservative evidence policy stay unchanged.
        try:
            import torch

            if torch.cuda.is_available():
                model_options["dtype"] = (
                    torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                )
        except ImportError:
            pass
        self._model = AutoModelForImageTextToText.from_pretrained(
            self.model_path, **model_options
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
            "Use not_action only as a high-certainty exclusion: the person must be clearly "
            "stationary, talking, or making a small explanatory gesture rather than performing "
            "athletic movement. Set unclear if one still cannot distinguish them. "
            "A visibly airborne player, a racket arm in an overhead swing, a lunge, or an "
            "obvious badminton practice swing/drill is plausible even when the shuttle is not "
            "visible or the moving racket is motion-blurred; do not reject it merely because it "
            "is a filmed demonstration or instruction. "
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

    def close(self) -> None:
        """Release the model explicitly when a larger local tier is needed."""
        self._model = None
        self._processor = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            return None


class _QwenLocalJsonModel:
    """Small shared adapter for bounded multi-image JSON generation.

    It is intentionally private: callers expose typed route/observation
    contracts instead of propagating raw model output through the application.
    """

    def __init__(
        self, model_path: str, max_new_tokens: int, *, max_image_pixels: int = 512 * 28 * 28
    ) -> None:
        self.model_path = model_path
        self.max_new_tokens = max(96, max_new_tokens)
        self.max_image_pixels = max(28 * 28, max_image_pixels)
        self._processor: Any | None = None
        self._model: Any | None = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from transformers import AutoModelForImageTextToText, AutoProcessor
        except ImportError as error:
            raise RuntimeError("Transformers image-text runtime is unavailable") from error
        self._processor = AutoProcessor.from_pretrained(
            self.model_path, use_fast=False, max_pixels=self.max_image_pixels
        )
        options: dict[str, object] = {"device_map": "auto", "low_cpu_mem_usage": True}
        try:
            import torch

            if torch.cuda.is_available():
                options["dtype"] = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        except ImportError:
            pass
        self._model = AutoModelForImageTextToText.from_pretrained(self.model_path, **options)

    def generate_json(self, image_paths: tuple[Path, ...], prompt: str) -> dict[str, object] | None:
        if not image_paths:
            return None
        self._load()
        assert self._model is not None and self._processor is not None
        content = [{"type": "image", "path": str(path)} for path in image_paths]
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]
        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._processor(
            text=[text], images=[str(path) for path in image_paths], return_tensors="pt", padding=True
        ).to(self._model.device)
        generated = self._model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=False)
        input_length = inputs.input_ids.shape[1]
        raw = self._processor.batch_decode(generated[:, input_length:], skip_special_tokens=True)[0].strip()
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def close(self) -> None:
        self._model = None
        self._processor = None
        try:
            import gc
            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            return None


class QwenLocalActionRouter:
    """3B local VLM action-router for conservative multi-action proposals."""

    def __init__(
        self,
        model_path: str,
        *,
        max_new_tokens: int = 320,
        maximum_samples: int = 24,
        minimum_duration_ms: int = 1500,
        maximum_units: int = 5,
    ) -> None:
        self._model = _QwenLocalJsonModel(model_path, max_new_tokens)
        self.maximum_samples = max(4, maximum_samples)
        self.minimum_duration_ms = max(800, minimum_duration_ms)
        self.maximum_units = max(1, maximum_units)

    @staticmethod
    def _routing_contact_sheet(
        image_paths: list[Path], timestamps_ms: list[int], route_dir: Path
    ) -> tuple[Path, ...]:
        """Give the router one ordered visual timeline instead of many images.

        A small VLM is more reliable at comparing movement across a labelled
        contact sheet than at retaining twelve separate image inputs.  The
        sheet is private worker media; if Pillow cannot read any sampled
        image, callers retain the original ordered-image fallback.
        """
        try:
            from PIL import Image, ImageDraw

            # A badminton stroke can happen in well under two seconds.  For a
            # short learner upload, squeezing seven or twelve samples into a
            # small 3-column sheet made the full body and racket too small for
            # the routing tier to reliably distinguish a real stroke from an
            # explanation.  Two columns retain a complete timeline while
            # giving the model materially more pixels per athlete.  The model
            # adapter still bounds the resulting sheet to its visual-token
            # budget before inference.
            columns = 2
            tile_width, tile_height, caption_height, gutter = 448, 252, 24, 6
            rows = (len(image_paths) + columns - 1) // columns
            canvas = Image.new(
                "RGB",
                (
                    columns * tile_width + (columns + 1) * gutter,
                    rows * (tile_height + caption_height) + (rows + 1) * gutter,
                ),
                "#101820",
            )
            draw = ImageDraw.Draw(canvas)
            for index, (image_path, timestamp_ms) in enumerate(zip(image_paths, timestamps_ms)):
                with Image.open(image_path) as image:
                    frame = image.convert("RGB")
                    frame.thumbnail((tile_width, tile_height))
                    tile = Image.new("RGB", (tile_width, tile_height), "#05080b")
                    x_offset = (tile_width - frame.width) // 2
                    y_offset = (tile_height - frame.height) // 2
                    tile.paste(frame, (x_offset, y_offset))
                row, column = divmod(index, columns)
                x = gutter + column * (tile_width + gutter)
                y = gutter + row * (tile_height + caption_height + gutter)
                canvas.paste(tile, (x, y))
                draw.text((x + 4, y + tile_height + 2), f"{index + 1} · {timestamp_ms}ms", fill="#f4f7f9")
            contact_sheet = route_dir / "timeline-contact-sheet.jpg"
            contact_sheet.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(contact_sheet, quality=90, optimize=True)
            return (contact_sheet,)
        except (ImportError, OSError):
            return tuple(image_paths)

    def route(self, video_path: Path, output_dir: Path) -> tuple[object, ...]:
        # Local import avoids a worker -> vlm -> agent import cycle.
        from .agent import ActionRoute, ROUTABLE_ACTIONS
        from .ffmpeg import extract_frame, probe_video

        metadata = probe_video(video_path)
        if metadata.duration_ms < self.minimum_duration_ms:
            return ()
        # A one-second cadence over-samples a 5–10 second badminton stroke:
        # the contact sheet then makes an already small moving athlete
        # illegibly tiny.  Retain four temporal checkpoints at minimum, and
        # add detail only every 2.5 seconds for longer uploads.  This is a
        # routing view, not the action package: the next tier still extracts
        # seven ordered phase anchors at the original video rate.
        sample_count = min(
            self.maximum_samples,
            max(4, (metadata.duration_ms + 2_499) // 2_500),
        )
        route_dir = output_dir / "private" / "agent-routing"
        image_paths: list[Path] = []
        image_timestamps: list[int] = []
        for index in range(sample_count):
            # Container duration can extend a few milliseconds past the final
            # decodable frame. Sampling each time bucket at its midpoint
            # avoids treating that harmless tail discrepancy as a failed
            # learner upload, while still covering the whole motion timeline.
            timestamp_ms = min(
                metadata.duration_ms - 1,
                ((2 * index + 1) * metadata.duration_ms) // (2 * sample_count),
            )
            image_path = route_dir / f"sample-{timestamp_ms}.jpg"
            try:
                extract_frame(video_path, timestamp_ms, image_path)
            except (CalledProcessError, OSError):
                # A bad terminal seek or one corrupt decode must not turn a
                # bounded router into an infrastructure failure.  Fewer than
                # four surviving samples are too little temporal evidence and
                # are rejected below.
                continue
            image_paths.append(image_path)
            image_timestamps.append(timestamp_ms)
        if len(image_paths) < 4:
            return ()
        sample_map = ", ".join(
            f"{index + 1}={timestamp_ms}ms"
            for index, timestamp_ms in enumerate(image_timestamps)
        )
        prompt = (
            "Return ONLY one JSON object, with no prose or markdown. The contact sheet is a private "
            "badminton video timeline read left-to-right then top-to-bottom. Choose one sustained "
            "single-player athletic action, not talking, titles, static poses, or gestures. "
            f"Samples: {sample_map}. Return {{\"action\":\"one_allowed_action\","
            "\"start_sample\":integer,\"end_sample\":integer,\"confidence\":number}. "
            "Sample indices are 1-based; choose a complete motion spanning at least three samples "
            "(end_sample is at least start_sample plus 2). "
            f"Allowed actions: {', '.join(sorted(ROUTABLE_ACTIONS))}. "
            "If no supported sustained action is visible, return {\"action\":\"unknown\",\"confidence\":0.0}."
        )
        router_images = self._routing_contact_sheet(image_paths, image_timestamps, route_dir)
        payload = self._model.generate_json(router_images, prompt) or {}
        raw_units: object = payload.get("units", []) if isinstance(payload, dict) else []
        # Smaller local Qwen checkpoints occasionally collapse a one-item
        # ``units`` array into its object while retaining the complete route
        # fields.  It is still only a *candidate*: normalize that bounded
        # shape here and let the same action/time/confidence gates below make
        # the acceptance decision.  Free text or partial objects remain
        # rejected.
        if (
            isinstance(payload, dict)
            and ("units" not in payload or not isinstance(raw_units, list))
            and {"action", "confidence"}.issubset(payload)
            and (
                {"start_sample", "end_sample"}.issubset(payload)
                or {"start_ms", "end_ms"}.issubset(payload)
            )
        ):
            raw_units = [{**payload, "decision": str(payload.get("decision", "candidate"))}]
        routes: list[ActionRoute] = []
        if not isinstance(raw_units, list):
            return ()
        for raw in raw_units:
            if not isinstance(raw, dict):
                continue
            # The public router schema intentionally has no ``decision``
            # field: a complete object with one allowed action, an ordered
            # sample range, and bounded confidence is itself a candidate.
            # Qwen sometimes wraps that exact schema in ``units`` rather than
            # returning the compact one-item shape.  Treat the omitted field
            # as candidate in both forms; explicit ``not_action`` or
            # ``unclear`` remains rejected below.
            if str(raw.get("decision", "candidate")) != "candidate":
                continue
            action = str(raw.get("action", ""))
            if action not in ROUTABLE_ACTIONS:
                continue
            try:
                confidence = float(raw.get("confidence", 0.0))
            except (TypeError, ValueError):
                continue
            try:
                start_sample = int(raw["start_sample"])
                end_sample = int(raw["end_sample"])
            except (KeyError, TypeError, ValueError):
                start_sample = 0
                end_sample = 0
            # The contact-sheet captions include both a 1-based ordinal and
            # a millisecond timestamp.  Qwen can faithfully select the
            # latter while placing it in the ``*_sample`` fields.  Normalize
            # only an *exact* known timestamp back to its corresponding
            # ordinal; a free-form number is never treated as timing.
            sample_index_by_timestamp = {
                timestamp_ms: index + 1
                for index, timestamp_ms in enumerate(image_timestamps)
            }
            if (
                start_sample not in range(1, len(image_timestamps) + 1)
                and start_sample in sample_index_by_timestamp
                and end_sample in sample_index_by_timestamp
            ):
                start_sample = sample_index_by_timestamp[start_sample]
                end_sample = sample_index_by_timestamp[end_sample]
            if 1 <= start_sample + 2 <= end_sample <= len(image_timestamps):
                sample_spacing = max(
                    500,
                    image_timestamps[end_sample - 1] - image_timestamps[end_sample - 2],
                )
                # A router selects the visible *core* of an action.  Preserve
                # the immediately preceding sampled context so downstream
                # seven-stage extraction can inspect preparation rather than
                # beginning halfway through a swing.  This only widens a
                # confirmed candidate window inside the uploaded video; it
                # does not assert that the action began at the wider boundary.
                start_ms = max(
                    0,
                    image_timestamps[start_sample - 1] - sample_spacing,
                )
                end_ms = min(
                    metadata.duration_ms,
                    image_timestamps[end_sample - 1] + sample_spacing // 2,
                )
            else:
                # Keep backward compatibility with an adapter that already
                # provides scalar timestamps, but never coerce a model's
                # arrays, bounding boxes, or partial coordinates into time.
                try:
                    start_ms = max(0, int(raw.get("start_ms", 0)))
                    end_ms = min(metadata.duration_ms, int(raw.get("end_ms", 0)))
                except (TypeError, ValueError):
                    continue
            if end_ms - start_ms < self.minimum_duration_ms or not 0.0 <= confidence <= 1.0:
                continue
            routes.append(
                ActionRoute(
                    unit_id=f"agent-{len(routes) + 1:02d}",
                    action=action,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    confidence=confidence,
                    reasons=("qwen_3b_temporal_route",),
                )
            )
        accepted: list[ActionRoute] = []
        for route in sorted(routes, key=lambda item: (-item.confidence, item.start_ms, item.action)):
            if any(not (route.end_ms <= item.start_ms or route.start_ms >= item.end_ms) for item in accepted):
                continue
            accepted.append(route)
            if len(accepted) == self.maximum_units:
                break
        return tuple(sorted(accepted, key=lambda item: item.start_ms))

    def close(self) -> None:
        self._model.close()


class QwenLocalSegmentObserver:
    """7B local VLM that fills only a caller-provided observation vocabulary."""

    def __init__(self, model_path: str, *, max_new_tokens: int = 480) -> None:
        self._model = _QwenLocalJsonModel(model_path, max_new_tokens)

    @staticmethod
    def _priority_paths(action: str, allowed_values: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
        """Order a small number of independently verifiable 2D proxies.

        Asking a compact local VLM to choose one observation from a long mix
        of upper-body, lower-body and time-series rubrics consistently caused
        it to return ``low`` even for an otherwise unmistakable proxy.  A
        short, action-specific sequence of *single-field* checks makes the
        evidence question precise without broadening what the model may say.
        The first high answer stops the pass; all other fields stay unknown.
        """
        overhead = (
            "phase_observations.arm_path",
            "elbow_height_before_hit",
            "racket_side_structure",
            "follow_through",
            "phase_observations.elbow_track",
            "phase_observations.swing_path",
        )
        movement = (
            "footwork_observations.landing",
            "footwork_observations.recovery",
            "footwork_observations.arrival",
            "footwork_observations.confirmation_step",
            "footwork_observations.rear_turn",
            "footwork_observations.first_step",
        )
        if action in {"high_clear", "smash", "drop"}:
            preferred = (*overhead[:3], *movement[:3], *overhead[3:], *movement[3:])
        elif action in {"rear_footwork", "front_footwork", "net"}:
            preferred = (*movement[:3], *overhead[:3], *movement[3:], *overhead[3:])
        else:
            preferred = (*overhead, *movement)
        remaining = tuple(path for path in sorted(allowed_values) if path not in preferred)
        # A complete user run must remain bounded even for a broad merged
        # three-coach vocabulary.  The first six cover the visible proxy
        # families that are meaningful for this supported single-player path.
        return tuple(path for path in (*preferred, *remaining) if path in allowed_values)[:6]

    @staticmethod
    def _project_response(
        payload: dict[str, object] | None,
        allowed_values: dict[str, tuple[str, ...]],
    ) -> dict[str, object]:
        if not isinstance(payload, dict):
            return {"confidence": "low"}
        confidence = str(payload.get("confidence", "low"))
        result: dict[str, object] = {
            "confidence": confidence if confidence in {"low", "medium", "high"} else "low",
            "camera_view": str(payload.get("camera_view", "unknown")),
        }
        observations = payload.get("observations", payload)
        if not isinstance(observations, dict):
            return result
        for path, values in allowed_values.items():
            candidate = observations.get(path)
            if not isinstance(candidate, str) or candidate not in values:
                continue
            current: dict[str, object] = result
            parts = path.split(".")
            for part in parts[:-1]:
                nested = current.get(part)
                if not isinstance(nested, dict):
                    nested = {}
                    current[part] = nested
                current = nested
            current[parts[-1]] = candidate
        return result

    @staticmethod
    def _projected_value(payload: dict[str, object], path: str) -> object:
        current: object = payload
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    def observe(
        self,
        *,
        action: str,
        image_paths: tuple[Path, ...],
        base_observation: dict[str, object],
        allowed_values: dict[str, tuple[str, ...]],
    ) -> dict[str, object]:
        fallback: dict[str, object] = {"confidence": "low", "camera_view": "unknown"}
        for path in self._priority_paths(action, allowed_values):
            values = allowed_values[path]
            vocabulary = {path: ["unknown", *values]}
            prompt = (
                "Return ONLY one JSON object, with no prose or markdown. The seven ordered images show a "
                f"continuous learner badminton {action} from preparation through recovery. Return exactly "
                "these top-level keys: confidence, camera_view, observations. confidence is low, medium, or high; "
                "camera_view is front, side, rear_side, or unknown. observations is a flat object whose keys and "
                f"values must come only from this vocabulary: {json.dumps(vocabulary, ensure_ascii=False)}. "
                "Choose at most one observation: the single clearest listed proxy across the complete sequence. "
                "Return high only for that clear proxy; otherwise return low with an empty observations object. "
                "Do not use medium. Omit every unclear or unlisted field rather than guessing. Do not diagnose or "
                "infer contact, racket face, grip, force, internal rotation, 3D mechanics, opponent intent, "
                "tactics, equipment, or pain."
            )
            result = self._project_response(
                self._model.generate_json(image_paths, prompt), {path: values}
            )
            if result.get("camera_view") != "unknown":
                fallback["camera_view"] = result["camera_view"]
            if (
                result.get("confidence") == "high"
                and self._projected_value(result, path) in values
            ):
                return result
        return fallback

    def close(self) -> None:
        self._model.close()
