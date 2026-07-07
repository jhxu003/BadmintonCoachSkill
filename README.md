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

## Repository Layout

- `data/source-index.tsv` indexes public sources and their usability.
- `skills/liu-hui-badminton-coach/` contains the agent skill and references.
- `schemas/` defines the profile, observation, and diagnosis contracts.
- `src/badminton_coach_skill/` contains deterministic support code.
- `tests/` verifies schemas, rule matching, and safety boundaries.

## Safety Boundaries

- Do not claim Liu Hui personally judged any video.
- Do not present this as official, certified, or authorized.
- Do not store paid-course transcripts, full subtitles, screenshots, or raw videos in git.
- When evidence is missing, return "insufficient evidence" rather than a confident diagnosis.

