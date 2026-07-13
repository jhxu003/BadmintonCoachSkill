# Li Yuxuan Public Corpus

This directory contains public-safe provenance artifacts for the non-official Li Yuxuan badminton coaching Skill.

It contains public source indexes, original topic summaries, source identifiers, timestamp pointers, aggregate review status, and provenance labels. It excludes raw media, complete ASR transcripts, screenshots, model dumps, private runtime inputs, and paid-course material.

## Source Boundary

- Official Bilibili account: `李宇轩教练` (UID `519050265`).
- Public account discovery found 389 unique Bilibili BV candidates through ordinary uploads, official seasons, and the account's live-replay series.
- 382 candidates were individually verified as accessible, free, and owned by the official account. They are eligible for content parsing.
- 7 historical BV candidates no longer resolve through the public detail endpoint. They remain in the source index as unavailable discovery records and are excluded from media parsing.
- The public paid-course catalog is retained only to record a coverage boundary. Paid lesson content is never downloaded, transcribed, or used as technical evidence.

## Evidence Layers

1. `source-index.tsv`: canonical public-source ledger.
2. `system-taxonomy.yaml`, `teaching-points.yaml`, and `source-topic-map.yaml`: concise, source-linked system map.
3. `video-asr-teaching-windows-full.yaml`: public-safe candidate timestamps distilled from private ASR.
4. `video-asr-timestamp-review.yaml`: original topic/timestamp summaries without transcript text.
5. `video-visual-evidence-summary.yaml`: aggregate sparse visibility review, with no images or model text.
6. `video-temporal-pose-summary.yaml`: aggregate 2D body-geometry proxy for selected motion sequences, with no coordinates.
7. The bundled Skill references contain the runtime frameworks, deterministic rules, drills, plans, and source-linked evidence map.

The completed accessible corpus contributes 2,886 reviewed timestamp windows, 369 sparse visual-review sources with 6,240 planned frames, and 306 temporal Pose sources with 611 sequences and 7,943 dense frames.

## Promotion Boundary

- ASR can support topic routing, timestamp lookup, question selection, and original summaries. It cannot be presented as a quote, exact coaching language, or visual biomechanical proof.
- Sparse VLM stills can describe whether a person, racket, posture, or on-screen text is visible. They cannot prove motion, force, contact, grip pressure, or true joint rotation.
- Dense monocular Pose can describe coarse 2D change over a planned sequence. It cannot prove shuttle contact, racket face, calibrated 3D biomechanics, force, or true internal rotation.
- Any deterministic Skill rule must carry a source id, evidence level, confidence boundary, and promotion status.
- Processing manifests, private artifact locations, raw model outputs, and controller logs are intentionally excluded from the public repository.
