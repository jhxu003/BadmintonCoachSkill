# Liu Hui Complete Public System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the most complete public/authorized Liu Hui badminton teaching-system skill possible, with exhaustive public source indexing, provenance-labeled teaching extraction, full coaching taxonomy, deterministic rules, examples, tests, and GitHub publication.

**Architecture:** Keep raw/public metadata collection separate from skill rules. Public-safe source indexes and teaching points live under `data/`; complete coaching taxonomy and rules live under `skills/liu-hui-badminton-coach/references/`; deterministic matching code consumes only schemas and references. Paid/private/raw copyrighted material never enters git.

**Tech Stack:** Python 3.10+, PyYAML, jsonschema, pytest, TSV/YAML/JSON schemas, public metadata import via `yt-dlp` JSONL when network access allows.

## Global Constraints

- Repository remains non-official, non-authorized, and not affiliated with Liu Hui.
- Do not commit paid-course transcripts, full subtitles, screenshots, raw videos, cookies, tokens, or account exports.
- Every deterministic rule must reference `source_ids` or be explicitly marked `hypothesis`.
- `needs_timestamp_review` teaching points cannot be treated as source-backed rules.
- Third-party discussion can guide product/user insight only; it cannot independently define technique rules.
- The system must say `insufficient evidence` when required video observations are missing.
- Completion means public/authorized corpus coverage is systematically attempted and access limits are recorded.

---

## Completion Contract

The project is not complete until all of these are true:

- Source coverage includes official YouTube channel metadata, authorized Bilibili clips/lists, public short-video discovery entries, public course/catalog/livestream pages, and third-party discussion/stat pages.
- Any channel-level metadata that cannot be fetched is documented with command, date, error, and workaround.
- `data/source-index.tsv` contains source rows for every discovered public item or segment used by the skill.
- `data/corpus/teaching-points.yaml` contains a broad, provenance-labeled map of Liu Hui-style teaching points.
- Skill references include a complete taxonomy for overhead strokes, footwork, front/midcourt strokes, backhand, serve/receive, doubles, match transfer, student profiles, power frameworks, drills, and training plans.
- The deterministic matcher can produce diagnosis for at least high clear, smash, rear-court footwork, front-court footwork, backhand, serve/receive, and doubles positioning observations.
- Examples cover at least six realistic use cases.
- Tests verify corpus coverage, taxonomy coverage, rule-source integrity, examples, safety boundaries, and no private artifacts.
- `pytest -q`, skill validation, corpus report, and source-integrity checks pass.
- Work is committed and pushed to GitHub.

## File Structure

- Modify: `data/source-index.tsv` to expand public source coverage.
- Modify: `data/corpus/teaching-points.yaml` to add broad teaching-point extraction.
- Create: `data/corpus/public-access-log.tsv` to record failed/blocked fetch attempts.
- Create: `data/corpus/system-taxonomy.yaml` as the full Liu Hui-inspired coaching ontology.
- Create: `data/corpus/source-topic-map.yaml` mapping source ids to taxonomy nodes.
- Modify: `schemas/teaching-point.schema.json` to support richer evidence and taxonomy links.
- Create: `schemas/system-taxonomy.schema.json`.
- Create: `schemas/source-topic-map.schema.json`.
- Modify: `src/badminton_coach_skill/source_index.py` with integrity and coverage helpers.
- Create: `src/badminton_coach_skill/taxonomy.py`.
- Modify: `scripts/build_corpus_report.py` with taxonomy and access-log coverage.
- Create: `scripts/check_source_integrity.py`.
- Modify: `skills/liu-hui-badminton-coach/SKILL.md`.
- Modify/Create: `skills/liu-hui-badminton-coach/references/*.yaml` and `*.md` for the complete system.
- Modify/Create: `examples/observations/*.json`, `examples/reports/*.md`, and `examples/run_*.py`.
- Modify/Create: `tests/test_*.py` for every new contract.

## Task 1: Completion Contract and Access Log

**Files:**
- Create: `data/corpus/public-access-log.tsv`
- Create: `tests/test_public_access_log.py`
- Modify: `docs/superpowers/plans/2026-07-08-liu-hui-complete-public-system.md`

**Interfaces:**
- Consumes: existing `data/source-index.tsv`
- Produces: access-log TSV used by `scripts/build_corpus_report.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]


def test_public_access_log_records_blocked_channel_fetches():
    path = ROOT / "data" / "corpus" / "public-access-log.tsv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows
    assert any(row["platform"] == "YouTube" and row["status"] == "blocked" for row in rows)
    assert all(row["attempted_at"] for row in rows)
    assert all(row["command_or_url"] for row in rows)
    assert all(row["result"] for row in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_public_access_log.py`

Expected: FAIL because `data/corpus/public-access-log.tsv` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `data/corpus/public-access-log.tsv` with header:

```text
attempt_id	attempted_at	platform	command_or_url	status	result	next_action
```

Add rows for the failed YouTube `yt-dlp` attempts on `2026-07-08`:

```text
YT_OFFICIAL_20260708	2026-07-08	YouTube	python3 -m yt_dlp --flat-playlist --dump-json "https://www.youtube.com/@liuhuiyumaoqiu/videos"	blocked	Connection reset by peer after retries; produced zero JSONL rows	Use search-indexed public pages and retry metadata import from a network that can reach YouTube.
YT_INITIAL_G_20260708	2026-07-08	YouTube	python3 -m yt_dlp --flat-playlist --dump-json "https://www.youtube.com/@initial-G_badminton/videos"	blocked	Connection reset by peer after retries; produced zero JSONL rows	Verify canonical handle and retry metadata import from a network that can reach YouTube.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_public_access_log.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-07-08-liu-hui-complete-public-system.md data/corpus/public-access-log.tsv tests/test_public_access_log.py
git commit -m "Define Liu Hui system completion contract"
```

## Task 2: Full Taxonomy Schema and Seed Taxonomy

**Files:**
- Create: `schemas/system-taxonomy.schema.json`
- Create: `data/corpus/system-taxonomy.yaml`
- Create: `src/badminton_coach_skill/taxonomy.py`
- Create: `tests/test_system_taxonomy.py`

**Interfaces:**
- Consumes: taxonomy YAML.
- Produces: `load_system_taxonomy(path: Path) -> dict[str, list[dict[str, object]]]`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import json

import jsonschema
import yaml

from badminton_coach_skill.taxonomy import load_system_taxonomy

ROOT = Path(__file__).resolve().parents[1]


def test_system_taxonomy_covers_complete_coaching_surface():
    schema = json.loads((ROOT / "schemas" / "system-taxonomy.schema.json").read_text(encoding="utf-8"))
    taxonomy = yaml.safe_load((ROOT / "data" / "corpus" / "system-taxonomy.yaml").read_text(encoding="utf-8"))
    jsonschema.validate(taxonomy, schema)
    required_sections = {
        "student_profiles",
        "power_frameworks",
        "stroke_families",
        "footwork_families",
        "correction_order",
        "drill_families",
        "training_plans",
        "match_transfer",
    }
    assert required_sections.issubset(taxonomy)
    stroke_ids = {item["id"] for item in taxonomy["stroke_families"]}
    for required in ["high_clear", "smash", "drop", "drive", "net", "backhand", "serve_receive", "doubles"]:
        assert required in stroke_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_system_taxonomy.py`

Expected: FAIL because schema/module/taxonomy do not exist.

- [ ] **Step 3: Write minimal implementation**

Create schema requiring all sections listed in the test. Create `taxonomy.py`:

```python
from __future__ import annotations

from pathlib import Path
import yaml


def load_system_taxonomy(path: str | Path) -> dict[str, list[dict[str, object]]]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
```

Create taxonomy YAML with the required sections and ids.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_system_taxonomy.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schemas/system-taxonomy.schema.json data/corpus/system-taxonomy.yaml src/badminton_coach_skill/taxonomy.py tests/test_system_taxonomy.py
git commit -m "Add Liu Hui coaching system taxonomy"
```

## Task 3: Source Topic Map and Corpus Integrity

**Files:**
- Create: `schemas/source-topic-map.schema.json`
- Create: `data/corpus/source-topic-map.yaml`
- Create: `scripts/check_source_integrity.py`
- Modify: `src/badminton_coach_skill/source_index.py`
- Create: `tests/test_source_integrity.py`

**Interfaces:**
- Consumes: `data/source-index.tsv`, `data/corpus/teaching-points.yaml`, `data/corpus/system-taxonomy.yaml`, `data/corpus/source-topic-map.yaml`
- Produces: command `python3 scripts/check_source_integrity.py`

- [ ] **Step 1: Write the failing test**

```python
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_source_integrity_script_passes():
    result = subprocess.run(
        [sys.executable, "scripts/check_source_integrity.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "source_integrity_ok" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_source_integrity.py`

Expected: FAIL because script does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement a script that checks:

- every teaching-point `source_id` exists in `data/source-index.tsv`
- every source-topic-map `source_id` exists in `data/source-index.tsv`
- every source-topic-map taxonomy id exists in `data/corpus/system-taxonomy.yaml`
- every deterministic skill rule `source_id` exists in `data/source-index.tsv`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_source_integrity.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schemas/source-topic-map.schema.json data/corpus/source-topic-map.yaml scripts/check_source_integrity.py src/badminton_coach_skill/source_index.py tests/test_source_integrity.py
git commit -m "Add source integrity checks"
```

## Task 4: Expand Teaching Points Into Full System

**Files:**
- Modify: `data/corpus/teaching-points.yaml`
- Modify: `tests/test_corpus_build.py`

**Interfaces:**
- Consumes: existing teaching-point schema and source index.
- Produces: at least 40 teaching points across taxonomy sections.

- [ ] **Step 1: Write the failing test**

Add assertions that teaching points cover:

```python
required_areas = {
    "student_profile",
    "power_framework",
    "high_clear",
    "smash",
    "drop",
    "drive",
    "net",
    "backhand",
    "serve_receive",
    "front_court_footwork",
    "rear_court_footwork",
    "doubles",
    "training_plan",
    "match_transfer",
}
covered = {area for point in teaching_points for area in point["applies_to"]}
assert required_areas.issubset(covered)
assert len(teaching_points) >= 40
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_corpus_build.py`

Expected: FAIL because current teaching points are fewer than 40 and do not cover all areas.

- [ ] **Step 3: Write minimal implementation**

Expand `data/corpus/teaching-points.yaml` with short original summaries. Each point must include `source_ids`, `evidence_type`, `status`, and `review_need`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_corpus_build.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data/corpus/teaching-points.yaml tests/test_corpus_build.py
git commit -m "Expand Liu Hui teaching point map"
```

## Task 5: Skill Reference Expansion

**Files:**
- Create: `skills/liu-hui-badminton-coach/references/student-profiles.yaml`
- Create: `skills/liu-hui-badminton-coach/references/stroke-taxonomy.yaml`
- Create: `skills/liu-hui-badminton-coach/references/training-plans.yaml`
- Modify: `skills/liu-hui-badminton-coach/references/frameworks.yaml`
- Modify: `skills/liu-hui-badminton-coach/references/drills.yaml`
- Modify: `skills/liu-hui-badminton-coach/SKILL.md`
- Modify: `tests/test_project_contracts.py`

**Interfaces:**
- Consumes: `data/corpus/system-taxonomy.yaml`
- Produces: skill references loaded by future agents.

- [ ] **Step 1: Write the failing test**

Add test assertions:

```python
required_refs = [
    "student-profiles.yaml",
    "stroke-taxonomy.yaml",
    "training-plans.yaml",
]
for filename in required_refs:
    assert (reference_dir / filename).exists()
skill = (ROOT / "skills" / "liu-hui-badminton-coach" / "SKILL.md").read_text(encoding="utf-8")
for filename in required_refs:
    assert filename in skill
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_project_contracts.py`

Expected: FAIL because these references do not exist.

- [ ] **Step 3: Write minimal implementation**

Create the three reference files and update `SKILL.md` reference-loading instructions.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_project_contracts.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/liu-hui-badminton-coach tests/test_project_contracts.py
git commit -m "Expand Liu Hui skill references"
```

## Task 6: Broaden Observation and Diagnosis Examples

**Files:**
- Modify: `schemas/video-observation.schema.json`
- Create: `examples/observations/*.json`
- Create: `examples/reports/*.md`
- Create: `examples/run_full_system_cases.py`
- Create: `tests/test_full_system_examples.py`

**Interfaces:**
- Consumes: existing matcher and skill references.
- Produces: command `python3 examples/run_full_system_cases.py`

- [ ] **Step 1: Write the failing test**

```python
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_full_system_examples_run():
    result = subprocess.run(
        [sys.executable, "examples/run_full_system_cases.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    for label in ["high_clear", "smash", "rear_footwork", "front_footwork", "backhand", "serve_receive"]:
        assert label in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_full_system_examples.py`

Expected: FAIL because script and cases do not exist.

- [ ] **Step 3: Write minimal implementation**

Add six example observation files and a runner that prints one line per case.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_full_system_examples.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schemas/video-observation.schema.json examples tests/test_full_system_examples.py
git commit -m "Add full system diagnosis examples"
```

## Task 7: Final Verification and Publication

**Files:**
- Modify: `README.md`
- Modify: `data/corpus/collection-status.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: pushed GitHub repository.

- [ ] **Step 1: Run complete verification**

Run:

```bash
pytest -q
python3 scripts/build_corpus_report.py
python3 scripts/check_source_integrity.py
python3 /dataStor/home/jhxu/.agents/skills/anthropic-skills/skills/skill-creator/scripts/quick_validate.py skills/liu-hui-badminton-coach
git diff --check
```

Expected: all commands pass.

- [ ] **Step 2: Commit final docs**

```bash
git add README.md data/corpus/collection-status.md
git commit -m "Document complete Liu Hui public system"
```

- [ ] **Step 3: Push**

```bash
git push origin main
```

- [ ] **Step 4: Confirm remote hash**

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Expected: hashes match.

## Self-Review

- Spec coverage: The plan covers source acquisition, access failure logging, taxonomy, teaching extraction, source integrity, skill references, examples, tests, final verification, commit, and push.
- Placeholder scan: No `TBD`, `TODO`, or unspecified "write tests" steps remain.
- Type consistency: File names and script names are consistent across tasks.
