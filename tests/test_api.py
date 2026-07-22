from typing import Any

import pytest
from fastapi.testclient import TestClient

from contract_guard.config import Settings
from contract_guard.main import create_app
from contract_guard.services.events import LocalEventBus
from contract_guard.services.storage import MemoryLayer


class FakeWorkflow:
    def __init__(self) -> None:
        self.calls = 0

    async def areview(self, text: str, contract_id: str | None = None) -> dict[str, Any]:
        self.calls += 1
        return {
            "report_id": f"report-{self.calls}",
            "contract_id": contract_id or "generated-contract-id",
            "findings": [],
            "obligations": [
                {
                    "obligation_id": "obligation-1",
                    "obligor": "甲方",
                    "action": "付款",
                    "evidence": {"quote": text},
                }
            ],
        }


@pytest.fixture
def app_client(tmp_path: Any) -> tuple[TestClient, FakeWorkflow, list[str]]:
    workflow = FakeWorkflow()
    events: list[str] = []
    bus = LocalEventBus()
    bus.subscribe("*", lambda event: events.append(event.name))
    settings = Settings(
        sqlite_path=str(tmp_path / "reviews.db"),
        auth_required=False,
        legacy_tenant_headers_enabled=True,
    )
    app = create_app(settings=settings, workflow=workflow, event_bus=bus)
    with TestClient(app) as client:
        yield client, workflow, events


def test_health(app_client: tuple[TestClient, FakeWorkflow, list[str]]) -> None:
    client, _, _ = app_client

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["storage"] == "ok"
    assert response.json()["mode"] == "offline"
    assert response.json()["ai_enabled"] is False
    assert response.json()["api_prefix"] == "/api/v1"
    assert response.json()["max_upload_bytes"] == 20 * 1024 * 1024


def test_nontechnical_web_ui_is_served(
    app_client: tuple[TestClient, FakeWorkflow, list[str]],
) -> None:
    client, _, _ = app_client

    page = client.get("/")

    assert page.status_code == 200
    assert "ContractGuard" in page.text
    assert "default-src 'self'" in page.headers["content-security-policy"]


def test_health_exposes_custom_api_prefix_for_web_ui(tmp_path: Any) -> None:
    app = create_app(
        settings=Settings(
            api_prefix="/contract-api",
            max_upload_bytes=4096,
            sqlite_path=str(tmp_path / "custom-prefix.db"),
            auth_required=False,
            legacy_tenant_headers_enabled=True,
        ),
        workflow=FakeWorkflow(),
    )

    with TestClient(app) as client:
        health = client.get("/health")
        reviewed = client.post(
            "/contract-api/reviews/text",
            json={"text": "甲方应付款。"},
        )

    assert health.json()["api_prefix"] == "/contract-api"
    assert health.json()["max_upload_bytes"] == 4096
    assert reviewed.status_code == 201


def test_text_review_get_cache_feedback_and_obligations(
    app_client: tuple[TestClient, FakeWorkflow, list[str]],
) -> None:
    client, workflow, events = app_client
    headers = {"X-Org-ID": "org-a", "X-Session-ID": "session-a"}
    request = {
        "text": "甲方应在三十日内付款。",
        "contract_id": "contract-1",
        "filename": "合同.md",
        "metadata": {"source": "test"},
    }

    first = client.post("/api/v1/reviews/text", json=request, headers=headers)
    second = client.post("/api/v1/reviews/text", json=request, headers=headers)

    assert first.status_code == 201
    assert first.json()["status"] == "completed"
    assert first.json()["document"]["media_type"] == "text/markdown"
    assert first.json()["cached"] is False
    assert second.status_code == 201
    assert second.json()["cached"] is True
    assert workflow.calls == 1
    review_id = first.json()["review_id"]

    fetched = client.get(f"/api/v1/reviews/{review_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["metadata"] == {"source": "test"}
    assert (
        client.get(
            f"/api/v1/reviews/{review_id}",
            headers={"X-Org-ID": "org-b", "X-Session-ID": "session-a"},
        ).status_code
        == 404
    )

    obligations = client.get(f"/api/v1/reviews/{review_id}/obligations", headers=headers)
    assert obligations.status_code == 200
    assert obligations.json()["obligations"][0]["obligation_id"] == "obligation-1"

    feedback = client.post(
        f"/api/v1/reviews/{review_id}/feedback",
        headers=headers,
        json={"rating": 5, "helpful": True, "comment": "Useful"},
    )
    assert feedback.status_code == 201
    assert feedback.json()["accepted"] is True
    assert events.count("review.created") == 2
    assert events.count("review.completed") == 2
    assert "review.feedback_submitted" in events


def test_cache_does_not_cross_session(
    app_client: tuple[TestClient, FakeWorkflow, list[str]],
) -> None:
    client, workflow, _ = app_client
    request = {"text": "甲方应付款。", "contract_id": "contract-1"}

    client.post(
        "/api/v1/reviews/text",
        json=request,
        headers={"X-Org-ID": "org", "X-Session-ID": "session-a"},
    )
    response = client.post(
        "/api/v1/reviews/text",
        json=request,
        headers={"X-Org-ID": "org", "X-Session-ID": "session-b"},
    )

    assert response.status_code == 201
    assert response.json()["cached"] is False
    assert workflow.calls == 2


def test_multipart_markdown_review(
    app_client: tuple[TestClient, FakeWorkflow, list[str]],
) -> None:
    client, _, _ = app_client

    response = client.post(
        "/api/v1/reviews",
        files={"file": ("contract.md", "甲方应付款。", "text/markdown")},
        data={"contract_id": "upload-1", "metadata": '{"source":"upload"}'},
    )

    assert response.status_code == 201
    assert response.json()["contract_id"] == "upload-1"
    assert response.json()["metadata"] == {"source": "upload"}


def test_invalid_multipart_metadata_is_rejected(
    app_client: tuple[TestClient, FakeWorkflow, list[str]],
) -> None:
    client, workflow, _ = app_client

    response = client.post(
        "/api/v1/reviews",
        files={"file": ("contract.txt", "terms", "text/plain")},
        data={"metadata": "[]"},
    )

    assert response.status_code == 422
    assert workflow.calls == 0


def test_profile_memory_endpoint_is_session_scoped(
    app_client: tuple[TestClient, FakeWorkflow, list[str]],
) -> None:
    client, _, _ = app_client
    repository = client.app.state.repository
    repository.upsert_memory(
        org_id="org-a",
        session_id="session-a",
        layer=MemoryLayer.PROFILE,
        key="preferred-language",
        content={"value": "zh-CN"},
    )

    response = client.get(
        "/api/v1/memories/profile",
        headers={"X-Org-ID": "org-a", "X-Session-ID": "session-a"},
    )
    isolated = client.get(
        "/api/v1/memories/profile",
        headers={"X-Org-ID": "org-a", "X-Session-ID": "session-b"},
    )

    assert response.status_code == 200
    assert response.json()["memories"][0]["key"] == "preferred-language"
    assert isolated.status_code == 200
    assert isolated.json()["memories"] == []


def test_profile_memory_can_be_upserted_and_invalidates_cached_review(
    app_client: tuple[TestClient, FakeWorkflow, list[str]],
) -> None:
    client, workflow, _ = app_client
    headers = {"X-Org-ID": "org-a", "X-Session-ID": "session-a"}
    request = {"text": "甲方应在验收后付款。", "contract_id": "contract-memory"}

    first = client.post("/api/v1/reviews/text", json=request, headers=headers)
    cached = client.post("/api/v1/reviews/text", json=request, headers=headers)
    memory = client.put(
        "/api/v1/memories/profile/payment-policy",
        headers=headers,
        json={
            "content": "付款触发条件必须与验收标准对应",
            "metadata": {"owner": "legal"},
        },
    )
    refreshed = client.post("/api/v1/reviews/text", json=request, headers=headers)

    assert first.status_code == 201
    assert cached.json()["cached"] is True
    assert memory.status_code == 200
    assert memory.json()["key"] == "payment-policy"
    assert memory.json()["metadata"]["source"] == "profile_api"
    assert refreshed.status_code == 201
    assert refreshed.json()["cached"] is False
    assert workflow.calls == 2


def test_completed_review_creates_compact_short_term_memory(
    app_client: tuple[TestClient, FakeWorkflow, list[str]],
) -> None:
    client, _, _ = app_client
    headers = {"X-Org-ID": "org-a", "X-Session-ID": "session-a"}

    response = client.post(
        "/api/v1/reviews/text",
        json={"text": "甲方应付款。", "contract_id": "short-term-contract"},
        headers=headers,
    )

    memories = client.app.state.repository.list_memories(
        org_id="org-a",
        session_id="session-a",
        layer=MemoryLayer.SHORT_TERM,
    )
    assert response.status_code == 201
    assert len(memories) == 1
    assert memories[0].metadata["contains_contract_text"] is False
    assert "甲方应付款" not in str(memories[0].content)


def test_negative_feedback_becomes_episodic_error_memory(
    app_client: tuple[TestClient, FakeWorkflow, list[str]],
) -> None:
    client, _, _ = app_client
    headers = {"X-Org-ID": "org-a", "X-Session-ID": "session-a"}
    created = client.post(
        "/api/v1/reviews/text",
        headers=headers,
        json={"text": "甲方应付款。"},
    )
    review_id = created.json()["review_id"]

    response = client.post(
        f"/api/v1/reviews/{review_id}/feedback",
        headers=headers,
        json={"rating": 1, "accepted": False, "comment": "Incorrect"},
    )

    assert response.status_code == 201
    memories = client.app.state.repository.list_memories(
        org_id="org-a",
        session_id="session-a",
        layer=MemoryLayer.EPISODIC,
    )
    assert len(memories) == 1
    assert memories[0].metadata["error"] is True
    assert memories[0].metadata["error_type"] == "negative_review_feedback"
