#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Iterable

from common import BENCHMARK_ROOT, CONFIG_PATH, load_yaml, resolve_benchmark_path, write_json


RAW_ROOT = BENCHMARK_ROOT / "data" / "raw"
DEFAULT_DATASET_ROOT = RAW_ROOT / "BADS_CLL"
CATALOG_PATH = BENCHMARK_ROOT / "data" / "manifests" / "badminsense_catalog.json"


def iter_samples(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if isinstance(value.get("Info"), dict) and isinstance(value.get("Label"), dict):
            yield value
        else:
            for child in value.values():
                yield from iter_samples(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_samples(child)


def locate_gif(json_path: Path, dataset_root: Path, sample: dict[str, Any], index: int) -> Path:
    info = sample.get("Info", {})
    gif_value = sample.get("Gif")
    candidates: list[Path] = []
    if isinstance(gif_value, str) and gif_value:
        candidates.extend((json_path.parent / gif_value, dataset_root / gif_value))
    record_name = str(info.get("recordName") or json_path.stem)
    candidates.extend(
        (
            json_path.parent / f"{record_name}@{index}.gif",
            json_path.parent / f"{record_name}_{index}.gif",
        )
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    exact = list(json_path.parent.glob(f"*@{index}.gif"))
    if len(exact) == 1:
        return exact[0].resolve()
    raise FileNotFoundError(f"No GIF for sample {index} in {json_path}")


def parse_dataset(dataset_root: Path) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    errors: list[str] = []
    for json_path in sorted(dataset_root.rglob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{json_path}: {exc}")
            continue
        for index, sample in enumerate(iter_samples(payload)):
            info, label = sample["Info"], sample["Label"]
            try:
                media = locate_gif(json_path, dataset_root, sample, index)
                rating = float(label["actionEval"])
            except (KeyError, TypeError, ValueError, FileNotFoundError) as exc:
                errors.append(f"{json_path} sample {index}: {exc}")
                continue
            record_name = str(info.get("recordName") or json_path.parent.name)
            player_id = str(info.get("playerCode") or "")
            if not player_id:
                parts = record_name.split("_")
                player_id = parts[3] if len(parts) > 3 else record_name
            relative_media = media.relative_to(dataset_root.resolve())
            catalog.append(
                {
                    "sample_id": f"{record_name}@{index}",
                    "source": "BADS_CLL",
                    "player_id": player_id,
                    "experience": info.get("exp"),
                    "gender": info.get("gender"),
                    "stroke_type": label.get("actionType"),
                    "quality_rating": rating,
                    "impact_location": {"x": label.get("positionX"), "y": label.get("positionY")},
                    "media_path": str(relative_media),
                    "record_name": record_name,
                    "section": info.get("section"),
                }
            )
    if errors:
        error_path = CATALOG_PATH.with_name("badminsense_parse_errors.txt")
        error_path.parent.mkdir(parents=True, exist_ok=True)
        error_path.write_text("\n".join(errors) + "\n", encoding="utf-8")
    return catalog


def download_archive(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = ["gdown", url, "--output", str(destination), "--continue", "--fuzzy"]
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError("gdown is required for automatic Google Drive download") from exc


def extract_archive(archive: Path, destination: Path) -> Path:
    if destination.exists() and any(destination.iterdir()):
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(destination)
    json_roots = {path.parent for path in destination.rglob("*.json")}
    if not json_roots:
        raise RuntimeError(f"No BADS_CLL JSON files found after extracting {archive}")
    return destination


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    parser = argparse.ArgumentParser(description="Download, extract, and index BADS_CLL.")
    parser.add_argument("--archive", help="Use an existing official ZIP instead of downloading.")
    parser.add_argument("--dataset-root", help="Use an already extracted BADS_CLL directory.")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--force-catalog", action="store_true")
    args = parser.parse_args()

    dataset_root = resolve_benchmark_path(args.dataset_root) if args.dataset_root else DEFAULT_DATASET_ROOT
    archive = (
        Path(args.archive).expanduser().resolve()
        if args.archive
        else RAW_ROOT / str(config["dataset"]["archive_name"])
    )
    if not dataset_root.exists() or not any(dataset_root.iterdir()):
        if not archive.is_file():
            if args.skip_download:
                raise SystemExit(f"Dataset not found. Place the official archive at {archive}")
            download_archive(str(config["dataset"]["archive_url"]), archive)
        extract_archive(archive, dataset_root)
    elif archive.is_file() and archive.parent != RAW_ROOT:
        RAW_ROOT.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive, RAW_ROOT / archive.name)

    if CATALOG_PATH.exists() and not args.force_catalog:
        print(f"Catalog already exists: {CATALOG_PATH}")
        return
    catalog = parse_dataset(dataset_root)
    write_json(CATALOG_PATH, catalog)
    print(f"Indexed {len(catalog)} samples -> {CATALOG_PATH}")
    if len(catalog) != 848:
        raise SystemExit(f"Expected 848 valid samples, found {len(catalog)}; inspect parse errors before continuing")


if __name__ == "__main__":
    main()
