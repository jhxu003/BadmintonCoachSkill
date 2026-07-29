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


def test_public_directory_routes_by_coach_system_not_candidate_window_union() -> None:
    module = load_module()
    cases = [
        (
            "liu-hui",
            "5u版李宁90New评测完整版！双打抽档利器打感细评，对比测试高远球杀球",
            "safety_equipment_and_load_selection",
        ),
        (
            "li-yuxuan",
            "99%球员做错了击球时手指抓紧时机！导致发不上力",
            "release",
        ),
        (
            "li-yuxuan",
            "【直播回放】聊技术和战术 2023年10月15日21点场",
            "learner_fit",
        ),
        (
            "zheng-siwei",
            "羽球思维第109期 双打卸力挡网反击",
            "defense_transition",
        ),
        (
            "zheng-siwei",
            "羽球思维第113期 双打反手搓球的正确方式",
            "frontcourt_pressure",
        ),
        (
            "liu-hui",
            "如何提升杀球速度和挥重？重杀和快杀怎么杀？2个技巧",
            "smash_variant_system",
        ),
        (
            "liu-hui",
            "高远球、吊球、杀球时左手应该放哪里？左手的作用和发力核心动作",
            "overhead_power_chain",
        ),
        (
            "liu-hui",
            "近四十分钟：刘教练带你摸透杀球和高远球发力技巧",
            "overhead_power_chain",
        ),
        (
            "liu-hui",
            "业余快速正确架拍的方法！快速检查架拍对错的技巧",
            "overhead_power_chain",
        ),
        (
            "li-yuxuan",
            "到底怎么选球拍？该用进攻还是防守拍子？",
            "equipment_safety",
        ),
        (
            "li-yuxuan",
            "为什么别人杀球你防得很困难？你的防守对吗？",
            "match_transfer",
        ),
        (
            "li-yuxuan",
            "我发了短球对方总推我底线就特别难受！怎么解决？",
            "serve_receive",
        ),
        (
            "li-yuxuan",
            "林丹【劈杀对角】必杀技！轻松学会！",
            "smash",
        ),
        (
            "zheng-siwei",
            "羽球思维111期 正确的正手中半场抽球发力模式",
            "defense_transition",
        ),
        (
            "zheng-siwei",
            "羽球思维四十六期 如何泄力平快球",
            "defense_transition",
        ),
        (
            "zheng-siwei",
            "羽球思维第118期 如何做好正手中半场勾对角",
            "defense_transition",
        ),
        (
            "zheng-siwei",
            "羽球思维第八十九期 混双男生右半场放网后 快速形成后杀前封站位",
            "pair_rotation_two_lanes",
        ),
    ]
    for coach_id, title, expected_system in cases:
        route, status = module.route_coach_system(coach_id, title)
        assert route.system_id == expected_system
        assert status == "title_system_route"


def test_public_directory_does_not_force_announcements_into_a_coaching_module() -> None:
    module = load_module()
    route, status = module.route_coach_system(
        "li-yuxuan", "我们又要送球拍了！这一次24支球拍！不要错过！！"
    )

    assert route.system_id == "outside_teaching_system"
    assert status == "title_outside_system"


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


def test_public_metadata_catalog_keeps_only_safe_index_fields(tmp_path: Path) -> None:
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
    private_catalog = module.build_catalog(
        tmp_path, (module.Batch("liu-hui", "刘辉", "batch"),)
    )
    output = tmp_path / "public" / "catalog.json"
    module.write_public_metadata_catalog(private_catalog, output)

    exported = json.loads(output.read_text(encoding="utf-8"))
    video = exported["coaches"][0]["videos"][0]
    assert exported["schema_version"] == "public-coach-video-catalog/v1"
    assert set(video) == {
        "source_id",
        "title",
        "url",
        "duration_seconds",
        "classification_status",
        "categories",
        "techniques",
    }
    forbidden_keys: set[str] = set()

    def collect_keys(value: object) -> None:
        if isinstance(value, dict):
            forbidden_keys.update(
                key
                for key in value
                if key.lower()
                in {
                    "clip",
                    "frames",
                    "episode",
                    "media",
                    "asr",
                    "raw_output",
                    "source_batch",
                    "taxonomy_paths",
                    "semantic_bases",
                    "window_ids",
                }
            )
            for child in value.values():
                collect_keys(child)
        elif isinstance(value, list):
            for child in value:
                collect_keys(child)

    collect_keys(exported)
    assert not forbidden_keys


def test_committed_pages_catalog_is_complete_and_media_free() -> None:
    repo = Path(__file__).resolve().parents[1]
    exported = json.loads(
        (repo / "web/public/pages-demo/catalog.json").read_text(encoding="utf-8")
    )
    assert exported["schema_version"] == "public-coach-video-catalog/v1"
    assert exported["total_video_count"] == 873
    assert [(coach["coach_name"], coach["video_count"]) for coach in exported["coaches"]] == [
        ("刘辉", 408),
        ("李宇轩", 382),
        ("郑思维", 83),
    ]

    forbidden_keys: set[str] = set()

    def collect_keys(value: object) -> None:
        if isinstance(value, dict):
            forbidden_keys.update(
                key
                for key in value
                if key.lower()
                in {
                    "clip",
                    "frames",
                    "episode",
                    "media",
                    "asr",
                    "raw_output",
                    "source_batch",
                    "taxonomy_paths",
                    "semantic_bases",
                    "window_ids",
                }
            )
            for child in value.values():
                collect_keys(child)
        elif isinstance(value, list):
            for child in value:
                collect_keys(child)

    collect_keys(exported)
    assert not forbidden_keys
    for coach in exported["coaches"]:
        assert all(len(video["categories"]) == 1 for video in coach["videos"])
        assert all(
            video["classification_status"]
            in {"title_system_route", "title_system_fallback", "title_outside_system"}
            for video in coach["videos"]
        )
        assert all(video["url"].startswith(("https://", "http://")) for video in coach["videos"])
