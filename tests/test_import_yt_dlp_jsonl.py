from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_import_yt_dlp_jsonl_outputs_source_index_rows(tmp_path):
    sample = tmp_path / "yt.jsonl"
    sample.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "abc123",
                        "title": "高远球击球点怎么找",
                        "webpage_url": "https://www.youtube.com/watch?v=abc123",
                        "upload_date": "20260701",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "id": "def456",
                        "title": "杀球发力和转髋顺序",
                        "url": "https://www.youtube.com/watch?v=def456",
                        "timestamp": None,
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/import_yt_dlp_jsonl.py",
            str(sample),
            "--source-prefix",
            "LH_YT_AUTO",
            "--authorization-status",
            "official",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "LH_YT_AUTO_ABC123" in result.stdout
    assert "LH_YT_AUTO_DEF456" in result.stdout
    assert "high_clear" in result.stdout
    assert "smash" in result.stdout
    assert "hip_rotation" in result.stdout
    assert "official" in result.stdout
