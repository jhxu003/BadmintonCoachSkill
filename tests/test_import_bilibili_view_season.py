from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_import_bilibili_view_season_outputs_episode_rows(tmp_path):
    payload = {
        "code": 0,
        "data": {
            "title": "刘辉教练告诉你杀球压不下去怎么办",
            "desc": "已获教练授权",
            "owner": {"name": "石宇奇b站头号铁粉"},
            "ugc_season": {
                "id": 1536706,
                "title": "8、杀球教程",
                "sections": [
                    {
                        "title": "杀球很平压不下去",
                        "episodes": [
                            {
                                "title": "刘辉教练带你解析杀球快和杀球重",
                                "bvid": "BV1Uo4y1x71B",
                                "page": {"duration": 351},
                                "arc": {
                                    "pubdate": 1683711000,
                                    "author": {"name": "石宇奇b站头号铁粉"},
                                },
                            }
                        ],
                    }
                ],
            }
        },
    }
    page = tmp_path / "view.json"
    page.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/import_bilibili_view_season.py",
            str(page),
            "--source-prefix",
            "LH_BILI_SEASON",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "LH_BILI_SEASON_BV1UO4Y1X71B" in result.stdout
    assert "刘辉教练带你解析杀球快和杀球重" in result.stdout
    assert "authorized" in result.stdout
    assert "smash" in result.stdout
    assert "season_id=1536706" in result.stdout
    assert "season=8、杀球教程" in result.stdout


def test_import_bilibili_view_season_keeps_public_status_without_authorization(tmp_path):
    payload = {
        "code": 0,
        "data": {
            "title": "刘辉羽毛球直播2022-11-04",
            "desc": "公开直播切片",
            "owner": {"name": "谁怜漂泊人"},
            "ugc_season": {
                "id": 1300706,
                "title": "刘辉羽毛球直播2022-11-04",
                "sections": [
                    {
                        "title": "直播切片",
                        "episodes": [
                            {
                                "title": "刘辉教练讲实战学习顺序",
                                "bvid": "BV1Public001",
                                "arc": {
                                    "pubdate": 1667570400,
                                    "author": {"name": "谁怜漂泊人"},
                                },
                            }
                        ],
                    }
                ],
            },
        },
    }
    page = tmp_path / "view-public.json"
    page.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/import_bilibili_view_season.py", str(page)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "LH_BILI_SEASON_BV1PUBLIC001" in result.stdout
    assert "\tpublic\tpublic\tvideo\t" in result.stdout
    assert "match_transfer" in result.stdout
