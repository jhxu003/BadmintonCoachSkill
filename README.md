# BadmintonCoachSkill

BadmintonCoachSkill is a research project for building an evidence-grounded badminton coaching skill. The first internal skill, `liu-hui-badminton-coach`, turns structured video observations into technique diagnosis, training priorities, drills, and retest metrics.

This repository is not official, not authorized, and not affiliated with Liu Hui or any coaching organization. It is intended for research and personal learning. Public files store only source indexes, original summaries, schemas, rules, and code. Raw transcripts, paid-course notes, screenshots, and video files must stay outside git.

## System Shape

```text
video agent observation JSON
  -> player profile
  -> rule matcher
  -> liu-hui-badminton-coach skill references
  -> diagnosis JSON + LLM report context
```

The project does not perform pose estimation or read raw videos in v1. A separate video agent should extract body, racket-side, contact-point, and footwork observations.

## Corpus Build

The Liu Hui corpus layer is now separated from the deterministic skill rules:

- `data/source-index.tsv` is the canonical public-source index.
- `data/corpus/teaching-points.yaml` stores short, original teaching-point summaries tied to source ids.
- `data/corpus/collection-status.md` records what is collected and what is still incomplete.
- `scripts/build_corpus_report.py` prints current corpus coverage.
- `scripts/import_yt_dlp_jsonl.py` converts public `yt-dlp --dump-json` metadata into source-index TSV rows for full-channel completion.

Current seed scope:

```bash
python3 scripts/build_corpus_report.py
```

Run the broader deterministic examples:

```bash
python3 examples/run_full_system_cases.py
```

Expected coverage:

```text
high_clear, smash, rear_footwork, front_footwork, backhand, serve_receive, doubles
```

Full-channel completion should import public metadata only. Do not commit raw videos, long subtitles, paid-course notes, cookies, or account exports.

## Quick Start

```bash
python3 -m pytest -q
```

Example usage:

```python
from pathlib import Path
from badminton_coach_skill.rubric_loader import load_skill_knowledge
from badminton_coach_skill.issue_matcher import match_diagnosis

knowledge = load_skill_knowledge(Path("skills/liu-hui-badminton-coach/references"))
diagnosis = match_diagnosis(player_profile, video_observation, knowledge)
```

## Usage Case

Use case: a beginner uploads a rear-court high-clear clip. The video agent observes late rear-court arrival, a contact point behind the head, a low elbow before hit, and a short follow-through.

Input file:

```text
examples/observations/high_clear_late_arrival.json
```

Run the deterministic usage case:

```bash
python3 examples/run_usage_case.py
```

Expected summary:

```text
Primary framework: stable-overhead-frame
Top priority: late-arrival
```

Interpretation: the skill prioritizes arrival and contact window before advanced hand-speed or pronation advice. It then attaches observable evidence, a concrete drill, and retest metrics so an LLM can write a bounded coaching report without inventing unsupported issues.

## Repository Layout

- `data/source-index.tsv` indexes public sources and their usability.
- `data/corpus/` stores public-safe corpus artifacts, access logs, teaching points, and system taxonomy.
- `skills/liu-hui-badminton-coach/` contains the agent skill and references.
- `schemas/` defines the profile, observation, and diagnosis contracts.
- `src/badminton_coach_skill/` contains deterministic support code.
- `tests/` verifies schemas, rule matching, and safety boundaries.

## Safety Boundaries

- Do not claim Liu Hui personally judged any video.
- Do not present this as official, certified, or authorized.
- Do not store paid-course transcripts, full subtitles, screenshots, or raw videos in git.
- When evidence is missing, return "insufficient evidence" rather than a confident diagnosis.
- Do not claim all official-channel metadata has been imported while YouTube direct metadata fetch remains blocked in `data/corpus/public-access-log.tsv`.
