"""Contract comparison endpoints for ContractGuard."""

from __future__ import annotations

import difflib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from contract_guard.api.dependencies import (
    TenantScope,
    get_repository,
    get_tenant_scope,
)
from contract_guard.services.storage import ReviewRepository, StoredReview

router = APIRouter(tags=["compare"], prefix="/compare")


# ─── Request / Response schemas ──────────────────────────────────────────────


class CompareRequest(BaseModel):
    review_a_id: str
    review_b_id: str


class ClauseEntry(BaseModel):
    index: int
    text: str
    status: str  # "unchanged" | "modified" | "removed" | "added"


class DiffPair(BaseModel):
    index_a: int | None = None
    index_b: int | None = None
    similarity: float = 0.0
    status: str  # "unchanged" | "modified" | "added" | "removed"


class RiskDeltaItem(BaseModel):
    title: str
    risk_level: str
    source: str


class RiskDelta(BaseModel):
    new_risks: list[RiskDeltaItem] = Field(default_factory=list)
    resolved_risks: list[RiskDeltaItem] = Field(default_factory=list)
    unchanged_count: int = 0


class CompareSummary(BaseModel):
    total_clauses_a: int = 0
    total_clauses_b: int = 0
    added: int = 0
    removed: int = 0
    modified: int = 0
    unchanged: int = 0


class CompareResponse(BaseModel):
    clauses_a: list[ClauseEntry] = Field(default_factory=list)
    clauses_b: list[ClauseEntry] = Field(default_factory=list)
    diff_pairs: list[DiffPair] = Field(default_factory=list)
    risk_delta: RiskDelta = Field(default_factory=RiskDelta)
    summary: CompareSummary = Field(default_factory=CompareSummary)


class VersionListResponse(BaseModel):
    versions: list[Any] = Field(default_factory=list)
    message: str = ""


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _load_review_for_scope(
    repository: ReviewRepository,
    review_id: str,
    scope: TenantScope,
) -> StoredReview:
    """Load a review scoped to the current org, raising 404 if not found."""
    actor_getter = getattr(repository, "get_review_for_actor", None)
    review: StoredReview | None = None
    if scope.authenticated and callable(actor_getter):
        review = actor_getter(
            review_id,
            org_id=scope.org_id,
            user_id=scope.user_id,
            can_manage_all=scope.role.can_view_all_reviews,
            include_deleted=False,
        )
    else:
        review = repository.get_review(review_id, org_id=scope.org_id, session_id=scope.session_id)

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found",
        )
    return review


def _extract_contract_text(review: StoredReview) -> str:
    """Extract the contract text from a review's report clauses."""
    report = review.report
    if not isinstance(report, dict):
        return ""
    clauses = report.get("clauses", [])
    if isinstance(clauses, list) and clauses:
        texts = []
        for clause in clauses:
            if isinstance(clause, dict):
                text = clause.get("text", "")
                if text:
                    texts.append(str(text))
        if texts:
            return "\n\n".join(texts)
    return ""


def _segment_clauses(text: str) -> list[str]:
    """Segment contract text into clauses by splitting on double newlines."""
    if not text or not text.strip():
        return []
    paragraphs = text.split("\n\n")
    return [p.strip() for p in paragraphs if p.strip()]


def _extract_findings(review: StoredReview) -> list[dict[str, Any]]:
    """Extract risk findings from a review's report."""
    report = review.report
    if not isinstance(report, dict):
        return []
    findings = report.get("findings", [])
    if isinstance(findings, dict):
        findings = findings.get("items", [])
    if not isinstance(findings, list):
        return []
    return [f for f in findings if isinstance(f, dict)]


def _compute_clause_diff(
    clauses_a: list[str], clauses_b: list[str]
) -> tuple[list[ClauseEntry], list[ClauseEntry], list[DiffPair], CompareSummary]:
    """Compute clause-level diff using SequenceMatcher."""
    matcher = difflib.SequenceMatcher(None, clauses_a, clauses_b, autojunk=False)
    opcodes = matcher.get_opcodes()

    entries_a: list[ClauseEntry] = []
    entries_b: list[ClauseEntry] = []
    diff_pairs: list[DiffPair] = []

    added_count = 0
    removed_count = 0
    modified_count = 0
    unchanged_count = 0

    # Track which indices have been added to entries
    a_added: set[int] = set()
    b_added: set[int] = set()

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for offset in range(i2 - i1):
                idx_a = i1 + offset
                idx_b = j1 + offset
                entries_a.append(ClauseEntry(index=idx_a, text=clauses_a[idx_a], status="unchanged"))
                entries_b.append(ClauseEntry(index=idx_b, text=clauses_b[idx_b], status="unchanged"))
                diff_pairs.append(DiffPair(index_a=idx_a, index_b=idx_b, similarity=1.0, status="unchanged"))
                a_added.add(idx_a)
                b_added.add(idx_b)
                unchanged_count += 1

        elif tag == "replace":
            # Pair up clauses from both sides for modification detection
            a_range = list(range(i1, i2))
            b_range = list(range(j1, j2))
            paired = min(len(a_range), len(b_range))

            for k in range(paired):
                idx_a = a_range[k]
                idx_b = b_range[k]
                similarity = difflib.SequenceMatcher(
                    None, clauses_a[idx_a], clauses_b[idx_b]
                ).ratio()
                entries_a.append(ClauseEntry(index=idx_a, text=clauses_a[idx_a], status="modified"))
                entries_b.append(ClauseEntry(index=idx_b, text=clauses_b[idx_b], status="modified"))
                diff_pairs.append(
                    DiffPair(index_a=idx_a, index_b=idx_b, similarity=round(similarity, 4), status="modified")
                )
                a_added.add(idx_a)
                b_added.add(idx_b)
                modified_count += 1

            # Remaining A clauses are removed
            for k in range(paired, len(a_range)):
                idx_a = a_range[k]
                entries_a.append(ClauseEntry(index=idx_a, text=clauses_a[idx_a], status="removed"))
                diff_pairs.append(DiffPair(index_a=idx_a, index_b=None, similarity=0.0, status="removed"))
                a_added.add(idx_a)
                removed_count += 1

            # Remaining B clauses are added
            for k in range(paired, len(b_range)):
                idx_b = b_range[k]
                entries_b.append(ClauseEntry(index=idx_b, text=clauses_b[idx_b], status="added"))
                diff_pairs.append(DiffPair(index_a=None, index_b=idx_b, similarity=0.0, status="added"))
                b_added.add(idx_b)
                added_count += 1

        elif tag == "delete":
            for idx_a in range(i1, i2):
                entries_a.append(ClauseEntry(index=idx_a, text=clauses_a[idx_a], status="removed"))
                diff_pairs.append(DiffPair(index_a=idx_a, index_b=None, similarity=0.0, status="removed"))
                a_added.add(idx_a)
                removed_count += 1

        elif tag == "insert":
            for idx_b in range(j1, j2):
                entries_b.append(ClauseEntry(index=idx_b, text=clauses_b[idx_b], status="added"))
                diff_pairs.append(DiffPair(index_a=None, index_b=idx_b, similarity=0.0, status="added"))
                b_added.add(idx_b)
                added_count += 1

    summary = CompareSummary(
        total_clauses_a=len(clauses_a),
        total_clauses_b=len(clauses_b),
        added=added_count,
        removed=removed_count,
        modified=modified_count,
        unchanged=unchanged_count,
    )

    return entries_a, entries_b, diff_pairs, summary


def _compute_risk_delta(
    findings_a: list[dict[str, Any]], findings_b: list[dict[str, Any]]
) -> RiskDelta:
    """Compare risk findings between two reports."""

    def _finding_key(f: dict[str, Any]) -> str:
        return str(f.get("title", "")).strip().lower()

    keys_a = {_finding_key(f) for f in findings_a}
    keys_b = {_finding_key(f) for f in findings_b}

    new_risks: list[RiskDeltaItem] = []
    resolved_risks: list[RiskDeltaItem] = []

    for f in findings_b:
        key = _finding_key(f)
        if key not in keys_a:
            new_risks.append(
                RiskDeltaItem(
                    title=str(f.get("title", "Unknown")),
                    risk_level=str(f.get("risk_level", "info")),
                    source=str(f.get("source", "unknown")),
                )
            )

    for f in findings_a:
        key = _finding_key(f)
        if key not in keys_b:
            resolved_risks.append(
                RiskDeltaItem(
                    title=str(f.get("title", "Unknown")),
                    risk_level=str(f.get("risk_level", "info")),
                    source=str(f.get("source", "unknown")),
                )
            )

    unchanged_count = len(keys_a & keys_b)

    return RiskDelta(
        new_risks=new_risks,
        resolved_risks=resolved_risks,
        unchanged_count=unchanged_count,
    )


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("", response_model=CompareResponse, summary="Compare two reviews")
async def compare_reviews(
    body: CompareRequest,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> CompareResponse:
    """Compare two contract reviews side-by-side with clause diff and risk delta."""
    if body.review_a_id == body.review_b_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot compare a review with itself",
        )

    review_a = _load_review_for_scope(repository, body.review_a_id, scope)
    review_b = _load_review_for_scope(repository, body.review_b_id, scope)

    # Extract and segment contract text
    text_a = _extract_contract_text(review_a)
    text_b = _extract_contract_text(review_b)

    clauses_a = _segment_clauses(text_a)
    clauses_b = _segment_clauses(text_b)

    # Compute clause-level diff
    entries_a, entries_b, diff_pairs, summary = _compute_clause_diff(clauses_a, clauses_b)

    # Compute risk delta
    findings_a = _extract_findings(review_a)
    findings_b = _extract_findings(review_b)
    risk_delta = _compute_risk_delta(findings_a, findings_b)

    return CompareResponse(
        clauses_a=entries_a,
        clauses_b=entries_b,
        diff_pairs=diff_pairs,
        risk_delta=risk_delta,
        summary=summary,
    )


@router.get(
    "/reviews/{review_id}/versions",
    response_model=VersionListResponse,
    summary="List version history for a review",
)
async def list_versions(
    review_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> VersionListResponse:
    """List version history for a review. Currently returns empty (pending DB migration)."""
    # Verify the review exists and is accessible
    _load_review_for_scope(repository, review_id, scope)
    return VersionListResponse(versions=[], message="版本追踪功能即将上线")


__all__ = ["router"]
