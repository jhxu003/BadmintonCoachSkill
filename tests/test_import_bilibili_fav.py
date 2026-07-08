from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_import_bilibili_fav_filters_relevant_public_metadata(tmp_path):
    page = tmp_path / "fav-page.json"
    page.write_text(
        json.dumps(
            {
                "code": 0,
                "data": {
                    "info": {"media_count": 2},
                    "medias": [
                        {
                            "title": "刘辉教练告诉你杀球压不下去怎么办",
                            "intro": "已获教练授权",
                            "bvid": "BV1WM4y1h7GY",
                            "pubtime": 1683043200,
                            "duration": 637,
                            "upper": {"name": "石宇奇b站头号铁粉"},
                        },
                        {
                            "title": "一顿能干3碗饭的下饭神菜",
                            "intro": "厨房小白轻松学会",
                            "bvid": "BV1sT411J7o5",
                            "pubtime": 1657868799,
                            "duration": 68,
                            "upper": {"name": "夏叔厨房"},
                        },
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/import_bilibili_fav.py",
            str(page),
            "--source-prefix",
            "LH_BILI_FAV",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "LH_BILI_FAV_BV1WM4Y1H7GY" in result.stdout
    assert "刘辉教练告诉你杀球压不下去怎么办" in result.stdout
    assert "authorized" in result.stdout
    assert "smash" in result.stdout
    assert "BV1sT411J7o5" not in result.stdout
