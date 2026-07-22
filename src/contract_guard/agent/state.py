"""State schema shared by ContractGuard LangGraph nodes."""

from __future__ import annotations

from typing import TypedDict

from contract_guard.domain import (
    Clause,
    ContextSnippet,
    Obligation,
    QualityMetrics,
    ReviewReport,
    RiskFinding,
)


class ReviewState(TypedDict, total=False):
    contract_id: str
    org_id: str | None
    session_id: str | None
    text: str
    clauses: list[Clause]
    rule_findings: list[RiskFinding]
    knowledge_context: list[ContextSnippet]
    memory_context: list[ContextSnippet]
    llm_findings: list[RiskFinding]
    analysis_notes: list[str]
    llm_review_performed: bool
    verified_findings: list[RiskFinding]
    rejected_findings: list[RiskFinding]
    obligations: list[Obligation]
    quality: QualityMetrics
    report: ReviewReport


__all__ = ["ReviewState"]
