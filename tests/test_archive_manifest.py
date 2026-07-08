from pathlib import Path

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
