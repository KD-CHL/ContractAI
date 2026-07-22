"""Core domain models for evidence-grounded contract review.

The models in this module intentionally make evidence mandatory for every risk
finding and obligation.  Syntactic validation alone cannot prove that a quote
exists in a contract; the workflow performs that verification before building
a :class:`ReviewReport`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DomainModel(BaseModel):
    """Strict base model shared by all public domain objects."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class RiskLevel(StrEnum):
    """Normalized risk levels used by rules and LLM reviewers."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingSource(StrEnum):
    """Origin of a finding before/after evidence reconciliation."""

    RULE = "rule"
    LLM = "llm"
    HYBRID = "hybrid"


class ContextSource(StrEnum):
    """Permitted sources for retrieved context."""

    KNOWLEDGE = "knowledge"
    MEMORY = "memory"


class Clause(DomainModel):
    """A source-preserving segment of the submitted contract."""

    clause_id: str = Field(min_length=1)
    ordinal: int = Field(ge=1)
    heading: str | None = None
    text: str = Field(min_length=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_offsets(self) -> Clause:
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class Evidence(DomainModel):
    """An exact quote anchored to a contract clause.

    ``verified`` may only be trusted after the workflow has checked the quote
    against the original contract text.  LLM and rule producers should leave
    it false; the evidence verification node sets it to true.
    """

    clause_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    verified: bool = False

    @model_validator(mode="after")
    def validate_offsets(self) -> Evidence:
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class ContextSnippet(DomainModel):
    """Retrieved knowledge or prior-review memory supplied to the reviewer."""

    context_id: str = Field(min_length=1)
    source: ContextSource
    content: str = Field(min_length=1)
    citation: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskFinding(DomainModel):
    """A potentially risky contract term supported by quoted evidence."""

    finding_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: str = Field(min_length=1)
    risk_level: RiskLevel
    source: FindingSource
    rule_id: str | None = None
    context_refs: list[str] = Field(default_factory=list)
    clause_ids: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(min_length=1)
    recommendation: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("clause_ids", "context_refs")
    @classmethod
    def unique_clause_ids(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item for item in value if item))

    @model_validator(mode="after")
    def evidence_must_reference_declared_clauses(self) -> RiskFinding:
        evidence_clause_ids = list(dict.fromkeys(item.clause_id for item in self.evidence))
        if not self.clause_ids:
            object.__setattr__(self, "clause_ids", evidence_clause_ids)
            return self

        missing = set(evidence_clause_ids).difference(self.clause_ids)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"evidence references undeclared clause ids: {missing_text}")
        return self


class Obligation(DomainModel):
    """A deterministic extraction of a duty stated in the contract."""

    obligation_id: str = Field(min_length=1)
    obligor: str = Field(min_length=1)
    action: str = Field(min_length=1)
    clause_id: str = Field(min_length=1)
    evidence: Evidence
    due_expression: str | None = None
    condition: str | None = None

    @model_validator(mode="after")
    def evidence_must_reference_clause(self) -> Obligation:
        if self.evidence.clause_id != self.clause_id:
            raise ValueError("obligation evidence must reference its clause_id")
        return self


class QualityMetrics(DomainModel):
    """Auditable coverage and citation metrics for a review run."""

    clause_count: int = Field(ge=0)
    rule_finding_count: int = Field(ge=0)
    llm_finding_count: int = Field(ge=0)
    verified_finding_count: int = Field(ge=0)
    rejected_finding_count: int = Field(ge=0)
    obligation_count: int = Field(ge=0)
    evidence_coverage: float = Field(ge=0.0, le=1.0)
    citation_validity: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    llm_review_performed: bool
    passed: bool
    warnings: list[str] = Field(default_factory=list)


class ReviewSummary(DomainModel):
    """Compact deterministic summary suitable for API/UI display."""

    total_findings: int = Field(ge=0)
    by_risk_level: dict[RiskLevel, int]
    highest_risk_level: RiskLevel | None = None
    top_finding_ids: list[str] = Field(default_factory=list)


class StructuredAnalysis(DomainModel):
    """Schema returned by structured-output LLM reviewers."""

    findings: list[RiskFinding] = Field(default_factory=list)
    analysis_notes: list[str] = Field(default_factory=list)


class ReviewReport(DomainModel):
    """Final report containing only source-verified conclusions."""

    report_id: str = Field(min_length=1)
    contract_id: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    clauses: list[Clause]
    findings: list[RiskFinding]
    obligations: list[Obligation]
    contexts: list[ContextSnippet] = Field(default_factory=list)
    analysis_notes: list[str] = Field(default_factory=list)
    run_metadata: dict[str, Any] = Field(default_factory=dict)
    quality: QualityMetrics
    summary: ReviewSummary
    disclaimer: str = "本报告仅提供基于所引合同文本的风险提示，不构成法律意见。"

    @model_validator(mode="after")
    def require_verified_report_evidence(self) -> ReviewReport:
        unverified_findings = [
            finding.finding_id
            for finding in self.findings
            if not finding.evidence or any(not evidence.verified for evidence in finding.evidence)
        ]
        unverified_obligations = [
            obligation.obligation_id
            for obligation in self.obligations
            if not obligation.evidence.verified
        ]
        if unverified_findings or unverified_obligations:
            invalid_ids = ", ".join([*unverified_findings, *unverified_obligations])
            raise ValueError(
                "review reports cannot contain conclusions without verified "
                f"evidence: {invalid_ids}"
            )
        return self
