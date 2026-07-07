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

