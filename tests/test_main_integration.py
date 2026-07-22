from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

import contract_guard.main as main_module
from contract_guard.config import Settings
from contract_guard.main import create_app


def test_default_offline_app_wires_knowledge_and_profile_memory(tmp_path: Any) -> None:
    settings = Settings(
        sqlite_path=str(tmp_path / "reviews.db"),
        knowledge_path="resources/demo_knowledge_base.json",
        auth_required=False,
        legacy_tenant_headers_enabled=True,
    )
    app = create_app(settings=settings)
    headers = {"X-Org-ID": "org-a", "X-Session-ID": "session-a"}

    with TestClient(app) as client:
        stored = client.put(
            "/api/v1/memories/profile/review-focus",
            headers=headers,
            json={"content": "验收付款触发条件必须清晰"},
        )
        reviewed = client.post(
            "/api/v1/reviews/text",
            headers=headers,
            json={
                "contract_id": "offline-integration",
                "text": "甲方单方认定验收，并有权无限期延迟付款。",
            },
        )

    assert stored.status_code == 200
    assert reviewed.status_code == 201
    report = reviewed.json()["report"]
    assert report["quality"]["llm_review_performed"] is False
    assert report["analysis_notes"]
    assert {item["source"] for item in report["contexts"]} == {
        "knowledge",
        "memory",
    }


def test_hybrid_app_automatically_wires_vision_ocr(tmp_path: Any, monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class FakeVisionOCR:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def extract_text(
            self,
            image: bytes,
            *,
            media_type: str,
            filename: str | None = None,
        ) -> str:
            captured.update(
                image_size=len(image),
                media_type=media_type,
                filename=filename,
            )
            return "甲方应在验收后付款。"

    class FakeWorkflow:
        async def areview(
            self,
            text: str,
            contract_id: str | None = None,
            **_: Any,
        ) -> dict[str, Any]:
            return {
                "report_id": "image-report",
                "contract_id": contract_id or "image-contract",
                "findings": [],
                "obligations": [],
                "transcribed_text": text,
            }

    monkeypatch.setattr(main_module, "OpenAIVisionOCR", FakeVisionOCR)
    app = create_app(
        settings=Settings(
            app_mode="hybrid",
            llm_enabled=True,
            openai_model="test-vision-model",
            sqlite_path=str(tmp_path / "reviews.db"),
            auth_required=False,
            legacy_tenant_headers_enabled=True,
        ),
        workflow=FakeWorkflow(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reviews",
            files={"file": ("contract.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
        )

    assert response.status_code == 201
    assert response.json()["report"]["transcribed_text"] == "甲方应在验收后付款。"
    assert captured["model"] == "test-vision-model"
    assert captured["media_type"] == "image/png"
