from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_deduplication_map_records_public_metadata_run():
    data = yaml.safe_load(
        (ROOT / "data" / "corpus" / "deduplication-map.yaml").read_text(
            encoding="utf-8"
        )
    )
    summary = data["deduplication_run"]["summary"]

    assert summary["bilibili_season_episode_rows"] >= 406
    assert summary["exact_existing_bilibili_duplicates"] >= 23
    assert summary["new_bilibili_video_rows_merged"] >= 383
    assert summary["cross_platform_exact_duplicates_confirmed"] == 0
    assert len(data["exact_existing_duplicates"]) == summary[
        "exact_existing_bilibili_duplicates"
    ]
    assert any(
        check["platform_pair"] == ["YouTube", "Bilibili"]
        and check["status"] == "deferred"
        for check in data["blocked_or_deferred_duplicate_checks"]
    )
