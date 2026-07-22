"""Knowledge retrieval adapters used by the contract review graph.

The local retriever keeps the demo runnable without infrastructure.  The
LightRAG adapter intentionally consumes *retrieved chunks*, not the generated
answer, so downstream findings can cite inspectable evidence.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

from contract_guard.domain import Clause, ContextSnippet, ContextSource


@dataclass(frozen=True, slots=True)
class KnowledgeHit:
    source_id: str
    title: str
    content: str
    score: float = 0.0
    source_uri: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def citation_label(self) -> str:
        suffix = f"（{self.version}）" if self.version else ""
        return f"{self.title}{suffix}"


class KnowledgeRetriever(Protocol):
    async def search(
        self, query: str, *, limit: int = 5, workspace: str | None = None
    ) -> list[KnowledgeHit]: ...


_LATIN_TOKEN = re.compile(r"[a-zA-Z0-9_\-]{2,}")
_CJK_RUN = re.compile(r"[\u3400-\u9fff]+")


def _tokens(text: str) -> set[str]:
    normalized = text.lower()
    tokens = set(_LATIN_TOKEN.findall(normalized))
    for run in _CJK_RUN.findall(normalized):
        if len(run) == 1:
            tokens.add(run)
        else:
            tokens.update(run[index : index + 2] for index in range(len(run) - 1))
    return tokens


class LocalKnowledgeRetriever:
    """Small lexical retriever for deterministic local development and tests."""

    def __init__(
        self,
        source: str | Path | None = None,
        *,
        entries: Sequence[dict[str, Any]] | None = None,
    ) -> None:
        self._source = Path(source) if source else None
        self._entries = list(entries) if entries is not None else None

    def _load(self) -> list[dict[str, Any]]:
        if self._entries is not None:
            return list(self._entries)
        if self._source is None or not self._source.exists():
            return []
        payload = json.loads(self._source.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("entries", [])
        if not isinstance(payload, list):
            raise ValueError("knowledge base must be a JSON list or contain an 'entries' list")
        return [item for item in payload if isinstance(item, dict)]

    def search_sync(
        self, query: str, *, limit: int = 5, workspace: str | None = None
    ) -> list[KnowledgeHit]:
        del workspace  # Local JSON data is shared, read-only demonstration content.
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        ranked: list[KnowledgeHit] = []
        for index, item in enumerate(self._load()):
            content = str(item.get("content", "")).strip()
            title = str(item.get("title", "未命名知识条目")).strip()
            tags = " ".join(str(tag) for tag in item.get("tags", []))
            document_tokens = _tokens(f"{title} {tags} {content}")
            overlap = query_tokens.intersection(document_tokens)
            if not overlap:
                continue
            # A bounded BM25-like signal is enough for a small curated knowledge set.
            coverage = len(overlap) / len(query_tokens)
            specificity = len(overlap) / math.sqrt(max(1, len(document_tokens)))
            score = round(0.8 * coverage + 0.2 * specificity, 6)
            ranked.append(
                KnowledgeHit(
                    source_id=str(item.get("id") or f"local-{index + 1}"),
                    title=title,
                    content=content,
                    score=score,
                    source_uri=item.get("source_uri"),
                    version=item.get("version"),
                    metadata={
                        "retriever": "local",
                        "category": item.get("category"),
                        "demo_only": bool(item.get("demo_only", True)),
                        "knowledge_id": item.get("knowledge_id") or item.get("id"),
                        "jurisdiction": item.get("jurisdiction"),
                        "effective_from": item.get("effective_from"),
                        "provenance": item.get("provenance"),
                    },
                )
            )
        ranked.sort(key=lambda hit: (-hit.score, hit.source_id))
        return ranked[: max(0, limit)]

    async def search(
        self, query: str, *, limit: int = 5, workspace: str | None = None
    ) -> list[KnowledgeHit]:
        return self.search_sync(query, limit=limit, workspace=workspace)


class LightRAGRetriever:
    """Retrieve citation-ready chunks from a LightRAG Server REST API."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        mode: str = "mix",
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._mode = mode
        self._timeout = timeout
        self._client = client

    async def search(
        self, query: str, *, limit: int = 5, workspace: str | None = None
    ) -> list[KnowledgeHit]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        if workspace:
            headers["X-Workspace"] = workspace

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            response = await client.post(
                f"{self._base_url}/query",
                headers=headers,
                json={
                    "query": query,
                    "mode": self._mode,
                    "include_references": True,
                    "include_chunk_content": True,
                    "enable_rerank": True,
                },
            )
            response.raise_for_status()
            payload = response.json()
        finally:
            if owns_client:
                await client.aclose()

        hits: list[KnowledgeHit] = []
        for reference in payload.get("references") or []:
            reference_id = str(reference.get("reference_id") or "unknown")
            file_path = str(reference.get("file_path") or "LightRAG 知识库")
            chunks = reference.get("content") or []
            if isinstance(chunks, str):
                chunks = [chunks]
            for chunk_index, chunk in enumerate(chunks):
                text = str(chunk).strip()
                if not text:
                    continue
                hits.append(
                    KnowledgeHit(
                        source_id=f"lightrag:{reference_id}:{chunk_index + 1}",
                        title=Path(file_path).name or file_path,
                        content=text,
                        score=max(0.0, 1.0 - len(hits) * 0.01),
                        source_uri=file_path,
                        metadata={"retriever": "lightrag", "workspace": workspace},
                    )
                )
                if len(hits) >= limit:
                    return hits
        return hits


class FallbackKnowledgeRetriever:
    """Use a production retriever when available, otherwise deterministic local data."""

    def __init__(self, primary: KnowledgeRetriever | None, fallback: KnowledgeRetriever) -> None:
        self._primary = primary
        self._fallback = fallback

    async def search(
        self, query: str, *, limit: int = 5, workspace: str | None = None
    ) -> list[KnowledgeHit]:
        if self._primary is not None:
            try:
                primary_hits = await self._primary.search(query, limit=limit, workspace=workspace)
                if primary_hits:
                    return primary_hits
            except (httpx.HTTPError, ValueError, TypeError):
                # The graph remains usable during a knowledge-service outage.  The
                # caller can surface the local source metadata in its audit trace.
                pass
        return await self._fallback.search(query, limit=limit, workspace=workspace)


class LocalKnowledgeContextProvider:
    """Bridge the local retriever into ContractGuard's synchronous graph boundary."""

    def __init__(
        self,
        source: str | Path | None = None,
        *,
        retriever: LocalKnowledgeRetriever | None = None,
        max_contexts: int = 8,
    ) -> None:
        if max_contexts <= 0:
            raise ValueError("max_contexts must be greater than zero")
        self._retriever = retriever or LocalKnowledgeRetriever(source)
        self._max_contexts = max_contexts

    def retrieve(
        self,
        *,
        contract_id: str,
        clauses: Sequence[Clause],
        org_id: str | None = None,
        session_id: str | None = None,
    ) -> list[ContextSnippet]:
        del contract_id, org_id, session_id
        hits_by_id: dict[str, KnowledgeHit] = {}
        for clause in clauses:
            for hit in self._retriever.search_sync(clause.text, limit=3):
                current = hits_by_id.get(hit.source_id)
                if current is None or hit.score > current.score:
                    hits_by_id[hit.source_id] = hit
        ranked = sorted(hits_by_id.values(), key=lambda hit: (-hit.score, hit.source_id))[
            : self._max_contexts
        ]
        return [
            ContextSnippet(
                context_id=hit.source_id,
                source=ContextSource.KNOWLEDGE,
                content=hit.content,
                citation=hit.citation_label,
                metadata={
                    **hit.metadata,
                    "source_uri": hit.source_uri,
                    "version": hit.version,
                    "score": hit.score,
                },
            )
            for hit in ranked
        ]


class LightRAGContextProvider:
    """Synchronous LightRAG bridge intended for graph execution in a worker thread."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        mode: str = "mix",
        timeout: float = 30.0,
        fallback: LocalKnowledgeContextProvider | None = None,
        max_contexts: int = 8,
        max_query_chars: int = 40_000,
    ) -> None:
        if max_contexts <= 0:
            raise ValueError("max_contexts must be greater than zero")
        if max_query_chars <= 0:
            raise ValueError("max_query_chars must be greater than zero")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._mode = mode
        self._timeout = timeout
        self._fallback = fallback
        self._max_contexts = max_contexts
        self._max_query_chars = max_query_chars

    def retrieve(
        self,
        *,
        contract_id: str,
        clauses: Sequence[Clause],
        org_id: str | None = None,
        session_id: str | None = None,
    ) -> list[ContextSnippet]:
        query = "\n\n".join(clause.text for clause in clauses)[: self._max_query_chars]
        headers = {"Accept": "application/json"}
        if org_id:
            headers["X-Workspace"] = org_id
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        fallback_reason: str | None = None
        try:
            response = httpx.post(
                f"{self._base_url}/query",
                headers=headers,
                json={
                    "query": query,
                    "mode": self._mode,
                    "include_references": True,
                    "include_chunk_content": True,
                    "enable_rerank": True,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("LightRAG response must be a JSON object")
            contexts = _lightrag_references_to_contexts(
                payload.get("references") or [], limit=self._max_contexts
            )
            if contexts:
                return contexts
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            fallback_reason = type(exc).__name__
        if self._fallback is not None:
            fallback_contexts = self._fallback.retrieve(
                contract_id=contract_id,
                clauses=clauses,
                org_id=org_id,
                session_id=session_id,
            )
            if fallback_reason:
                return [
                    context.model_copy(
                        update={
                            "metadata": {
                                **context.metadata,
                                "degraded_from": "lightrag",
                                "degraded_reason": fallback_reason,
                            }
                        }
                    )
                    for context in fallback_contexts
                ]
            return fallback_contexts
        return []


def _lightrag_references_to_contexts(
    references: Sequence[dict[str, Any]], *, limit: int
) -> list[ContextSnippet]:
    contexts: list[ContextSnippet] = []
    for reference in references:
        reference_id = str(reference.get("reference_id") or "unknown")
        file_path = str(reference.get("file_path") or "LightRAG 知识库")
        chunks = reference.get("content") or []
        if isinstance(chunks, str):
            chunks = [chunks]
        for index, chunk in enumerate(chunks):
            content = str(chunk).strip()
            if not content:
                continue
            contexts.append(
                ContextSnippet(
                    context_id=f"lightrag:{reference_id}:{index + 1}",
                    source=ContextSource.KNOWLEDGE,
                    content=content,
                    citation=Path(file_path).name or file_path,
                    metadata={
                        "retriever": "lightrag",
                        "source_uri": file_path,
                        "reference_id": reference_id,
                    },
                )
            )
            if len(contexts) >= limit:
                return contexts
    return contexts


__all__ = [
    "FallbackKnowledgeRetriever",
    "KnowledgeHit",
    "KnowledgeRetriever",
    "LightRAGContextProvider",
    "LightRAGRetriever",
    "LocalKnowledgeContextProvider",
    "LocalKnowledgeRetriever",
]
