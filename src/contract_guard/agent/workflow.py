"""Evidence-first LangGraph contract review workflow."""

from __future__ import annotations

import hashlib
import inspect
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from langgraph.graph import END, START, StateGraph

from contract_guard.agent.state import ReviewState
from contract_guard.domain import (
    Clause,
    ContextSnippet,
    ContextSource,
    Evidence,
    Obligation,
    QualityMetrics,
    ReviewReport,
    ReviewSummary,
    RiskFinding,
    RiskLevel,
    StructuredAnalysis,
)
from contract_guard.services.llm import (
    ContractReviewer,
    OfflineContractReviewer,
    OpenAIContractReviewer,
)
from contract_guard.services.rules import RuleScanner


@runtime_checkable
class ContextProvider(Protocol):
    """Retrieval boundary for policy knowledge and prior-review memory."""

    def retrieve(
        self,
        *,
        contract_id: str,
        clauses: Sequence[Clause],
        org_id: str | None = None,
        session_id: str | None = None,
    ) -> Sequence[ContextSnippet]:
        """Return relevant snippets without mutating review state."""


class EmptyContextProvider:
    """No-op provider used by the offline/default graph."""

    def retrieve(
        self,
        *,
        contract_id: str,
        clauses: Sequence[Clause],
        org_id: str | None = None,
        session_id: str | None = None,
    ) -> Sequence[ContextSnippet]:
        del contract_id, clauses, org_id, session_id
        return ()


@dataclass(slots=True)
class ReviewDependencies:
    """All side-effecting graph dependencies in one injectable object."""

    reviewer: ContractReviewer = field(default_factory=OfflineContractReviewer)
    rule_scanner: RuleScanner = field(default_factory=RuleScanner)
    knowledge_provider: ContextProvider = field(default_factory=EmptyContextProvider)
    memory_provider: ContextProvider = field(default_factory=EmptyContextProvider)


def build_review_graph(dependencies: ReviewDependencies | None = None) -> Any:
    """Build and compile the complete evidence-grounded StateGraph."""

    deps = dependencies or ReviewDependencies()
    graph = StateGraph(ReviewState)

    def segment_node(state: ReviewState) -> dict[str, Any]:
        return {"clauses": segment_contract(state["text"])}

    def rule_scan_node(state: ReviewState) -> dict[str, Any]:
        return {"rule_findings": deps.rule_scanner.scan(state["clauses"])}

    def knowledge_node(state: ReviewState) -> dict[str, Any]:
        return {
            "knowledge_context": _retrieve_context(
                deps.knowledge_provider,
                source=ContextSource.KNOWLEDGE,
                contract_id=state["contract_id"],
                clauses=state["clauses"],
                org_id=state.get("org_id"),
                session_id=state.get("session_id"),
            )
        }

    def memory_node(state: ReviewState) -> dict[str, Any]:
        return {
            "memory_context": _retrieve_context(
                deps.memory_provider,
                source=ContextSource.MEMORY,
                contract_id=state["contract_id"],
                clauses=state["clauses"],
                org_id=state.get("org_id"),
                session_id=state.get("session_id"),
            )
        }

    def llm_node(state: ReviewState) -> dict[str, Any]:
        raw_analysis = deps.reviewer.analyze_clauses(
            state["clauses"],
            knowledge_context=state.get("knowledge_context", ()),
            memory_context=state.get("memory_context", ()),
        )
        analysis = _coerce_analysis(raw_analysis)
        valid_context_ids = {
            item.context_id
            for item in (
                *state.get("knowledge_context", ()),
                *state.get("memory_context", ()),
            )
        }
        findings = [
            finding.model_copy(
                update={
                    "context_refs": [
                        ref for ref in finding.context_refs if ref in valid_context_ids
                    ]
                }
            )
            for finding in analysis.findings
        ]
        return {
            "llm_findings": findings,
            "analysis_notes": analysis.analysis_notes,
            "llm_review_performed": not bool(getattr(deps.reviewer, "is_offline", False)),
        }

    def evidence_node(state: ReviewState) -> dict[str, Any]:
        candidates = [
            *state.get("rule_findings", ()),
            *state.get("llm_findings", ()),
        ]
        verified, rejected = verify_findings(
            candidates,
            clauses=state["clauses"],
            contract_text=state["text"],
        )
        return {
            "verified_findings": verified,
            "rejected_findings": rejected,
        }

    def obligation_node(state: ReviewState) -> dict[str, Any]:
        return {"obligations": extract_obligations(state["clauses"])}

    def quality_node(state: ReviewState) -> dict[str, Any]:
        return {"quality": assess_quality(state)}

    def report_node(state: ReviewState) -> dict[str, Any]:
        findings = state.get("verified_findings", [])
        obligations = state.get("obligations", [])
        summary = summarize_findings(findings)
        report_id = _stable_identifier(
            "report",
            state["contract_id"],
            *(finding.finding_id for finding in findings),
            *(obligation.obligation_id for obligation in obligations),
        )
        return {
            "report": ReviewReport(
                report_id=report_id,
                contract_id=state["contract_id"],
                clauses=state["clauses"],
                findings=findings,
                obligations=obligations,
                contexts=[
                    *state.get("knowledge_context", ()),
                    *state.get("memory_context", ()),
                ],
                analysis_notes=state.get("analysis_notes", []),
                run_metadata={
                    "workflow": "contractguard-review-v1",
                    "reviewer": type(deps.reviewer).__name__,
                    "model": getattr(deps.reviewer, "model_name", None),
                    "knowledge_provider": type(deps.knowledge_provider).__name__,
                    "memory_provider": type(deps.memory_provider).__name__,
                    "rule_ids": sorted(
                        {finding.rule_id for finding in findings if finding.rule_id is not None}
                    ),
                },
                quality=state["quality"],
                summary=summary,
            )
        }

    graph.add_node("segment_contract", segment_node)
    graph.add_node("scan_rules", rule_scan_node)
    graph.add_node("retrieve_knowledge", knowledge_node)
    graph.add_node("retrieve_memory", memory_node)
    graph.add_node("structured_llm_analysis", llm_node)
    graph.add_node("verify_evidence", evidence_node)
    graph.add_node("extract_obligations", obligation_node)
    graph.add_node("assess_quality", quality_node)
    graph.add_node("finalize_report", report_node)

    graph.add_edge(START, "segment_contract")
    graph.add_edge("segment_contract", "scan_rules")
    graph.add_edge("scan_rules", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "retrieve_memory")
    graph.add_edge("retrieve_memory", "structured_llm_analysis")
    graph.add_edge("structured_llm_analysis", "verify_evidence")
    graph.add_edge("verify_evidence", "extract_obligations")
    graph.add_edge("extract_obligations", "assess_quality")
    graph.add_edge("assess_quality", "finalize_report")
    graph.add_edge("finalize_report", END)
    return graph.compile()


class ContractReviewWorkflow:
    """Small facade around the compiled review graph."""

    def __init__(self, dependencies: ReviewDependencies | None = None) -> None:
        self.dependencies = dependencies or ReviewDependencies()
        self.graph = build_review_graph(self.dependencies)

    @classmethod
    def with_openai(
        cls,
        *,
        settings: object | Mapping[str, Any] | None = None,
        model: str | None = None,
        rule_scanner: RuleScanner | None = None,
        knowledge_provider: ContextProvider | None = None,
        memory_provider: ContextProvider | None = None,
    ) -> ContractReviewWorkflow:
        """Construct an online workflow while keeping configuration injected."""

        return cls(
            ReviewDependencies(
                reviewer=OpenAIContractReviewer(model=model, settings=settings),
                rule_scanner=rule_scanner or RuleScanner(),
                knowledge_provider=knowledge_provider or EmptyContextProvider(),
                memory_provider=memory_provider or EmptyContextProvider(),
            )
        )

    def review(
        self,
        text: str,
        contract_id: str | None = None,
        *,
        org_id: str | None = None,
        session_id: str | None = None,
    ) -> ReviewReport:
        """Review text synchronously and return the evidence-safe report."""

        normalized_contract_id = _validate_review_input(text, contract_id)
        result = self.graph.invoke(
            {
                "text": text,
                "contract_id": normalized_contract_id,
                "org_id": _normalize_optional_scope(org_id, "org_id"),
                "session_id": _normalize_optional_scope(session_id, "session_id"),
            }
        )
        return result["report"]

    async def areview(
        self,
        text: str,
        contract_id: str | None = None,
        *,
        org_id: str | None = None,
        session_id: str | None = None,
    ) -> ReviewReport:
        """Run the same graph via LangGraph's asynchronous entry point."""

        normalized_contract_id = _validate_review_input(text, contract_id)
        result = await self.graph.ainvoke(
            {
                "text": text,
                "contract_id": normalized_contract_id,
                "org_id": _normalize_optional_scope(org_id, "org_id"),
                "session_id": _normalize_optional_scope(session_id, "session_id"),
            }
        )
        return result["report"]


def review_contract(
    text: str,
    *,
    contract_id: str | None = None,
    org_id: str | None = None,
    session_id: str | None = None,
    dependencies: ReviewDependencies | None = None,
) -> ReviewReport:
    """Functional offline-friendly review entry point."""

    return ContractReviewWorkflow(dependencies).review(
        text,
        contract_id,
        org_id=org_id,
        session_id=session_id,
    )


def segment_contract(text: str) -> list[Clause]:
    """Split on blank lines while preserving exact source offsets."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("contract text cannot be blank")

    spans = list(_iter_nonempty_paragraphs(text))
    if not spans:
        raise ValueError("contract text does not contain a reviewable clause")

    clauses: list[Clause] = []
    for ordinal, (start, end) in enumerate(spans, start=1):
        clause_text = text[start:end]
        first_line = clause_text.splitlines()[0].strip()
        heading = first_line if _looks_like_heading(first_line) else None
        clauses.append(
            Clause(
                clause_id=f"clause-{ordinal:04d}",
                ordinal=ordinal,
                heading=heading,
                text=clause_text,
                start_offset=start,
                end_offset=end,
            )
        )
    return clauses


def verify_findings(
    findings: Sequence[RiskFinding],
    *,
    clauses: Sequence[Clause],
    contract_text: str,
) -> tuple[list[RiskFinding], list[RiskFinding]]:
    """Keep only findings with at least one exact quote in a known clause."""

    clause_by_id = {clause.clause_id: clause for clause in clauses}
    verified_findings: list[RiskFinding] = []
    rejected_findings: list[RiskFinding] = []

    for finding in findings:
        verified_evidence: list[Evidence] = []
        for evidence in finding.evidence:
            clause = clause_by_id.get(evidence.clause_id)
            if clause is None:
                continue
            verified = _verify_evidence(evidence, clause, contract_text)
            if verified is not None:
                verified_evidence.append(verified)

        if not verified_evidence:
            rejected_findings.append(finding)
            continue

        verified_clause_ids = list(dict.fromkeys(item.clause_id for item in verified_evidence))
        verified_findings.append(
            finding.model_copy(
                update={
                    "evidence": verified_evidence,
                    "clause_ids": verified_clause_ids,
                }
            )
        )
    return verified_findings, rejected_findings


def extract_obligations(clauses: Sequence[Clause]) -> list[Obligation]:
    """Extract explicit duty language without adding unstated legal meaning."""

    obligations: list[Obligation] = []
    seen: set[tuple[str, int, int]] = set()
    for clause in clauses:
        for sentence_match in _SENTENCE_RE.finditer(clause.text):
            raw = sentence_match.group(0)
            left_trim = len(raw) - len(raw.lstrip())
            quote = raw.strip()
            if not quote:
                continue
            local_start = sentence_match.start() + left_trim
            local_end = local_start + len(quote)
            trigger = _OBLIGATION_TRIGGER_RE.search(quote)
            if trigger is None or _is_non_obligation_trigger(quote, trigger.start()):
                continue

            absolute_start = clause.start_offset + local_start
            absolute_end = clause.start_offset + local_end
            dedupe_key = (clause.clause_id, absolute_start, absolute_end)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            action = quote[trigger.end() :].strip(" ，,:：。；;\t") or quote
            obligations.append(
                Obligation(
                    obligation_id=_stable_identifier(
                        "obligation",
                        clause.clause_id,
                        str(absolute_start),
                        str(absolute_end),
                    ),
                    obligor=_extract_obligor(quote[: trigger.start()]),
                    action=action,
                    clause_id=clause.clause_id,
                    due_expression=_extract_optional(_DUE_RE, quote),
                    condition=_extract_optional(_CONDITION_RE, quote),
                    evidence=Evidence(
                        clause_id=clause.clause_id,
                        quote=quote,
                        start_offset=absolute_start,
                        end_offset=absolute_end,
                        verified=True,
                    ),
                )
            )
    return obligations


def assess_quality(state: ReviewState) -> QualityMetrics:
    """Compute transparent coverage metrics from graph state."""

    rule_findings = state.get("rule_findings", [])
    llm_findings = state.get("llm_findings", [])
    verified = state.get("verified_findings", [])
    rejected = state.get("rejected_findings", [])
    candidates = [*rule_findings, *llm_findings]

    candidate_count = len(candidates)
    candidate_evidence_count = sum(len(item.evidence) for item in candidates)
    verified_evidence_count = sum(len(item.evidence) for item in verified)
    evidence_coverage = len(verified) / candidate_count if candidate_count else 1.0
    citation_validity = (
        min(verified_evidence_count / candidate_evidence_count, 1.0)
        if candidate_evidence_count
        else 1.0
    )
    has_clauses = bool(state.get("clauses"))
    completeness = ((1.0 if has_clauses else 0.0) + evidence_coverage + citation_validity) / 3

    warnings: list[str] = []
    if not state.get("llm_review_performed", False):
        warnings.append("LLM analysis was skipped; results are rule-based only.")
    if rejected:
        warnings.append(f"Rejected {len(rejected)} finding(s) with unsupported evidence.")
    if not verified:
        warnings.append("No evidence-backed risk finding was produced.")

    passed = has_clauses and not rejected and citation_validity == 1.0
    return QualityMetrics(
        clause_count=len(state.get("clauses", [])),
        rule_finding_count=len(rule_findings),
        llm_finding_count=len(llm_findings),
        verified_finding_count=len(verified),
        rejected_finding_count=len(rejected),
        obligation_count=len(state.get("obligations", [])),
        evidence_coverage=evidence_coverage,
        citation_validity=citation_validity,
        completeness=completeness,
        llm_review_performed=state.get("llm_review_performed", False),
        passed=passed,
        warnings=warnings,
    )


def summarize_findings(findings: Sequence[RiskFinding]) -> ReviewSummary:
    counts = {level: 0 for level in RiskLevel}
    for finding in findings:
        counts[finding.risk_level] += 1

    ranked = sorted(
        findings,
        key=lambda item: (
            _RISK_RANK[item.risk_level],
            item.confidence,
            item.finding_id,
        ),
        reverse=True,
    )
    highest = ranked[0].risk_level if ranked else None
    return ReviewSummary(
        total_findings=len(findings),
        by_risk_level=counts,
        highest_risk_level=highest,
        top_finding_ids=[item.finding_id for item in ranked[:5]],
    )


def _retrieve_context(
    provider: ContextProvider,
    *,
    source: ContextSource,
    contract_id: str,
    clauses: Sequence[Clause],
    org_id: str | None = None,
    session_id: str | None = None,
) -> list[ContextSnippet]:
    retrieve = provider.retrieve
    kwargs: dict[str, Any] = {"contract_id": contract_id, "clauses": clauses}
    parameters: Mapping[str, inspect.Parameter]
    try:
        parameters = inspect.signature(retrieve).parameters
    except (TypeError, ValueError):  # pragma: no cover - unusual native callable
        parameters = {}
    accepts_extra = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    )
    if accepts_extra or "org_id" in parameters:
        kwargs["org_id"] = org_id
    if accepts_extra or "session_id" in parameters:
        kwargs["session_id"] = session_id
    raw_items = retrieve(**kwargs)
    result: list[ContextSnippet] = []
    for index, raw_item in enumerate(raw_items):
        if isinstance(raw_item, ContextSnippet):
            item = raw_item
        elif isinstance(raw_item, str):
            item = ContextSnippet(
                context_id=f"{source.value}-{index + 1}",
                source=source,
                content=raw_item,
            )
        else:
            item = ContextSnippet.model_validate(raw_item)
        if item.source != source:
            raise ValueError(f"{source.value} provider returned {item.source.value} context")
        result.append(item)
    return result


def _coerce_analysis(value: Any) -> StructuredAnalysis:
    if isinstance(value, StructuredAnalysis):
        return value
    if isinstance(value, Mapping):
        return StructuredAnalysis.model_validate(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return StructuredAnalysis(findings=list(value))
    raise TypeError("reviewer must return StructuredAnalysis, a mapping, or findings")


def _verify_evidence(
    evidence: Evidence,
    clause: Clause,
    contract_text: str,
) -> Evidence | None:
    quote = evidence.quote
    requested_local_start = evidence.start_offset - clause.start_offset
    if (
        requested_local_start >= 0
        and clause.text[requested_local_start : requested_local_start + len(quote)] == quote
    ):
        local_start = requested_local_start
    else:
        local_start = clause.text.find(quote)
    if local_start < 0:
        return None

    absolute_start = clause.start_offset + local_start
    absolute_end = absolute_start + len(quote)
    if contract_text[absolute_start:absolute_end] != quote:
        return None
    return evidence.model_copy(
        update={
            "start_offset": absolute_start,
            "end_offset": absolute_end,
            "verified": True,
        }
    )


def _iter_nonempty_paragraphs(text: str) -> Sequence[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in _PARAGRAPH_RE.finditer(text):
        raw = match.group(0)
        left_trim = len(raw) - len(raw.lstrip())
        right_trim = len(raw.rstrip())
        start = match.start() + left_trim
        end = match.start() + right_trim
        if end > start:
            spans.append((start, end))
    return spans


def _looks_like_heading(text: str) -> bool:
    if len(text) > 120:
        return False
    return bool(_HEADING_RE.match(text))


def _extract_obligor(prefix: str) -> str:
    matches = list(_OBLIGOR_RE.finditer(prefix))
    if matches:
        return matches[-1].group(0).strip()
    return "未明确主体"


def _extract_optional(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0).strip() if match else None


def _is_non_obligation_trigger(text: str, trigger_start: int) -> bool:
    prefix = text[max(0, trigger_start - 1) : trigger_start]
    return prefix == "无"


def _validate_review_input(text: str, contract_id: str | None) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("contract text cannot be blank")
    if contract_id is not None:
        normalized = contract_id.strip()
        if not normalized:
            raise ValueError("contract_id cannot be blank")
        return normalized
    return _stable_identifier("contract", text)


def _normalize_optional_scope(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} cannot be blank")
    return normalized


def _stable_identifier(*parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:20]


_PARAGRAPH_RE = re.compile(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", re.DOTALL)
_HEADING_RE = re.compile(
    r"^(?:第[一二三四五六七八九十百千万零〇0-9]+条|"
    r"Article\s+\d+|\d+(?:\.\d+)*[.、)]|[（(][一二三四五六七八九十0-9]+[)）])",
    re.IGNORECASE,
)
_SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?", re.MULTILINE)
_OBLIGATION_TRIGGER_RE = re.compile(
    r"(?:应当|必须|不得|不应|须|应|\bshall\b|\bmust\b)",
    re.IGNORECASE,
)
_OBLIGOR_RE = re.compile(
    r"(?:甲方|乙方|双方|任何一方|供应商|客户|承包商|服务方|"
    r"许可方|被许可方|Party\s+[AB]|Supplier|Customer|Contractor)",
    re.IGNORECASE,
)
_DUE_RE = re.compile(
    r"(?:在[^，。；;]{1,30}?前|自[^，。；;]{0,20}?起[^，。；;]{0,20}?内|"
    r"\bwithin\s+\d+\s+(?:business\s+)?days?\b)",
    re.IGNORECASE,
)
_CONDITION_RE = re.compile(
    r"(?:如|若|如果|当)[^，。；;]{1,40}|\b(?:if|when)\b[^,.;]{1,40}",
    re.IGNORECASE,
)
_RISK_RANK = {
    RiskLevel.INFO: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


__all__ = [
    "ContextProvider",
    "ContractReviewWorkflow",
    "EmptyContextProvider",
    "ReviewDependencies",
    "assess_quality",
    "build_review_graph",
    "extract_obligations",
    "review_contract",
    "segment_contract",
    "summarize_findings",
    "verify_findings",
]
