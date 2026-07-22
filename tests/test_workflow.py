from __future__ import annotations

from collections.abc import Sequence

import pytest
from pydantic import ValidationError

from contract_guard.agent import (
    ContractReviewWorkflow,
    ReviewDependencies,
    build_review_graph,
    segment_contract,
)
from contract_guard.domain import (
    Clause,
    ContextSnippet,
    ContextSource,
    Evidence,
    FindingSource,
    RiskFinding,
    RiskLevel,
    StructuredAnalysis,
)
from contract_guard.services.llm import (
    DEFAULT_OPENAI_MODEL,
    LLMStructuredAnalysis,
    OfflineContractReviewer,
    OpenAIContractReviewer,
    resolve_openai_base_url,
    resolve_openai_model,
)

CONTRACT_TEXT = """第一条 期限
本合同期限届满后自动续期，任一方应在到期前三十日书面通知对方。

第二条 付款
甲方必须在收到合格发票后十日内付款。"""


class RecordingProvider:
    def __init__(self, source: ContextSource) -> None:
        self.source = source
        self.calls = 0

    def retrieve(
        self,
        *,
        contract_id: str,
        clauses: Sequence[Clause],
    ) -> Sequence[ContextSnippet]:
        self.calls += 1
        assert contract_id == "contract-123"
        assert clauses
        return [
            ContextSnippet(
                context_id=f"{self.source.value}-1",
                source=self.source,
                content=f"{self.source.value} context",
                citation="demo://context/1",
            )
        ]


class EvidenceCheckingFakeReviewer:
    is_offline = False

    def __init__(self) -> None:
        self.received_context = False

    def analyze_clauses(
        self,
        clauses: Sequence[Clause],
        *,
        knowledge_context: Sequence[ContextSnippet] = (),
        memory_context: Sequence[ContextSnippet] = (),
    ) -> StructuredAnalysis:
        self.received_context = bool(knowledge_context and memory_context)
        clause = clauses[0]
        quote = "到期前三十日书面通知"
        # Deliberately wrong offsets: the verification node must safely relocate
        # the exact quote rather than trusting model-provided positions.
        valid = RiskFinding(
            finding_id="llm-valid",
            title="通知窗口需要复核",
            description="续期通知窗口应与业务操作流程核对。",
            category="term",
            risk_level=RiskLevel.MEDIUM,
            source=FindingSource.LLM,
            context_refs=["knowledge-1", "invented-context"],
            evidence=[
                Evidence(
                    clause_id=clause.clause_id,
                    quote=quote,
                    start_offset=0,
                    end_offset=1,
                )
            ],
            recommendation="确认提醒与通知送达机制。",
            confidence=0.8,
        )
        hallucinated = RiskFinding(
            finding_id="llm-hallucinated",
            title="不存在的立即撤销权",
            description="这条结论没有合同原文支持。",
            category="termination",
            risk_level=RiskLevel.HIGH,
            source=FindingSource.LLM,
            evidence=[
                Evidence(
                    clause_id=clause.clause_id,
                    quote="任何一方可立即撤销合同",
                    start_offset=0,
                    end_offset=1,
                )
            ],
            confidence=0.5,
        )
        return StructuredAnalysis(
            findings=[valid, hallucinated],
            analysis_notes=["Reviewed renewal and payment clauses."],
        )


def test_graph_contains_all_review_stages() -> None:
    graph = build_review_graph()
    node_names = set(graph.get_graph().nodes)
    assert {
        "segment_contract",
        "scan_rules",
        "retrieve_knowledge",
        "retrieve_memory",
        "structured_llm_analysis",
        "verify_evidence",
        "extract_obligations",
        "assess_quality",
        "finalize_report",
    }.issubset(node_names)


def test_fake_reviewer_context_and_evidence_guard() -> None:
    knowledge = RecordingProvider(ContextSource.KNOWLEDGE)
    memory = RecordingProvider(ContextSource.MEMORY)
    reviewer = EvidenceCheckingFakeReviewer()
    workflow = ContractReviewWorkflow(
        ReviewDependencies(
            reviewer=reviewer,
            knowledge_provider=knowledge,
            memory_provider=memory,
        )
    )

    report = workflow.review(CONTRACT_TEXT, contract_id="contract-123")

    finding_ids = {finding.finding_id for finding in report.findings}
    assert "llm-valid" in finding_ids
    assert "llm-hallucinated" not in finding_ids
    assert reviewer.received_context
    assert knowledge.calls == 1
    assert memory.calls == 1
    assert {item.context_id for item in report.contexts} == {
        "knowledge-1",
        "memory-1",
    }
    assert report.analysis_notes == ["Reviewed renewal and payment clauses."]
    valid_finding = next(item for item in report.findings if item.finding_id == "llm-valid")
    assert valid_finding.context_refs == ["knowledge-1"]
    assert report.quality.llm_finding_count == 2
    assert report.quality.rejected_finding_count == 1
    assert report.quality.llm_review_performed is True
    assert report.quality.passed is False

    for finding in report.findings:
        for evidence in finding.evidence:
            assert evidence.verified
            assert CONTRACT_TEXT[evidence.start_offset : evidence.end_offset] == evidence.quote
    assert any(item.obligor == "甲方" for item in report.obligations)
    assert all(item.evidence.verified for item in report.obligations)


def test_workflow_passes_tenant_scope_to_scoped_provider() -> None:
    captured: dict[str, str | None] = {}

    class ScopedProvider:
        def retrieve(
            self,
            *,
            contract_id: str,
            clauses: Sequence[Clause],
            org_id: str | None = None,
            session_id: str | None = None,
        ) -> Sequence[ContextSnippet]:
            captured.update(
                contract_id=contract_id,
                org_id=org_id,
                session_id=session_id,
            )
            return ()

    workflow = ContractReviewWorkflow(ReviewDependencies(knowledge_provider=ScopedProvider()))

    workflow.review(
        "合同自动续期。",
        contract_id="scoped-contract",
        org_id="org-a",
        session_id="session-a",
    )

    assert captured == {
        "contract_id": "scoped-contract",
        "org_id": "org-a",
        "session_id": "session-a",
    }


def test_offline_workflow_runs_rules_without_openai() -> None:
    workflow = ContractReviewWorkflow(ReviewDependencies(reviewer=OfflineContractReviewer()))
    report = workflow.review("期限届满后自动续期。", contract_id="offline")

    assert report.findings
    assert report.quality.llm_review_performed is False
    assert any("rule-based only" in warning for warning in report.quality.warnings)
    assert all(finding.source == FindingSource.RULE for finding in report.findings)


def test_segment_contract_preserves_offsets() -> None:
    clauses = segment_contract(CONTRACT_TEXT)
    assert len(clauses) == 2
    for clause in clauses:
        assert CONTRACT_TEXT[clause.start_offset : clause.end_offset] == clause.text


def test_finding_model_rejects_conclusion_without_evidence() -> None:
    with pytest.raises(ValidationError):
        RiskFinding(
            finding_id="unsupported",
            title="无证据结论",
            description="不允许进入系统。",
            category="other",
            risk_level=RiskLevel.HIGH,
            source=FindingSource.LLM,
            evidence=[],
        )


def test_openai_configuration_resolution_is_injected() -> None:
    assert resolve_openai_model(environ={}) == DEFAULT_OPENAI_MODEL
    assert (
        resolve_openai_model(
            settings={"openai_model": "settings-model"},
            environ={"OPENAI_MODEL": "environment-model"},
        )
        == "settings-model"
    )
    assert (
        resolve_openai_base_url(
            settings={"openai_base_url": "https://gateway.example/v1/"},
            environ={},
        )
        == "https://gateway.example/v1"
    )


def test_openai_reviewer_uses_responses_api_without_live_request(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def with_structured_output(self, schema: object, **kwargs: object) -> object:
            captured["schema"] = schema
            captured["structured_options"] = kwargs
            return self

    monkeypatch.setattr("langchain_openai.ChatOpenAI", FakeChatOpenAI)
    reviewer = OpenAIContractReviewer(
        settings={
            "openai_model": "settings-model",
            "openai_base_url": "https://gateway.example/v1",
        },
        environ={},
    )

    assert reviewer.model_name == "settings-model"
    assert captured["model"] == "settings-model"
    assert captured["base_url"] == "https://gateway.example/v1"
    assert captured["use_responses_api"] is True
    assert "temperature" not in captured
    assert captured["schema"] is LLMStructuredAnalysis
