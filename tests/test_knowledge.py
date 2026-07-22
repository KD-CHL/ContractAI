from __future__ import annotations

import httpx
import pytest

from contract_guard.agent.workflow import segment_contract
from contract_guard.services.knowledge import (
    LightRAGContextProvider,
    LightRAGRetriever,
    LocalKnowledgeContextProvider,
    LocalKnowledgeRetriever,
)


@pytest.mark.asyncio
async def test_local_retriever_prioritizes_relevant_clause() -> None:
    retriever = LocalKnowledgeRetriever(
        entries=[
            {
                "id": "payment",
                "title": "付款与验收",
                "content": "付款条件应与交付和验收节点保持一致。",
                "tags": ["付款", "验收"],
            },
            {
                "id": "confidentiality",
                "title": "保密条款",
                "content": "保密义务应明确期限和例外。",
                "tags": ["保密"],
            },
        ]
    )

    hits = await retriever.search("付款必须发生在验收完成后", limit=1)

    assert [hit.source_id for hit in hits] == ["payment"]
    assert hits[0].score > 0


@pytest.mark.asyncio
async def test_lightrag_retriever_returns_chunks_as_evidence() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/query"
        assert request.headers["x-api-key"] == "test-key"
        return httpx.Response(
            200,
            json={
                "response": "synthesized answer must not become evidence",
                "references": [
                    {
                        "reference_id": "7",
                        "file_path": "/kb/policy.md",
                        "content": ["第一条证据", "第二条证据"],
                    }
                ],
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://rag"
    ) as client:
        retriever = LightRAGRetriever("http://rag", api_key="test-key", client=client)
        hits = await retriever.search("风险", limit=5, workspace="org-a")

    assert [hit.content for hit in hits] == ["第一条证据", "第二条证据"]
    assert all("synthesized" not in hit.content for hit in hits)


def test_local_context_provider_returns_versioned_citations() -> None:
    retriever = LocalKnowledgeRetriever(
        entries=[
            {
                "id": "renewal",
                "title": "续期政策",
                "version": "2.0",
                "content": "自动续期需要明确通知窗口。",
                "tags": ["自动续期"],
            }
        ]
    )
    provider = LocalKnowledgeContextProvider(retriever=retriever)

    contexts = provider.retrieve(
        contract_id="contract-1", clauses=segment_contract("本合同自动续期十二个月。")
    )

    assert len(contexts) == 1
    assert contexts[0].context_id == "renewal"
    assert contexts[0].citation == "续期政策（2.0）"


def test_lightrag_context_uses_org_workspace_and_local_fallback(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fallback = LocalKnowledgeContextProvider(
        retriever=LocalKnowledgeRetriever(
            entries=[
                {
                    "id": "renewal",
                    "title": "续期政策",
                    "content": "自动续期需要通知窗口。",
                    "tags": ["自动续期"],
                }
            ]
        )
    )

    def unavailable(url: str, **kwargs: object) -> httpx.Response:
        captured["url"] = url
        captured.update(kwargs)
        raise httpx.ConnectError("unavailable")

    monkeypatch.setattr(httpx, "post", unavailable)
    provider = LightRAGContextProvider(
        "http://rag",
        api_key="test-key",
        fallback=fallback,
    )

    contexts = provider.retrieve(
        contract_id="user-controlled-contract-id",
        clauses=segment_contract("本合同自动续期十二个月。"),
        org_id="trusted-org",
        session_id="session-a",
    )

    assert captured["url"] == "http://rag/query"
    assert captured["headers"] == {
        "Accept": "application/json",
        "X-Workspace": "trusted-org",
        "X-API-Key": "test-key",
    }
    assert contexts[0].metadata["degraded_from"] == "lightrag"
    assert contexts[0].metadata["degraded_reason"] == "ConnectError"
