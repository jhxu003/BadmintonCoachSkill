# Keyframe Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Review all accessible Liu Hui sparse keyframes, select teaching-useful frames, and produce private accepted/rejected contact-sheet previews.

**Architecture:** A local inventory builder joins public frame plans with private VLM/Pose artifacts and node-resident JPEGs. It computes explainable image, visibility, action, and duplicate scores, ranks frames per teaching window, copies only preview selections to ignored storage, and renders topic-stratified contact sheets for human review.

**Tech Stack:** Python 3, Pillow, NumPy, PyYAML, existing private JSON artifacts, SSH access to compute-node `/tmp` storage.

## Global Constraints

- Raw frames and review inventories remain under ignored `data/raw-private/`.
- No test or evaluation directories are added to the repository.
- No raw VLM response, Pose coordinates, transcript, token, or server absolute path is published.
- Selection decisions must have explicit component scores and reasons.

---

### Task 1: Build The Review Inventory

**Files:**
- Create: `scripts/review_keyframe_quality.py`
- Create privately at runtime: `data/raw-private/keyframe-review/frame-inventory.jsonl`

**Interfaces:**
- Consumes: visual pipeline manifest, keyframe manifests, VLM/Pose JSON, node frame roots.
- Produces: normalized frame records and per-window ranked selection decisions.

- [ ] Implement artifact joining by job id and frame id.
- [ ] Resolve each JPEG from shared storage or configured compute-node roots.
- [ ] Compute sharpness, luminance, contrast, subject scale, VLM visibility, Pose coverage, action-state, and topic-fit scores.
- [ ] Compute perceptual hashes and suppress near duplicates within each teaching window.
- [ ] Keep at most three distinct useful frames per teaching window and record rejection reasons.
- [ ] Run a small `/tmp` smoke check against several jobs and verify every emitted record has provenance and a decision.

### Task 2: Render Private Review Sheets

**Files:**
- Modify: `scripts/review_keyframe_quality.py`
- Create privately at runtime: `data/raw-private/keyframe-review/previews/*.jpg`

**Interfaces:**
- Consumes: selected and rejected inventory records with resolvable JPEG paths.
- Produces: overview, accepted-frame, and topic-specific contact sheets.

- [ ] Render fixed-size thumbnails without changing aspect ratio.
- [ ] Add source id, timestamp, topics, score, decision, and concise reasons beneath each thumbnail.
- [ ] Create a balanced accepted/rejected overview and an accepted-only representative sheet.
- [ ] Create topic sheets for the ten required technical categories.
- [ ] Verify generated JPEG dimensions and nonblank pixel variance.

### Task 3: Human Review And Threshold Refinement

**Files:**
- Modify if required: `scripts/review_keyframe_quality.py`
- Create privately at runtime: `data/raw-private/keyframe-review/selection-summary.yaml`

**Interfaces:**
- Consumes: first-pass contact sheets and inventory statistics.
- Produces: final thresholds, final inventory, and reviewed previews.

- [ ] Inspect overview, accepted-only, and topic sheets visually.
- [ ] Identify systematic false acceptance and false rejection patterns.
- [ ] Adjust scoring or hard-rejection thresholds once when supported by visible examples.
- [ ] Rebuild the complete inventory and previews.
- [ ] Record final frame counts, selection rate, unavailable frames, duplicate removals, and rejection-reason counts.

### Task 4: Verify And Document

**Files:**
- Modify: `docs/content-video-pipeline.md`

**Interfaces:**
- Consumes: final private summary and preview outputs.
- Produces: public-safe reproduction guidance and verification evidence.

- [ ] Document the distinction between ASR-guided samples and reviewed teaching keyframes.
- [ ] Run Python compilation and source-integrity checks.
- [ ] Verify private output paths are ignored and no image or raw artifact is tracked.
- [ ] Run `git diff --check` and inspect the final worktree.
