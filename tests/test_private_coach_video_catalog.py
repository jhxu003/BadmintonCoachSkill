from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/build_private_coach_video_catalog.py"


def load_module():
    spec = importlib.util.spec_from_file_location("private_catalog_for_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def package(title: str, techniques: list[dict[str, object]]) -> dict[str, object]:
    return {
        "video": {
            "source_id": "SOURCE_001",
            "job_id": "job-001",
            "title": title,
            "url": "https://example.invalid/video",
            "duration_seconds": 42.0,
        },
        "techniques": techniques,
        "semantic_inventory": [],
    }


def test_catalog_keeps_multiple_technical_categories() -> None:
    module = load_module()
    record = module.video_record(
        package(
            "双打接发后平抽挡",
            [
                {"action": "serve_receive", "family_id": "serve_receive", "label_zh": "发接发"},
                {"action": "drive", "family_id": "midcourt_fast_exchange", "label_zh": "平抽挡"},
            ],
        ),
        module.Batch("coach", "教练", "batch"),
    )

    assert [item["id"] for item in record["categories"]] == [
        "midcourt_exchange",
        "serve_receive",
    ]
    assert {item["label_zh"] for item in record["techniques"]} == {"发接发", "平抽挡"}


def test_title_fallback_marks_non_instructional_content() -> None:
    module = load_module()
    record = module.video_record(
        package("来到上海旅游，放松一下", []), module.Batch("coach", "教练", "batch")
    )

    assert record["categories"] == [
        {"id": "non_instructional", "name": "非教学／生活／产品信息", "sources": ["title_fallback_non_instructional"]}
    ]
    assert record["evidence_status"] == "title_fallback_non_instructional"


def test_build_catalog_writes_media_free_private_viewer(tmp_path: Path) -> None:
    module = load_module()
    batch = tmp_path / "batch" / "videos" / "video-001"
    batch.mkdir(parents=True)
    (batch / "lesson-package.json").write_text(
        json.dumps(
            package(
                "后场杀球",
                [{"action": "smash", "family_id": "overhead", "label_zh": "杀球"}],
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    catalog = module.build_catalog(tmp_path, (module.Batch("coach", "教练", "batch"),))
    output = tmp_path / "private-output"
    module.write_catalog(catalog, output)

    exported = json.loads((output / "catalog.json").read_text(encoding="utf-8"))
    html = (output / "index.html").read_text(encoding="utf-8")
    assert exported["total_video_count"] == 1
    assert exported["coaches"][0]["category_counts"] == [
        {"id": "overhead_attack", "name": "后场头顶与进攻", "video_count": 1}
    ]
    assert "<video" not in html
    assert "episodes/" not in html
