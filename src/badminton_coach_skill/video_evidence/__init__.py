"""Bounded frame evidence used by the video coaching application."""

from .contracts import CoachReference, FrameRef, IssueEvidence
from .evidence_resolver import resolve_issue_evidence

__all__ = [
    "CoachReference",
    "FrameRef",
    "IssueEvidence",
    "resolve_issue_evidence",
]
