"""Tenant-safe retrieval of prior-review memory for the agent graph.

The storage layer is the primary isolation boundary.  This adapter deliberately
checks the scope of every returned row again before it becomes model context so
that an incorrectly implemented repository cannot silently leak another
organization's or session's memory into a review.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from contract_guard.domain import Clause, ContextSnippet, ContextSource
from contract_guard.services.storage import MemoryLayer, StoredMemory


class MemoryRepository(Protocol):
    """Minimal repository surface needed by the context provider."""

    def list_memories(
        self,
        *,
        org_id: str,
        session_id: str | None,
        layer: MemoryLayer | str | None = None,
        limit: int = 100,
    ) -> Sequence[StoredMemory]: ...


_LATIN_TOKEN = re.compile(r"[a-zA-Z0-9_\-]{2,}")
_CJK_RUN = re.compile(r"[\u3400-\u9fff]+")


def _tokens(text: str) -> set[str]:
    """Return compact Latin tokens and CJK bigrams for lexical matching."""

    normalized = text.lower()
    tokens = set(_LATIN_TOKEN.findall(normalized))
    for run in _CJK_RUN.findall(normalized):
        if len(run) == 1:
            tokens.add(run)
        else:
            tokens.update(run[index : index + 2] for index in range(len(run) - 1))
    return tokens


def _render_content(value: Any) -> str:
    """Render JSON-compatible memory as stable, readable model context."""

    if isinstance(value, str):
        return value.strip()
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        # Repository implementations are expected to return JSON-compatible
        # values, but a conservative string representation keeps the provider
        # useful for protocol-compatible stores without weakening isolation.
        return str(value).strip()


def _lexical_score(query_tokens: set[str], document_tokens: set[str]) -> float:
    if not query_tokens or not document_tokens:
        return 0.0
    overlap = len(query_tokens.intersection(document_tokens))
    if not overlap:
        return 0.0
    # Cosine-like token overlap rewards specific matches without letting a long
    # contract or a long memory dominate solely because it contains more words.
    return overlap / math.sqrt(len(query_tokens) * len(document_tokens))


@dataclass(frozen=True, slots=True)
class _RankedMemory:
    memory: StoredMemory
    content: str
    score: float


class RepositoryMemoryContextProvider:
    """Retrieve relevant global, profile, episodic, and short-term memory.

    ``org_id`` is mandatory for any memory access.  When ``session_id`` is not
    supplied, only organization-global memory is eligible.  The three other
    layers require an exact session match.
    """

    def __init__(
        self,
        repository: MemoryRepository,
        *,
        max_contexts: int = 8,
        per_layer_limit: int = 100,
    ) -> None:
        if max_contexts <= 0:
            raise ValueError("max_contexts must be greater than zero")
        if not 1 <= per_layer_limit <= 1000:
            raise ValueError("per_layer_limit must be between 1 and 1000")
        self._repository = repository
        self._max_contexts = max_contexts
        self._per_layer_limit = per_layer_limit

    def retrieve(
        self,
        *,
        contract_id: str,
        clauses: Sequence[Clause],
        org_id: str | None = None,
        session_id: str | None = None,
    ) -> list[ContextSnippet]:
        """Return relevant memory snippets within the exact requested scope."""

        normalized_org = org_id.strip() if isinstance(org_id, str) else ""
        if not normalized_org:
            # Missing tenant scope must fail closed: never query a shared or
            # implicit namespace on behalf of an unscoped review.
            return []

        normalized_session = (
            session_id.strip() if isinstance(session_id, str) and session_id.strip() else None
        )
        query_parts = [contract_id]
        for clause in clauses:
            if clause.heading:
                query_parts.append(clause.heading)
            query_parts.append(clause.text)
        query_tokens = _tokens("\n".join(query_parts))
        if not query_tokens:
            return []

        ranked: list[_RankedMemory] = []
        for layer in MemoryLayer:
            if layer is not MemoryLayer.GLOBAL and normalized_session is None:
                continue
            requested_session = None if layer is MemoryLayer.GLOBAL else normalized_session
            memories = self._repository.list_memories(
                org_id=normalized_org,
                session_id=requested_session,
                layer=layer,
                limit=self._per_layer_limit,
            )
            for memory in memories:
                if not self._is_in_scope(
                    memory,
                    org_id=normalized_org,
                    session_id=normalized_session,
                    requested_layer=layer,
                ):
                    continue
                content = _render_content(memory.content)
                if not content:
                    continue
                score = _lexical_score(
                    query_tokens,
                    _tokens(f"{memory.key}\n{content}"),
                )
                if score <= 0:
                    continue
                ranked.append(_RankedMemory(memory=memory, content=content, score=score))

        ranked.sort(
            key=lambda item: (
                -item.score,
                -item.memory.updated_at.timestamp(),
                item.memory.layer.value,
                item.memory.key,
                item.memory.id,
            )
        )
        return [self._to_context(item) for item in ranked[: self._max_contexts]]

    @staticmethod
    def _is_in_scope(
        memory: StoredMemory,
        *,
        org_id: str,
        session_id: str | None,
        requested_layer: MemoryLayer,
    ) -> bool:
        if memory.org_id != org_id or memory.layer is not requested_layer:
            return False
        if requested_layer is MemoryLayer.GLOBAL:
            return memory.session_id is None or memory.session_id == ""
        return session_id is not None and memory.session_id == session_id

    @staticmethod
    def _to_context(item: _RankedMemory) -> ContextSnippet:
        memory = item.memory
        return ContextSnippet(
            context_id=f"memory:{memory.layer.value}:{memory.id}",
            source=ContextSource.MEMORY,
            content=item.content,
            citation=f"memory:{memory.layer.value}:{memory.key}",
            metadata={
                **memory.metadata,
                "layer": memory.layer.value,
                "memory_key": memory.key,
                "score": round(item.score, 6),
                "updated_at": memory.updated_at.isoformat(),
            },
        )


__all__ = ["MemoryRepository", "RepositoryMemoryContextProvider"]
