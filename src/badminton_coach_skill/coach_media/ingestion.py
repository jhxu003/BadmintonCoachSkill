from __future__ import annotations

from pathlib import Path
import shutil

from ..video_evidence.contracts import CoachReference


def cache_reference_image(reference: CoachReference, image_path: Path, cache_root: Path) -> CoachReference:
    """Copy an already-authorized extracted reference frame into private cache storage."""
    if not image_path.is_file():
        raise FileNotFoundError(image_path)
    relative = Path(reference.coach_id) / reference.source_id / f"{reference.timestamp_ms}.jpg"
    target = cache_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image_path, target)
    return CoachReference(
        reference_id=reference.reference_id,
        coach_id=reference.coach_id,
        source_id=reference.source_id,
        phase=reference.phase,
        timestamp_ms=reference.timestamp_ms,
        source_url=reference.source_url,
        confidence=reference.confidence,
        actions=reference.actions,
        framework_ids=reference.framework_ids,
        availability="cached",
        media_key=str(relative),
        title=reference.title,
        window_start_ms=reference.window_start_ms,
        window_end_ms=reference.window_end_ms,
        visible_facts=reference.visible_facts,
        limitations=reference.limitations,
    )
