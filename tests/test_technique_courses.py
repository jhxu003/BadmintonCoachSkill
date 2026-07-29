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


def test_nine_canonical_courses_validate_with_public_media_and_knowledge_links() -> None:
    catalogs = load_and_validate_technique_courses(ROOT)

    assert {catalog["coach_id"] for catalog in catalogs} == {
        "liu-hui",
        "li-yuxuan",
        "zheng-siwei",
    }
    assert sum(len(catalog["courses"]) for catalog in catalogs) == 9
    assert all(len(catalog["courses"]) == 3 for catalog in catalogs)
    for catalog in catalogs:
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
    assert expected["course_count"] == 9

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
