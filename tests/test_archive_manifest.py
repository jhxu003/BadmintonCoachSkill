from pathlib import Path
import re

import yaml

from badminton_coach_skill.source_index import read_source_index


ROOT = Path(__file__).resolve().parents[1]


def test_bilibili_archive_manifest_tracks_full_public_list_attempt():
    manifest = yaml.safe_load(
        (ROOT / "data" / "corpus" / "archive-manifest.yaml").read_text(
            encoding="utf-8"
        )
    )
    source_ids = {
        row["source_id"] for row in read_source_index(ROOT / "data" / "source-index.tsv")
    }

    archive = next(
        item for item in manifest["archives"] if item["archive_id"] == "bili_fav_73830778"
    )
    assert archive["expected_public_count"] == 326
    assert archive["fetched_public_count"] >= 322
    assert archive["filtered_relevant_count"] >= 10
    assert archive["status"] in {"partially_indexed", "indexed_needs_timestamp_review"}
    assert archive["unavailable_public_count"] == (
        archive["expected_public_count"] - archive["fetched_public_count"]
    )
    assert archive["merged_source_ids"]
    assert set(archive["merged_source_ids"]).issubset(source_ids)


def test_bilibili_ugc_season_archives_match_source_index_counts():
    manifest = yaml.safe_load(
        (ROOT / "data" / "corpus" / "archive-manifest.yaml").read_text(
            encoding="utf-8"
        )
    )
    source_rows = read_source_index(ROOT / "data" / "source-index.tsv")
    season_archives = [
        archive
        for archive in manifest["archives"]
        if str(archive["archive_id"]).startswith("bili_ugc_season_")
    ]

    assert len(season_archives) >= 7
    assert sum(archive["fetched_public_count"] for archive in season_archives) >= 406
    assert sum(archive["merged_new_source_count"] for archive in season_archives) >= 383
    assert sum(archive["duplicate_or_existing_count"] for archive in season_archives) >= 23

    for archive in season_archives:
        season_id = str(archive["season_id"])
        indexed_rows = [
            row for row in source_rows if f"season_id={season_id};" in row["notes"]
        ]
        assert len(indexed_rows) == archive["merged_new_source_count"]


def test_bilibili_video_source_rows_are_deduplicated_by_bvid():
    rows = read_source_index(ROOT / "data" / "source-index.tsv")
    bvids = []
    for row in rows:
        if row["platform"] != "Bilibili" or row["source_type"] != "video":
            continue
        match = re.search(r"(BV[0-9A-Za-z]+)", row["url"])
        if match:
            bvids.append(match.group(1).lower())

    assert len(bvids) >= 400
    assert len(bvids) == len(set(bvids))
