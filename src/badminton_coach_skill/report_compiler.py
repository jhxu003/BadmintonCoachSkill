from __future__ import annotations

from typing import Any


def compile_llm_context(diagnosis: dict[str, Any]) -> str:
    """Create a compact, evidence-first context block for an LLM report."""
    lines = [
        "Use this diagnosis as bounded evidence. Do not add unsupported issues.",
        f"Primary framework: {diagnosis['primary_framework']}",
        f"Overall confidence: {diagnosis['confidence']}",
    ]

    if diagnosis.get("missing_evidence"):
        lines.append("Missing evidence: " + ", ".join(diagnosis["missing_evidence"]))

    if diagnosis.get("corpus_evidence"):
        lines.append("")
        lines.append("Corpus evidence chains (routing support, not biomechanical proof):")
        for item in diagnosis["corpus_evidence"]:
            lines.append(
                f"Source: {item.get('source_id')} | Framework: {item.get('framework_id')}"
            )
            window = item.get("asr_window")
            if window:
                lines.append(
                    "ASR window: "
                    f"{window.get('window_id')} "
                    f"({window.get('start_seconds')}-{window.get('end_seconds')}s)"
                )
            if item.get("visual_timestamps"):
                lines.append(
                    "Visual timestamps: "
                    + ", ".join(f"{value}s" for value in item["visual_timestamps"])
                )
            for observation in item.get("visual_observations", []):
                body = ",".join(observation.get("body_configuration", [])) or "none"
                limits = ",".join(observation.get("visibility_limits", [])) or "none"
                lines.append(
                    f"Visible observation at {observation.get('timestamp_seconds')}s: "
                    f"person_visible={observation.get('person_visible')}; "
                    f"racket_visibility={observation.get('racket_visibility')}; "
                    f"racket_position={observation.get('racket_position')}; "
                    f"view={observation.get('primary_subject_view')}; "
                    f"body={body}; limits={limits}; "
                    f"confidence={observation.get('confidence')}"
                )
            if item.get("temporal_sequences"):
                lines.append(
                    "Temporal sequence: "
                    + ", ".join(
                        str(sequence.get("sequence_id"))
                        for sequence in item["temporal_sequences"]
                    )
                )
            lines.append("Evidence levels: " + ", ".join(item.get("evidence_levels", [])))
            lines.append("Boundary: " + item.get("confidence_boundary", ""))

    for issue in diagnosis.get("issues", []):
        lines.extend(
            [
                "",
                f"Issue: {issue['issue_id']} - {issue['issue']}",
                "Evidence: " + "; ".join(issue.get("evidence", [])),
                "Why it matters: " + "; ".join(issue.get("likely_effect", [])),
                "Correction: " + issue.get("correction_principle", ""),
                "Retest: " + "; ".join(issue.get("retest_metrics", [])),
            ]
        )
        if issue.get("drills"):
            drill = issue["drills"][0]
            lines.append(f"Drill: {drill['name']} ({drill['dosage']})")

    return "\n".join(lines)
