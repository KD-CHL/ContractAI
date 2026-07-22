from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from contract_guard.domain import Clause, ContextSource
from contract_guard.services.memory import RepositoryMemoryContextProvider
from contract_guard.services.storage import (
    MemoryLayer,
    SQLiteReviewRepository,
    StoredMemory,
)


def _clause(text: str, *, heading: str | None = None) -> Clause:
    return Clause(
        clause_id="clause-0001",
        ordinal=1,
        heading=heading,
        text=text,
        start_offset=0,
        end_offset=len(text),
    )


def _store_all_layers(
    repository: SQLiteReviewRepository,
    *,
    org_id: str,
    session_id: str,
) -> None:
    repository.upsert_memory(
        org_id=org_id,
        session_id=None,
        layer=MemoryLayer.GLOBAL,
        key="payment-policy",
        content="付款期限一般不超过三十日",
        metadata={"owner": "legal", "layer": "forged", "score": 999},
    )
    repository.upsert_memory(
        org_id=org_id,
        session_id=session_id,
        layer=MemoryLayer.PROFILE,
        key="payment-preference",
        content={"preference": "付款必须以收到合格发票为起算点"},
    )
    repository.upsert_memory(
        org_id=org_id,
        session_id=session_id,
        layer=MemoryLayer.EPISODIC,
        key="late-payment-review",
        content="上次审阅要求提示逾期付款违约金",
    )
    repository.upsert_memory(
        org_id=org_id,
        session_id=session_id,
        layer=MemoryLayer.SHORT_TERM,
        key="current-negotiation",
        content="本轮谈判重点是付款和发票条件",
    )


def test_retrieves_relevant_context_from_all_four_layers() -> None:
    repository = SQLiteReviewRepository(":memory:")
    _store_all_layers(repository, org_id="org-a", session_id="session-a")
    provider = RepositoryMemoryContextProvider(repository)

    contexts = provider.retrieve(
        contract_id="contract-1",
        clauses=[_clause("甲方应在收到合格发票后三十日内付款。")],
        org_id="org-a",
        session_id="session-a",
    )

    assert {item.metadata["layer"] for item in contexts} == {layer.value for layer in MemoryLayer}
    assert all(item.source is ContextSource.MEMORY for item in contexts)
    assert all(item.context_id.startswith("memory:") for item in contexts)
    assert all(item.citation and item.citation.startswith("memory:") for item in contexts)
    assert any("preference" in item.content for item in contexts)
    assert any(item.metadata.get("owner") == "legal" for item in contexts)
    global_context = next(
        item for item in contexts if item.metadata["memory_key"] == "payment-policy"
    )
    assert global_context.metadata["layer"] == MemoryLayer.GLOBAL.value
    assert global_context.metadata["score"] != 999


def test_lexical_relevance_controls_order_and_limit() -> None:
    repository = SQLiteReviewRepository(":memory:")
    repository.upsert_memory(
        org_id="org",
        session_id=None,
        layer=MemoryLayer.GLOBAL,
        key="high-match",
        content="发票付款逾期违约金",
    )
    repository.upsert_memory(
        org_id="org",
        session_id=None,
        layer=MemoryLayer.GLOBAL,
        key="low-match",
        content="付款流程",
    )
    repository.upsert_memory(
        org_id="org",
        session_id=None,
        layer=MemoryLayer.GLOBAL,
        key="unrelated",
        content="办公场所门禁规则",
    )
    provider = RepositoryMemoryContextProvider(repository, max_contexts=1)

    contexts = provider.retrieve(
        contract_id="contract",
        clauses=[_clause("发票付款逾期违约金")],
        org_id="org",
    )

    assert len(contexts) == 1
    assert contexts[0].metadata["memory_key"] == "high-match"
    assert contexts[0].metadata["score"] > 0


def test_exact_organization_and_session_isolation() -> None:
    repository = SQLiteReviewRepository(":memory:")
    _store_all_layers(repository, org_id="org-a", session_id="session-a")
    _store_all_layers(repository, org_id="org-a", session_id="session-b")
    _store_all_layers(repository, org_id="org-b", session_id="session-a")
    provider = RepositoryMemoryContextProvider(repository)

    contexts = provider.retrieve(
        contract_id="contract",
        clauses=[_clause("付款发票逾期条件")],
        org_id="org-a",
        session_id="session-a",
    )

    # The one organization-global item plus exactly three session-a items.
    assert len(contexts) == 4
    assert {item.metadata["layer"] for item in contexts} == {layer.value for layer in MemoryLayer}

    global_only = provider.retrieve(
        contract_id="contract",
        clauses=[_clause("付款发票逾期条件")],
        org_id="org-a",
        session_id=None,
    )
    assert len(global_only) == 1
    assert global_only[0].metadata["layer"] == MemoryLayer.GLOBAL.value


class _UnexpectedRowsRepository:
    """Repository double that intentionally violates its requested scope."""

    def __init__(self, rows: Sequence[StoredMemory]) -> None:
        self.rows = rows
        self.calls = 0

    def list_memories(
        self,
        *,
        org_id: str,
        session_id: str | None,
        layer: MemoryLayer | str | None = None,
        limit: int = 100,
    ) -> Sequence[StoredMemory]:
        del org_id, session_id, layer, limit
        self.calls += 1
        return self.rows


def _memory(
    identifier: str,
    *,
    org_id: str,
    session_id: str | None,
    layer: MemoryLayer,
) -> StoredMemory:
    now = datetime.now(UTC)
    return StoredMemory(
        id=identifier,
        org_id=org_id,
        session_id=session_id,
        layer=layer,
        key=identifier,
        content="付款发票条件",
        metadata={},
        created_at=now,
        updated_at=now,
    )


def test_provider_defensively_filters_repository_scope_violations() -> None:
    rows = [
        _memory(
            "allowed-global",
            org_id="org-a",
            session_id=None,
            layer=MemoryLayer.GLOBAL,
        ),
        _memory(
            "allowed-profile",
            org_id="org-a",
            session_id="session-a",
            layer=MemoryLayer.PROFILE,
        ),
        _memory(
            "other-org",
            org_id="org-b",
            session_id="session-a",
            layer=MemoryLayer.PROFILE,
        ),
        _memory(
            "other-session",
            org_id="org-a",
            session_id="session-b",
            layer=MemoryLayer.PROFILE,
        ),
    ]
    provider = RepositoryMemoryContextProvider(_UnexpectedRowsRepository(rows))

    contexts = provider.retrieve(
        contract_id="contract",
        clauses=[_clause("付款发票条件")],
        org_id="org-a",
        session_id="session-a",
    )

    assert {item.metadata["memory_key"] for item in contexts} == {
        "allowed-global",
        "allowed-profile",
    }


def test_missing_org_scope_fails_closed_without_querying_repository() -> None:
    repository = _UnexpectedRowsRepository([])
    provider = RepositoryMemoryContextProvider(repository)

    assert (
        provider.retrieve(
            contract_id="contract",
            clauses=[_clause("付款")],
            org_id=None,
            session_id="session-a",
        )
        == []
    )
    assert repository.calls == 0


def test_provider_configuration_is_validated() -> None:
    repository = SQLiteReviewRepository(":memory:")
    with pytest.raises(ValueError, match="max_contexts"):
        RepositoryMemoryContextProvider(repository, max_contexts=0)
    with pytest.raises(ValueError, match="per_layer_limit"):
        RepositoryMemoryContextProvider(repository, per_layer_limit=1001)
