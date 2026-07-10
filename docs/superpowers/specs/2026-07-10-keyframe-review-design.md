# Keyframe Review Design

## Objective

Review the Liu Hui corpus keyframes as teaching evidence rather than treating every ASR-guided sample as useful. Produce a private, reproducible selection inventory and contact-sheet previews that show both accepted frames and representative rejection cases.

## Inputs

- `data/corpus/video-visual-pipeline-manifest.yaml` provides the planned source, teaching window, timestamp, and topic relationships.
- `data/raw-private/video-corpus/*/keyframes/manifest.json` provides extracted-frame metadata.
- `data/raw-private/video-corpus/*/vlm.json` provides structured visibility observations.
- `data/raw-private/video-corpus/*/pose.json` provides person count, body coverage, and keypoint confidence.
- Keyframe JPEG files remain on compute-node `/tmp` storage and are copied only into the ignored private review directory when selected for preview.

## Review Model

Each frame receives transparent component scores rather than a single opaque model judgment:

- visible person and usable Pose coverage
- visible racket and racket position
- action-bearing body configuration
- subject scale and crop quality
- VLM confidence and visibility limitations
- image sharpness, brightness, and blank-frame checks
- perceptual similarity to neighboring frames in the same teaching window
- consistency with the teaching-window topic tags

Hard rejection is limited to missing/corrupt images, blank or near-blank frames, no visible person, unusably small subject, and severe blur. Other frames remain candidates and are ranked within their teaching window.

## Selection Policy

- Review all planned sparse frames that can be resolved from node storage.
- Group frames by `source_window_id`.
- Keep up to three frames per window when they provide distinct useful states.
- Prefer a preparation or raised-racket state, an action-bearing middle state, and a follow-through/recovery state when present.
- Do not keep near-duplicate frames solely to satisfy a quota.
- Keep a lower-ranked frame when it provides a distinct camera view or body state useful for understanding the teaching point.
- Record component scores, final decision, rank, and explicit reasons in private JSONL/CSV outputs.

## Human Review

Generate topic-stratified contact sheets for high clear, smash, top elbow, hip rotation, internal rotation, footwork, drop, drive, serve/receive, and doubles. Inspect accepted and rejected samples side by side. Adjust thresholds once if systematic false acceptance or false rejection is visible, then rebuild the final inventory and previews.

## Outputs

Private outputs under `data/raw-private/keyframe-review/`:

- `frame-inventory.jsonl`: one record per reviewed frame
- `selection-summary.yaml`: counts and rejection reasons
- `selected-frames/`: copied preview frames only
- `previews/keyframe-review-overview.jpg`: accepted/rejected comparison
- `previews/keyframe-review-selected.jpg`: representative accepted frames
- `previews/topics/*.jpg`: topic-specific contact sheets

The repository may contain the reusable review script and this methodology, but no extracted video frames or raw model artifacts.

## Acceptance Criteria

- Every planned sparse frame is either resolved and reviewed or recorded as unavailable.
- Every selected frame has a source id, timestamp, teaching-window id, topic tags, score, and selection reasons.
- Near duplicates are suppressed within a teaching window.
- The overview visibly includes accepted and rejected examples.
- Human inspection confirms that accepted examples are predominantly action-bearing teaching frames rather than talking-head, empty, or neutral-standing frames.
