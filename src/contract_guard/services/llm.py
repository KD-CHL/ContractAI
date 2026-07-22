"""Structured contract reviewers, including the OpenAI implementation."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from contract_guard.domain import (
    Clause,
    ContextSnippet,
    Evidence,
    FindingSource,
    RiskFinding,
    RiskLevel,
    StructuredAnalysis,
)

DEFAULT_OPENAI_MODEL = "gpt-5.6-luna"


class _LLMOutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LLMEvidence(_LLMOutputModel):
    """Strict draft quote; verification remains an application responsibility."""

    clause_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)


class LLMRiskFinding(_LLMOutputModel):
    """Strict LLM draft with every JSON-schema property required."""

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: str = Field(min_length=1)
    risk_level: RiskLevel
    context_refs: list[str]
    evidence: list[LLMEvidence] = Field(min_length=1)
    recommendation: str | None
    confidence: float = Field(ge=0.0, le=1.0)


class LLMStructuredAnalysis(_LLMOutputModel):
    """OpenAI structured-output schema, separate from trusted domain state."""

    findings: list[LLMRiskFinding]
    analysis_notes: list[str]


@runtime_checkable
class ContractReviewer(Protocol):
    """Dependency-injection boundary used by the review graph."""

    def analyze_clauses(
        self,
        clauses: Sequence[Clause],
        *,
        knowledge_context: Sequence[ContextSnippet] = (),
        memory_context: Sequence[ContextSnippet] = (),
    ) -> StructuredAnalysis:
        """Return structured candidates; the graph verifies all evidence."""


class OfflineContractReviewer:
    """Offline reviewer that deliberately adds no generative conclusions."""

    is_offline = True

    def analyze_clauses(
        self,
        clauses: Sequence[Clause],
        *,
        knowledge_context: Sequence[ContextSnippet] = (),
        memory_context: Sequence[ContextSnippet] = (),
    ) -> StructuredAnalysis:
        del clauses, knowledge_context, memory_context
        return StructuredAnalysis(
            analysis_notes=["LLM review was not requested; deterministic rules still ran."]
        )


class StaticContractReviewer:
    """Small reusable fake for offline integration tests and demos."""

    is_offline = False

    def __init__(self, findings: Sequence[RiskFinding]) -> None:
        self._findings = list(findings)

    def analyze_clauses(
        self,
        clauses: Sequence[Clause],
        *,
        knowledge_context: Sequence[ContextSnippet] = (),
        memory_context: Sequence[ContextSnippet] = (),
    ) -> StructuredAnalysis:
        del clauses, knowledge_context, memory_context
        return StructuredAnalysis(findings=self._findings)


class OpenAIContractReviewer:
    """LangChain ``ChatOpenAI`` reviewer using strict structured output.

    Model resolution order is explicit constructor argument, injected settings,
    injected/current process environment, then ``DEFAULT_OPENAI_MODEL``.  This
    module never reads dotenv files; secret loading remains an application-level
    concern handled by ``ChatOpenAI``.
    """

    is_offline = False

    def __init__(
        self,
        *,
        model: str | None = None,
        settings: object | Mapping[str, Any] | None = None,
        environ: Mapping[str, str] | None = None,
        base_url: str | None = None,
        chat_model: Any | None = None,
        temperature: float | None = None,
        use_responses_api: bool = True,
    ) -> None:
        self.model_name = resolve_openai_model(
            model=model,
            settings=settings,
            environ=environ,
        )
        self.base_url = resolve_openai_base_url(
            base_url=base_url,
            settings=settings,
            environ=environ,
        )
        if chat_model is None:
            try:
                from langchain_openai import ChatOpenAI
            except ImportError as exc:  # pragma: no cover - installation concern
                raise RuntimeError(
                    "langchain-openai is required for OpenAIContractReviewer"
                ) from exc
            chat_options: dict[str, Any] = {
                "model": self.model_name,
                "base_url": self.base_url,
                "use_responses_api": use_responses_api,
            }
            timeout = _read_setting(settings, "openai_timeout_seconds")
            if isinstance(timeout, int | float) and timeout > 0:
                chat_options["timeout"] = float(timeout)
            max_retries = _read_setting(settings, "openai_max_retries")
            if isinstance(max_retries, int) and max_retries >= 0:
                chat_options["max_retries"] = max_retries
            if temperature is not None:
                chat_options["temperature"] = temperature
            chat_model = ChatOpenAI(**chat_options)
        self._chat_model = chat_model
        self._structured_model = chat_model.with_structured_output(
            LLMStructuredAnalysis,
            method="json_schema",
            strict=True,
        )

    def analyze_clauses(
        self,
        clauses: Sequence[Clause],
        *,
        knowledge_context: Sequence[ContextSnippet] = (),
        memory_context: Sequence[ContextSnippet] = (),
    ) -> StructuredAnalysis:
        if not clauses:
            return StructuredAnalysis()

        payload = {
            "clauses": [clause.model_dump(mode="json") for clause in clauses],
            "knowledge_context": [item.model_dump(mode="json") for item in knowledge_context],
            "memory_context": [item.model_dump(mode="json") for item in memory_context],
        }
        messages = [
            ("system", _SYSTEM_PROMPT),
            (
                "human",
                "Review the following JSON payload. Return only the structured "
                "analysis requested by the response schema.\n"
                + json.dumps(payload, ensure_ascii=False),
            ),
        ]
        result = self._structured_model.invoke(messages)
        if not isinstance(result, LLMStructuredAnalysis):
            result = LLMStructuredAnalysis.model_validate(result)
        return _to_domain_analysis(result)


def resolve_openai_model(
    *,
    model: str | None = None,
    settings: object | Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve the ChatOpenAI model without loading or inspecting dotenv files."""

    if model and model.strip():
        return model.strip()

    for key in (
        "openai_model",
        "llm_model",
        "model_name",
        "OPENAI_MODEL",
        "CONTRACT_GUARD_OPENAI_MODEL",
    ):
        value = _read_setting(settings, key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    environment = os.environ if environ is None else environ
    for key in ("CONTRACT_GUARD_OPENAI_MODEL", "OPENAI_MODEL"):
        value = environment.get(key)
        if value and value.strip():
            return value.strip()
    return DEFAULT_OPENAI_MODEL


def resolve_openai_base_url(
    *,
    base_url: str | None = None,
    settings: object | Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve an optional OpenAI-compatible endpoint from injected config."""

    if base_url and base_url.strip():
        return base_url.strip().rstrip("/")

    for key in (
        "openai_base_url",
        "base_url",
        "OPENAI_BASE_URL",
        "CONTRACT_GUARD_OPENAI_BASE_URL",
    ):
        value = _read_setting(settings, key)
        if isinstance(value, str) and value.strip():
            return value.strip().rstrip("/")

    environment = os.environ if environ is None else environ
    for key in ("CONTRACT_GUARD_OPENAI_BASE_URL", "OPENAI_BASE_URL"):
        value = environment.get(key)
        if value and value.strip():
            return value.strip().rstrip("/")
    return None


def _read_setting(
    settings: object | Mapping[str, Any] | None,
    key: str,
) -> Any:
    if settings is None:
        return None
    if isinstance(settings, Mapping):
        return settings.get(key)
    return getattr(settings, key, None)


def _to_domain_analysis(value: LLMStructuredAnalysis) -> StructuredAnalysis:
    findings: list[RiskFinding] = []
    for draft in value.findings:
        evidence = [
            Evidence(
                clause_id=item.clause_id,
                quote=item.quote,
                start_offset=item.start_offset,
                end_offset=item.end_offset,
                verified=False,
            )
            for item in draft.evidence
        ]
        identity_parts = [
            draft.category,
            draft.title,
            *(f"{item.clause_id}:{item.quote}" for item in draft.evidence),
        ]
        finding_id = hashlib.sha256("\x1f".join(identity_parts).encode("utf-8")).hexdigest()[:20]
        findings.append(
            RiskFinding(
                finding_id=f"llm-{finding_id}",
                title=draft.title,
                description=draft.description,
                category=draft.category,
                risk_level=draft.risk_level,
                source=FindingSource.LLM,
                context_refs=draft.context_refs,
                evidence=evidence,
                recommendation=draft.recommendation,
                confidence=draft.confidence,
            )
        )
    return StructuredAnalysis(
        findings=findings,
        analysis_notes=value.analysis_notes,
    )


_SYSTEM_PROMPT = """\
You are a cautious contract issue-spotting assistant, not a lawyer and not a
source of legal conclusions. Identify only risks directly supported by the
provided contract clauses.

Mandatory evidence rules:
1. Every finding must include at least one verbatim, exact quote from a supplied
   clause and must name that clause_id.
2. Never invent, paraphrase, or repair a quote. If no exact quote supports a
   candidate finding, omit the finding.
3. start_offset/end_offset should locate that quote in the original contract;
   the application will verify it independently.
4. Retrieved knowledge and memory are context only. They can guide issue
   spotting but cannot replace contract evidence or prove facts about this
   contract. Put only context IDs actually used in context_refs, otherwise [].
5. Describe uncertainty as a review question. Do not state that a term is legal,
   illegal, enforceable, or unenforceable.
6. Recommendations must be framed as matters to clarify, compare, or discuss
   with qualified counsel.
"""


__all__ = [
    "ContractReviewer",
    "DEFAULT_OPENAI_MODEL",
    "LLMEvidence",
    "LLMRiskFinding",
    "LLMStructuredAnalysis",
    "OfflineContractReviewer",
    "OpenAIContractReviewer",
    "StaticContractReviewer",
    "resolve_openai_base_url",
    "resolve_openai_model",
]
