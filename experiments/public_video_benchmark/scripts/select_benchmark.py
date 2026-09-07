#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import BENCHMARK_ROOT, CONFIG_PATH, load_json, load_yaml, write_json


def diverse_pick(pool: list[dict[str, Any]], count: int, rng: random.Random) -> list[dict[str, Any]]:
    pool = [dict(item) for item in pool]
    rng.shuffle(pool)
    chosen: list[dict[str, Any]] = []
    used_players: set[str] = set()
    for item in pool:
        player = str(item.get("player_id", ""))
        if player not in used_players:
            chosen.append(item)
            used_players.add(player)
        if len(chosen) == count:
            return chosen
    for item in pool:
        if item not in chosen:
            chosen.append(item)
        if len(chosen) == count:
            return chosen
    raise ValueError(f"Only {len(chosen)} samples available; need {count}")


def stratified_selection(
    catalog: list[dict[str, Any]], actions: list[str], samples_per_cell: int, seed: int
) -> list[dict[str, Any]]:
    by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in catalog:
        if item.get("stroke_type") in actions:
            by_action[str(item["stroke_type"])].append(item)
    selected: list[dict[str, Any]] = []
    rng = random.Random(seed)
    for action in actions:
        rows = sorted(by_action[action], key=lambda row: (float(row["quality_rating"]), row["sample_id"]))
        if len(rows) < samples_per_cell * 3:
            raise ValueError(f"Not enough {action} samples")
        ratings = [float(row["quality_rating"]) for row in rows]
        median = statistics.median(ratings)
        quarter = max(samples_per_cell, len(rows) // 4)
        pools = {
            "low": rows[:quarter],
            "medium": sorted(rows, key=lambda row: (abs(float(row["quality_rating"]) - median), row["sample_id"])),
            "high": rows[-quarter:],
        }
        action_min, action_max = min(ratings), max(ratings)
        picked_by_tier: dict[str, list[dict[str, Any]]] = {}
        used_ids: set[str] = set()
        # Reserve both tails before selecting the median-nearest group so cells stay disjoint.
        for tier in ("low", "high", "medium"):
            available = [item for item in pools[tier] if str(item["sample_id"]) not in used_ids]
            picked_by_tier[tier] = diverse_pick(available, samples_per_cell, rng)
            used_ids.update(str(item["sample_id"]) for item in picked_by_tier[tier])
        for tier in ("low", "medium", "high"):
            for item in picked_by_tier[tier]:
                item["quality_tier"] = tier
                item["quality_rating_normalized"] = (
                    (float(item["quality_rating"]) - action_min) / (action_max - action_min)
                    if action_max > action_min
                    else 0.0
                )
                selected.append(item)
    return selected


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    parser = argparse.ArgumentParser(description="Select the reproducible 4 x 3 BADS_CLL benchmark.")
    parser.add_argument("--catalog", default="data/manifests/badminsense_catalog.json")
    parser.add_argument("--output", default="data/manifests/badminsense_60.json")
    parser.add_argument("--samples-per-cell", type=int, default=int(config["selection"]["samples_per_cell"]))
    parser.add_argument("--seed", type=int, default=int(config["selection"]["seed"]))
    args = parser.parse_args()
    catalog = load_json(BENCHMARK_ROOT / args.catalog)
    selected = stratified_selection(catalog, list(config["selection"]["actions"]), args.samples_per_cell, args.seed)
    output = BENCHMARK_ROOT / args.output
    write_json(output, selected)
    print(f"Selected {len(selected)} samples -> {output}")


if __name__ == "__main__":
    main()
