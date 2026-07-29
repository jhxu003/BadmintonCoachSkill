from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Iterable

import jsonschema
import yaml


SCHEMA_VERSION = "technique-course/v1"
PUBLIC_SCHEMA_VERSION = "public-technique-course/v1"
COURSE_REFERENCE_DIRS = {
    "liu-hui": "skills/liu-hui-badminton-coach/references",
    "li-yuxuan": "skills/li-yuxuan-badminton-coach/references",
    "zheng-siwei": "skills/zheng-siwei-badminton-coach/references",
}
PUBLIC_TARGETS = (
    "web/src/data/technique-courses.public.json",
    "web/public/pages-demo/technique-courses.json",
)
_BVID_RE = re.compile(r"/video/(BV[0-9A-Za-z]+)")
_PRIVATE_MARKERS = (
    "/public/home/",
    ".runtime/",
    "data/raw-private/",
    "video-lesson-source-cache",
    "github_pat_",
)
_FORBIDDEN_POSITIVE_CLAIMS = (
    "精确触球",
    "拍面角度",
    "握拍压力",
    "力量大小",
    "真实内旋",
    "三维运动学",
    "对手意图",
)


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_list(path: Path, key: str) -> dict[str, dict[str, Any]]:
    payload = _read_yaml(path)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a YAML list")
    result: dict[str, dict[str, Any]] = {}
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get(key), str):
            raise ValueError(f"{path} contains an invalid {key} entry")
        identifier = str(item[key])
        if identifier in result:
            raise ValueError(f"{path} contains duplicate {key}={identifier}")
        result[identifier] = item
    return result


def _skill_references(root: Path, coach_id: str) -> dict[str, dict[str, dict[str, Any]]]:
    reference_dir = root / COURSE_REFERENCE_DIRS[coach_id]
    rules: dict[str, dict[str, Any]] = {}
    for path in sorted(reference_dir.glob("*-rubric.yaml")):
        for identifier, item in _load_list(path, "rule_id").items():
            if identifier in rules:
                raise ValueError(f"duplicate rule_id={identifier} across {reference_dir}")
            rules[identifier] = item
    return {
        "frameworks": _load_list(reference_dir / "frameworks.yaml", "framework_id"),
        "rules": rules,
        "drills": _load_list(reference_dir / "drills.yaml", "drill_id"),
    }


def _title_registry(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "web/public/pages-demo/bilibili-title-registry.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    videos = payload.get("videos") if isinstance(payload, dict) else None
    if not isinstance(videos, list):
        raise ValueError(f"invalid title registry: {path}")
    return {
        str(item["source_id"]): item
        for item in videos
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _claim_strings(course: dict[str, Any]) -> Iterable[str]:
    yield str(course["learning_goal_zh"])
    yield from (str(item) for item in course["prerequisites"])
    for item in course["core_principles"]:
        yield str(item["cue_zh"])
    for item in course["common_errors"]:
        yield str(item["summary_zh"])
        yield str(item["correction_zh"])
    for stage in course["media"]["stages"]:
        yield str(stage["cue_zh"])
        yield str(stage["visible_evidence_zh"])


def _same_number(left: Any, right: Any) -> bool:
    try:
        return abs(float(left) - float(right)) <= 0.001
    except (TypeError, ValueError):
        return False


def _validate_review_manifest(
    root: Path, course: dict[str, Any], errors: list[str]
) -> None:
    course_id = str(course["course_id"])
    source = course["source"]
    clip_path = Path("web/public") / str(course["media"]["clip_path"])
    manifest_path = (root / clip_path).parent / "review.json"
    if not manifest_path.is_file():
        errors.append(f"{course_id}: missing review manifest {manifest_path.relative_to(root)}")
        return
    try:
        review = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{course_id}: invalid review manifest: {exc}")
        return
    for key in (
        "source_id",
        "source_url",
        "demonstrator_role",
        "example_polarity",
        "context_review_status",
    ):
        source_key = "url" if key == "source_url" else key
        if review.get(key) != source.get(source_key):
            errors.append(f"{course_id}: review manifest {key} does not match course source")
    for key in (
        "action_start_seconds",
        "action_end_seconds",
        "context_start_seconds",
        "context_end_seconds",
    ):
        if not _same_number(review.get(key), source.get(key)):
            errors.append(f"{course_id}: review manifest {key} does not match course source")
    if review.get("review_basis") != source.get("review_basis"):
        errors.append(f"{course_id}: review_basis does not match the public review manifest")


def _validate_course(
    root: Path,
    catalog_coach_id: str,
    course: dict[str, Any],
    system_ids: set[str],
    references: dict[str, dict[str, dict[str, Any]]],
    titles: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    course_id = str(course["course_id"])
    if course["coach_id"] != catalog_coach_id:
        errors.append(f"{course_id}: coach_id does not match its catalog")
    if course["system_id"] not in system_ids:
        errors.append(f"{course_id}: unknown system_id={course['system_id']}")

    for field, reference_group in (
        ("framework_ids", "frameworks"),
        ("drill_ids", "drills"),
    ):
        for identifier in course[field]:
            if identifier not in references[reference_group]:
                errors.append(f"{course_id}: unresolved {field[:-1]}={identifier}")
    for item in course["common_errors"]:
        if item["rule_id"] not in references["rules"]:
            errors.append(f"{course_id}: unresolved rule_id={item['rule_id']}")

    source = course["source"]
    if source["action_end_seconds"] <= source["action_start_seconds"]:
        errors.append(f"{course_id}: action interval is not ordered")
    if source["context_start_seconds"] > source["action_start_seconds"] - 20:
        errors.append(f"{course_id}: review context has less than 20 seconds before action")
    if source["context_end_seconds"] < source["action_end_seconds"] + 20:
        errors.append(f"{course_id}: review context has less than 20 seconds after action")

    registry_item = titles.get(str(source["source_id"]))
    if registry_item is None:
        errors.append(f"{course_id}: source_id is absent from the public title registry")
    else:
        if source["title"] != registry_item.get("title"):
            errors.append(f"{course_id}: source title does not exactly match Bilibili registry")
        match = _BVID_RE.search(str(source["url"]))
        if match is None or match.group(1).lower() != str(registry_item.get("bvid", "")).lower():
            errors.append(f"{course_id}: source URL BVID does not match title registry")

    clip_relative = Path(str(course["media"]["clip_path"]))
    if clip_relative.parts[:2] != ("pages-demo", course_id):
        errors.append(f"{course_id}: clip path must use pages-demo/{course_id}/")
    clip = root / "web/public" / clip_relative
    if not clip.is_file() or clip.stat().st_size <= 0:
        errors.append(f"{course_id}: public clip is missing or empty")

    exact_anchors: list[float] = []
    image_paths: set[str] = set()
    for stage in course["media"]["stages"]:
        image_path = str(stage["image_path"])
        if image_path in image_paths:
            errors.append(f"{course_id}: duplicate stage image {image_path}")
        image_paths.add(image_path)
        if Path(image_path).parts[:2] != ("pages-demo", course_id):
            errors.append(f"{course_id}: stage image must use pages-demo/{course_id}/")
        image = root / "web/public" / image_path
        if not image.is_file() or image.stat().st_size <= 0:
            errors.append(f"{course_id}: missing or empty stage image {image_path}")
        if stage["anchor_status"] == "exact_export_timestamp":
            anchor = float(stage["anchor_seconds"])
            exact_anchors.append(anchor)
            if not source["action_start_seconds"] <= anchor <= source["action_end_seconds"]:
                errors.append(f"{course_id}: stage anchor {anchor} is outside action interval")
    if exact_anchors and exact_anchors != sorted(set(exact_anchors)):
        errors.append(f"{course_id}: exact stage anchors must be unique and increasing")

    for claim in _claim_strings(course):
        for forbidden in _FORBIDDEN_POSITIVE_CLAIMS:
            if forbidden in claim:
                errors.append(
                    f"{course_id}: teaching claim contains unsupported monocular claim {forbidden!r}"
                )

    for text in _iter_strings(course):
        if any(marker in text for marker in _PRIVATE_MARKERS):
            errors.append(f"{course_id}: private or absolute path marker leaked into course data")
            break
    _validate_review_manifest(root, course, errors)


def _validate_technique_map(
    catalog: dict[str, Any],
    references: dict[str, dict[str, dict[str, Any]]],
    errors: list[str],
) -> None:
    """Validate the coach's curriculum graph and its reviewed-course bindings."""
    coach_id = str(catalog["coach_id"])
    system_ids = {str(item["system_id"]) for item in catalog["systems"]}
    techniques = catalog["techniques"]
    technique_by_id = {str(item["technique_id"]): item for item in techniques}
    if len(technique_by_id) != len(techniques):
        errors.append(f"{coach_id}: duplicate technique_id")
        return

    course_by_id = {str(item["course_id"]): item for item in catalog["courses"]}
    bound_course_ids: dict[str, str] = {}
    for technique_id, technique in technique_by_id.items():
        if technique["system_id"] not in system_ids:
            errors.append(
                f"{coach_id}:{technique_id}: unknown system_id={technique['system_id']}"
            )
        for field, reference_group in (
            ("framework_ids", "frameworks"),
            ("rule_ids", "rules"),
            ("drill_ids", "drills"),
        ):
            for identifier in technique[field]:
                if identifier not in references[reference_group]:
                    errors.append(
                        f"{coach_id}:{technique_id}: unresolved {field[:-1]}={identifier}"
                    )
        for field in ("prerequisite_technique_ids", "next_technique_ids"):
            for related_id in technique[field]:
                if related_id == technique_id:
                    errors.append(f"{coach_id}:{technique_id}: cannot route to itself")
                elif related_id not in technique_by_id:
                    errors.append(
                        f"{coach_id}:{technique_id}: unresolved curriculum route={related_id}"
                    )
        for next_id in technique["next_technique_ids"]:
            target = technique_by_id.get(next_id)
            if target and technique_id not in target["prerequisite_technique_ids"]:
                errors.append(
                    f"{coach_id}:{technique_id}: next route {next_id} is missing the reciprocal prerequisite"
                )
        for course_id in technique["course_ids"]:
            course = course_by_id.get(course_id)
            if course is None:
                errors.append(
                    f"{coach_id}:{technique_id}: unresolved course_id={course_id}"
                )
                continue
            if course.get("technique_id") != technique_id:
                errors.append(
                    f"{coach_id}:{technique_id}: course {course_id} binds a different technique"
                )
            if course_id in bound_course_ids:
                errors.append(
                    f"{coach_id}: course {course_id} is bound by both {bound_course_ids[course_id]} and {technique_id}"
                )
            bound_course_ids[course_id] = technique_id
        if technique["availability"] == "teaching_ready" and not technique["course_ids"]:
            errors.append(f"{coach_id}:{technique_id}: teaching_ready node has no reviewed course")
        if technique["availability"] == "knowledge_only" and technique["course_ids"]:
            errors.append(f"{coach_id}:{technique_id}: knowledge_only node cannot expose media")
        for text in _iter_strings(technique):
            if any(marker in text for marker in _PRIVATE_MARKERS):
                errors.append(f"{coach_id}:{technique_id}: private or absolute path marker leaked into map")
                break

    for course_id, course in course_by_id.items():
        technique_id = str(course["technique_id"])
        if technique_id not in technique_by_id:
            errors.append(f"{coach_id}:{course_id}: course has no curriculum technique node")
        elif bound_course_ids.get(course_id) != technique_id:
            errors.append(
                f"{coach_id}:{course_id}: reviewed course is not uniquely bound to its technique node"
            )


def load_and_validate_technique_courses(root: str | Path) -> list[dict[str, Any]]:
    project_root = Path(root).resolve()
    schema = json.loads(
        (project_root / "schemas/technique-course.schema.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(schema)
    titles = _title_registry(project_root)
    catalogs: list[dict[str, Any]] = []
    errors: list[str] = []
    course_ids: set[str] = set()

    for coach_id, relative_reference_dir in COURSE_REFERENCE_DIRS.items():
        path = project_root / relative_reference_dir / "technique-courses.yaml"
        catalog = _read_yaml(path)
        if not isinstance(catalog, dict):
            errors.append(f"{path.relative_to(project_root)} must contain a YAML mapping")
            continue
        schema_errors = sorted(validator.iter_errors(catalog), key=lambda item: list(item.path))
        for error in schema_errors:
            location = ".".join(str(part) for part in error.path) or "root"
            errors.append(f"{path.relative_to(project_root)}:{location}: {error.message}")
        if schema_errors:
            continue
        if catalog["schema_version"] != SCHEMA_VERSION or catalog["coach_id"] != coach_id:
            errors.append(f"{path.relative_to(project_root)} has the wrong coach/schema identity")
            continue
        system_ids = {str(item["system_id"]) for item in catalog["systems"]}
        if len(system_ids) != len(catalog["systems"]):
            errors.append(f"{coach_id}: duplicate system_id")
        references = _skill_references(project_root, coach_id)
        for course in catalog["courses"]:
            course_id = str(course["course_id"])
            if course_id in course_ids:
                errors.append(f"duplicate course_id={course_id}")
            course_ids.add(course_id)
            _validate_course(
                project_root,
                coach_id,
                course,
                system_ids,
                references,
                titles,
                errors,
            )
        _validate_technique_map(catalog, references, errors)
        catalogs.append(catalog)

    if errors:
        raise ValueError("technique-course validation failed:\n- " + "\n- ".join(errors))
    return catalogs


def build_public_technique_course_catalog(root: str | Path) -> dict[str, Any]:
    project_root = Path(root).resolve()
    catalogs = load_and_validate_technique_courses(project_root)
    coaches: list[dict[str, Any]] = []
    for catalog in catalogs:
        coach_id = str(catalog["coach_id"])
        references = _skill_references(project_root, coach_id)
        courses: list[dict[str, Any]] = []
        for raw_course in catalog["courses"]:
            course = deepcopy(raw_course)
            course["resolved_frameworks"] = [
                {
                    "framework_id": identifier,
                    "name": references["frameworks"][identifier]["name"],
                    "summary": references["frameworks"][identifier]["summary"],
                }
                for identifier in course["framework_ids"]
            ]
            course["resolved_drills"] = []
            for identifier in course["drill_ids"]:
                drill = references["drills"][identifier]
                public_drill = {
                    key: deepcopy(drill[key])
                    for key in (
                        "drill_id",
                        "name",
                        "purpose",
                        "target_issues",
                        "steps",
                        "dosage",
                        "progression",
                        "stop_conditions",
                        "retest_metrics",
                    )
                    if key in drill
                }
                course["resolved_drills"].append(public_drill)
            courses.append(course)
        techniques: list[dict[str, Any]] = []
        for raw_technique in catalog["techniques"]:
            technique = deepcopy(raw_technique)
            technique["resolved_frameworks"] = [
                {
                    "framework_id": identifier,
                    "name": references["frameworks"][identifier]["name"],
                    "summary": references["frameworks"][identifier]["summary"],
                }
                for identifier in technique["framework_ids"]
            ]
            technique["resolved_rules"] = [
                {
                    "rule_id": identifier,
                    "issue": references["rules"][identifier].get("issue", identifier),
                    "correction_principle": references["rules"][identifier].get(
                        "correction_principle", "Use the linked drill and retest."
                    ),
                }
                for identifier in technique["rule_ids"]
            ]
            techniques.append(technique)
        coaches.append(
            {
                "coach_id": coach_id,
                "systems": deepcopy(catalog["systems"]),
                "techniques": techniques,
                "courses": courses,
            }
        )
    return {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "course_count": sum(len(item["courses"]) for item in coaches),
        "coaches": coaches,
    }


def render_public_technique_course_catalog(root: str | Path) -> str:
    return (
        json.dumps(
            build_public_technique_course_catalog(root),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def write_public_technique_course_catalog(root: str | Path) -> list[Path]:
    project_root = Path(root).resolve()
    rendered = render_public_technique_course_catalog(project_root)
    targets: list[Path] = []
    for relative in PUBLIC_TARGETS:
        target = project_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        targets.append(target)
    return targets


def public_technique_course_catalog_is_current(root: str | Path) -> bool:
    project_root = Path(root).resolve()
    rendered = render_public_technique_course_catalog(project_root)
    return all(
        (project_root / relative).is_file()
        and (project_root / relative).read_text(encoding="utf-8") == rendered
        for relative in PUBLIC_TARGETS
    )
