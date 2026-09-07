from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "experiments" / "public_video_benchmark"
sys.path.insert(0, str(BENCHMARK / "scripts"))
sys.path.insert(0, str(BENCHMARK))

from observers.base import extract_json, sample_gif  # noqa: E402
from select_benchmark import stratified_selection  # noqa: E402


def test_stratified_selection_is_reproducible_and_diverse() -> None:
    catalog = []
    for action in ("BackhandTransition", "ForehandHigh", "ForehandLob", "ForehandKill"):
        for index in range(40):
            catalog.append(
                {
                    "sample_id": f"{action}-{index}",
                    "stroke_type": action,
                    "quality_rating": float(index),
                    "player_id": f"p{index % 8}",
                }
            )
    actions = ["BackhandTransition", "ForehandHigh", "ForehandLob", "ForehandKill"]
    first = stratified_selection(catalog, actions, 5, 42)
    second = stratified_selection(catalog, actions, 5, 42)
    assert first == second
    assert len(first) == 60
    assert len({row["sample_id"] for row in first}) == 60
    for action in actions:
        for tier in ("low", "medium", "high"):
            cell = [row for row in first if row["stroke_type"] == action and row["quality_tier"] == tier]
            assert len(cell) == 5
            assert len({row["player_id"] for row in cell}) == 5


def test_sample_gif_keeps_all_short_clip_frames(tmp_path: Path) -> None:
    frames = [Image.new("RGB", (8, 8), (index * 20, 0, 0)) for index in range(6)]
    path = tmp_path / "stroke.gif"
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=50, loop=0)
    clip = sample_gif(path, sampling_fps=8, max_frames=48)
    assert len(clip.frames) == 6
    assert clip.timestamps_ms == (0.0, 50.0, 100.0, 150.0, 200.0, 250.0)


def test_extract_json_accepts_fenced_json() -> None:
    assert extract_json('```json\n{"action":"unknown"}\n```') == {"action": "unknown"}


def test_action_mapping_targets_current_schema_actions() -> None:
    import yaml

    schema = json.loads((ROOT / "schemas" / "video-observation.schema.json").read_text())
    mapping = yaml.safe_load((BENCHMARK / "configs" / "action_mapping.yaml").read_text())
    allowed = set(schema["properties"]["action"]["enum"])
    assert {item["skill_action"] for item in mapping.values()} <= allowed
