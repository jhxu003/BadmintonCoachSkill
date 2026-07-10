# BadmintonCoachSkill

BadmintonCoachSkill is an evidence-grounded coaching layer for badminton video-analysis agents.

It does not read raw video by itself. Instead, a video agent or human annotator provides structured observations such as contact point, elbow height, racket-side frame, hip timing, footwork arrival, preparation size, rally pressure, and recovery. BadmintonCoachSkill then ranks the most important technical issue, selects a suitable coaching framework, recommends a drill, and adds a retest metric.

The first skill in this repository is `liu-hui-badminton-coach`, a non-official Liu Hui-inspired badminton coaching skill built from public-source indexing and original summaries.

## What It Does

- Diagnoses high clear, smash, drop/slice/slide, drive/flat exchange, rear-court footwork, front-court footwork, backhand, serve/receive, doubles, and match-transfer cases.
- Chooses a student-fit path before giving isolated technique cues.
- Prioritizes observable problems such as late arrival, contact point, low elbow, collapsed frame, late hip drive, forced wrist/pronation, big-arm pulling, poor unloading/deceleration, jump-smash contact or landing failure, slow or exposed drop, jammed drive spacing, short follow-through, slow recovery, large preparation, and equipment mismatch.
- Produces bounded coaching context for an LLM report: main priority, evidence, correction principle, drill, and retest metric.
- Tracks source provenance so the model can distinguish source-backed, inferred, hypothesis, and insufficient-evidence claims.

## Who It Is For

- Developers building badminton video-analysis agents.
- Coaches who want structured draft reports from annotated video.
- Researchers or builders experimenting with skill/rubric-driven sports feedback.

## Quick Start

```bash
git clone https://github.com/jhxu003/BadmintonCoachSkill.git
cd BadmintonCoachSkill
python3 -m pip install -e .
python3 examples/run_usage_case.py
```

Expected output begins like this:

```text
Primary framework: stable-overhead-frame
Top priority: late-arrival
```

Run all built-in examples:

```bash
python3 examples/run_full_system_cases.py
```

## How It Fits Into A Video Agent

```text
badminton video
  -> video agent extracts structured observations
  -> BadmintonCoachSkill matches rules and priorities
  -> LLM writes a coaching report with evidence and retest metrics
```

Example code:

```python
from pathlib import Path
from badminton_coach_skill.rubric_loader import load_skill_knowledge
from badminton_coach_skill.issue_matcher import match_diagnosis
from badminton_coach_skill.report_compiler import compile_llm_context

knowledge = load_skill_knowledge(Path("skills/liu-hui-badminton-coach/references"))
diagnosis = match_diagnosis(player_profile, video_observation, knowledge)
llm_context = compile_llm_context(diagnosis)
```

`player_profile` and `video_observation` should follow:

- `schemas/player-profile.schema.json`
- `schemas/video-observation.schema.json`

See `examples/observations/` for ready-to-run inputs.

## Content-Level Video Corpus

The bundled Liu Hui-inspired knowledge base is distilled from the accessible non-YouTube public Bilibili index in this repository:

- 411 indexed Bilibili rows, including 2 discovery-only rows.
- 409 independent video jobs, of which 408 are accessible and 1 is unavailable.
- 408 sources with full-audio reviewed ASR coverage and 2610 public-safe teaching windows.
- 402 action or visible-demonstration sources with 6064 teaching-window keyframes for Qwen3-VL and Pose review.
- 6 conceptual or equipment sources explicitly kept as ASR-only evidence.
- 204 critical sources with 408 dense temporal sequences and 5304 frames for coarse 2D Pose change evidence.

The resulting evidence map connects source id, ASR timestamp, visible timestamp, optional temporal sequence, candidate framework, evidence level, and confidence boundary. The runtime uses that chain to explain why a framework was selected without treating model output as a coach-certified biomechanical fact.

YouTube is excluded by project decision. Douyin and Instagram remain discovery-level access gaps and are not counted as parsed content.

Only original summaries and evidence metadata belong in git. Raw videos, subtitles, ASR transcripts, OCR dumps, VLM outputs, cookies, tokens, and paid material stay private.

See `docs/content-video-pipeline.md` for the promotion rules.

## Usage Case

A beginner uploads a rear-court high-clear clip. The video agent observes:

- late rear-court arrival
- contact point behind the head
- low elbow before hit
- short follow-through

BadmintonCoachSkill ranks `late-arrival` first, because arrival and contact window should be fixed before advanced hand-speed or pronation advice. The output then includes observable evidence, a drill, and a retest metric so the report stays actionable.

## Current Coverage

The skill currently includes deterministic examples for:

```text
high_clear, smash, drop, drive, rear_footwork, front_footwork, backhand, serve_receive, doubles, match_transfer
```

The Liu Hui-inspired runtime contains 67 selectable frameworks, 44 reviewed corpus guardrails, 50 deterministic rubric rules, 10 visual evidence contracts, 30 drills, and 8 training plans across student-fit paths, equipment fit, high-clear rebuilds, racket preparation, power systems, smash variants, drop/slice/slide variants, footwork, backhand, drive/receive defense, doubles/singles tactics, match transfer, and safety-load selection.

The public corpus currently indexes hundreds of public/authorized source metadata rows, with separate records for collection status, deduplication, timestamp review, and access blockers.

## Important Boundaries

This project is not official, not authorized, and not affiliated with Liu Hui or any coaching organization.

BadmintonCoachSkill does not:

- claim Liu Hui personally reviewed any user video
- claim official certification or endorsement
- store raw videos, paid-course transcripts, screenshots, cookies, account exports, or long copied subtitles
- infer invisible biomechanics from a single 2D frame
- replace a qualified coach, medical professional, or injury-risk assessment

When evidence is missing, the skill should say `insufficient evidence` and request better observations instead of forcing a confident diagnosis.

## Repository Layout

- `skills/liu-hui-badminton-coach/`: the skill and coaching references.
- `src/badminton_coach_skill/`: deterministic rule loading, issue matching, and report-context compilation.
- `schemas/`: input and output contracts.
- `examples/`: runnable diagnosis examples.
- `data/source-index.tsv`: public source index.
- `data/corpus/`: public-safe corpus artifacts, review logs, taxonomy, and provenance records.
- `docs/`: collection, annotation, legal, and video-agent guidance.

## Provenance Model

The skill separates evidence levels:

- `source_backed`: supported by source metadata or reviewed notes within the allowed claim.
- `inferred`: synthesized from multiple public titles or metadata rows; useful but not a direct quote.
- `hypothesis`: useful as a diagnostic prompt, not a firm Liu Hui-derived rule.
- `insufficient_evidence`: required observations are missing.
- `asr_timestamp_reviewed_public_safe`: reviewed speech/topic routing evidence, not visual proof.
- `asr_only_conceptual_public_safe`: conceptual or equipment evidence with no action-bearing visual scope.
- `visual_model_structured_candidate_public_safe`: schema-validated still-frame visibility evidence, not motion or force evidence.
- `temporal_pose_proxy_public_safe`: coarse monocular 2D change evidence, not racket-face, shuttle-contact, force, or true joint-rotation evidence.

See:

- `skills/liu-hui-badminton-coach/references/corpus-provenance.md`
- `skills/liu-hui-badminton-coach/references/reviewed-corpus-rules.yaml`
- `data/corpus/collection-status.md`
