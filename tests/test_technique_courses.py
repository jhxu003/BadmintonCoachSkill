from __future__ import annotations

import json
from pathlib import Path

from badminton_coach_skill.technique_courses import (
    PUBLIC_SCHEMA_VERSION,
    build_public_technique_course_catalog,
    load_and_validate_technique_courses,
    public_technique_course_catalog_is_current,
)


ROOT = Path(__file__).resolve().parents[1]


def test_sixteen_canonical_courses_validate_with_curriculum_maps_and_public_media() -> None:
    catalogs = load_and_validate_technique_courses(ROOT)

    assert {catalog["coach_id"] for catalog in catalogs} == {
        "liu-hui",
        "li-yuxuan",
        "zheng-siwei",
    }
    assert {catalog["coach_id"]: len(catalog["courses"]) for catalog in catalogs} == {
        "liu-hui": 7,
        "li-yuxuan": 3,
        "zheng-siwei": 6,
    }
    assert {catalog["coach_id"]: len(catalog["techniques"]) for catalog in catalogs} == {
        "liu-hui": 12,
        "li-yuxuan": 10,
        "zheng-siwei": 9,
    }
    for catalog in catalogs:
        techniques = {item["technique_id"]: item for item in catalog["techniques"]}
        bound_courses = {
            course_id
            for technique in techniques.values()
            for course_id in technique["course_ids"]
        }
        assert bound_courses == {course["course_id"] for course in catalog["courses"]}
        for technique_id, technique in techniques.items():
            assert technique["framework_ids"]
            assert technique["rule_ids"]
            assert technique["drill_ids"]
            assert technique["retest_metrics"]
            if technique["availability"] == "teaching_ready":
                assert technique["course_ids"]
            else:
                assert technique["course_ids"] == []
            for next_id in technique["next_technique_ids"]:
                assert technique_id in techniques[next_id]["prerequisite_technique_ids"]
        for course in catalog["courses"]:
            assert course["status"] == "teaching_ready"
            assert course["source"]["demonstrator_role"] == "coach"
            assert course["source"]["example_polarity"] == "correct"
            assert course["source"]["context_review_status"] == "agent_reviewed"
            assert len(course["media"]["stages"]) == 7
            assert course["framework_ids"]
            assert course["drill_ids"]
            assert course["common_errors"]
            assert course["retest_metrics"]


def test_public_course_artifacts_are_current_and_safe() -> None:
    assert public_technique_course_catalog_is_current(ROOT)
    expected = build_public_technique_course_catalog(ROOT)
    assert expected["schema_version"] == PUBLIC_SCHEMA_VERSION
    assert expected["course_count"] == 16
    assert {coach["coach_id"]: len(coach["techniques"]) for coach in expected["coaches"]} == {
        "liu-hui": 12,
        "li-yuxuan": 10,
        "zheng-siwei": 9,
    }

    for relative in (
        "web/src/data/technique-courses.public.json",
        "web/public/pages-demo/technique-courses.json",
    ):
        rendered = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert rendered == expected
        serialized = json.dumps(rendered, ensure_ascii=False)
        assert "/public/home/" not in serialized
        assert ".runtime/" not in serialized
        assert "data/raw-private/" not in serialized
        assert "github_pat_" not in serialized


def test_pages_demo_consumes_the_generated_course_artifact() -> None:
    pages_source = (ROOT / "web/src/features/pages/PagesDemo.tsx").read_text(
        encoding="utf-8"
    )
    assert 'import techniqueCourseData from "../../data/technique-courses.public.json"' in pages_source
    assert "techniqueCourseById" in pages_source
    assert "pages-course-loop" in pages_source
    assert "pages-curriculum-map" in pages_source
    assert "knowledge_only" in pages_source
