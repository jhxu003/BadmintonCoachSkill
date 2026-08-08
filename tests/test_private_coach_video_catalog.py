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


def test_public_metadata_catalog_prefers_official_bilibili_title_registry(tmp_path: Path) -> None:
    module = load_module()
    batch = tmp_path / "batch" / "videos" / "video-001"
    batch.mkdir(parents=True)
    (batch / "lesson-package.json").write_text(
        json.dumps(package("internal import label", []), ensure_ascii=False), encoding="utf-8"
    )
    private_catalog = module.build_catalog(
        tmp_path, (module.Batch("liu-hui", "刘辉", "batch"),)
    )

    exported = module.public_metadata_catalog(
        private_catalog, title_overrides={"SOURCE_001": "B站原始标题：高远球教学"}
    )

    assert exported["coaches"][0]["videos"][0]["title"] == "B站原始标题：高远球教学"


def test_public_topic_index_keeps_parent_system_and_narrow_title_topics() -> None:
    module = load_module()
    catalog = {
        "total_video_count": 3,
        "coaches": [
            {
                "coach_id": "liu-hui",
                "coach_name": "刘辉",
                "videos": [
                    {
                        "source_id": "LH_001",
                        "title": "internal label",
                        "url": "https://example.invalid/liu",
                        "duration_seconds": 60,
                    }
                ],
            },
            {
                "coach_id": "li-yuxuan",
                "coach_name": "李宇轩",
                "videos": [
                    {
                        "source_id": "LYX_001",
                        "title": "internal label",
                        "url": "https://example.invalid/li",
                        "duration_seconds": 60,
                    }
                ],
            },
            {
                "coach_id": "zheng-siwei",
                "coach_name": "郑思维",
                "videos": [
                    {
                        "source_id": "ZSW_001",
                        "title": "internal label",
                        "url": "https://example.invalid/zheng",
                        "duration_seconds": 60,
                    }
                ],
            },
        ],
    }
    exported = module.public_metadata_catalog(
        catalog,
        title_overrides={
            "LH_001": "高远球改动作：击球点、顶肘与完整释放",
            "LYX_001": "场地太大接不了球：什么时候用并步和交叉步？",
            "ZSW_001": "羽球思维第116期 接发球后如何回连贯扑压",
        },
    )

    liu, li, zheng = exported["coaches"]
    assert liu["videos"][0]["categories"] == [
        {"id": "rear_court_base_and_high_clear", "name": "后场基础与高远球"}
    ]
    assert [item["action"] for item in liu["videos"][0]["techniques"]] == [
        "liu-contact-window",
        "liu-top-elbow",
        "liu-high-clear-base",
    ]
    assert li["videos"][0]["categories"] == [
        {"id": "footwork", "name": "启动、到位、落地与回收"}
    ]
    assert [item["action"] for item in li["videos"][0]["techniques"]] == ["lyx-rear-start"]
    assert zheng["videos"][0]["categories"] == [
        {"id": "receive_opening_exchange", "name": "接发与前两拍衔接"}
    ]
    assert zheng["videos"][0]["techniques"][0]["action"] == "zsw-receive-opening"
    assert all(coach["topic_count"] >= 1 for coach in exported["coaches"])

    indexes = module.build_skill_source_topic_indexes(exported)
    assert set(indexes) == {"liu-hui", "li-yuxuan", "zheng-siwei"}
    source = indexes["liu-hui"]["sources"][0]
    assert set(source) == {"source_id", "title", "url", "classification_status", "system", "topics"}
    assert source["topics"][0]["id"] == "liu-contact-window"
    serialized = json.dumps(indexes, ensure_ascii=False)
    assert "duration_seconds" not in serialized
    assert ".runtime" not in serialized
    assert "raw_output" not in serialized


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

    title_registry = json.loads(
        (repo / "web/public/pages-demo/bilibili-title-registry.json").read_text(encoding="utf-8")
    )
    assert title_registry["schema_version"] == "public-bilibili-title-registry/v1"
    assert title_registry["video_count"] == exported["total_video_count"]
    assert set(title_registry) == {
        "schema_version",
        "retrieved_at",
        "publication_boundary",
        "video_count",
        "videos",
    }
    assert all(set(item) == {"source_id", "bvid", "title"} for item in title_registry["videos"])
    official_titles = {item["source_id"]: item["title"] for item in title_registry["videos"]}
    assert len(official_titles) == title_registry["video_count"]
    assert all(
        official_titles[video["source_id"]] == video["title"]
        for coach in exported["coaches"]
        for video in coach["videos"]
    )

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
            in {"title_topic_route", "title_topic_fallback", "title_outside_system"}
            for video in coach["videos"]
        )
        assert all(video["url"].startswith(("https://", "http://")) for video in coach["videos"])


def test_committed_skill_source_topic_indexes_match_public_catalog_and_stay_safe() -> None:
    repo = Path(__file__).resolve().parents[1]
    catalog = json.loads(
        (repo / "web/public/pages-demo/catalog.json").read_text(encoding="utf-8")
    )
    expected = {item["coach_id"]: item for item in catalog["coaches"]}
    relative_paths = {
        "liu-hui": "skills/liu-hui-badminton-coach/references/source-topic-index.json",
        "li-yuxuan": "skills/li-yuxuan-badminton-coach/references/source-topic-index.json",
        "zheng-siwei": "skills/zheng-siwei-badminton-coach/references/source-topic-index.json",
    }
    for coach_id, relative_path in relative_paths.items():
        index = json.loads((repo / relative_path).read_text(encoding="utf-8"))
        coach = expected[coach_id]
        assert index["schema_version"] == "coach-skill-source-topic-index/v1"
        assert index["source_count"] == coach["video_count"]
        assert {item["source_id"] for item in index["sources"]} == {
            item["source_id"] for item in coach["videos"]
        }
        assert all(set(item) == {"source_id", "title", "url", "classification_status", "system", "topics"} for item in index["sources"])
        serialized = json.dumps(index, ensure_ascii=False)
        assert ".runtime" not in serialized
        assert "data/raw-private" not in serialized
        assert "raw_output" not in serialized
        assert "episodes" not in serialized
