from pathlib import Path
import csv


ROOT = Path(__file__).resolve().parents[1]


def test_public_access_log_records_blocked_channel_fetches():
    path = ROOT / "data" / "corpus" / "public-access-log.tsv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    assert rows
    assert any(
        row["platform"] == "YouTube" and row["status"] == "blocked"
        for row in rows
    )
    assert all(row["attempted_at"] for row in rows)
    assert all(row["command_or_url"] for row in rows)
    assert all(row["result"] for row in rows)
