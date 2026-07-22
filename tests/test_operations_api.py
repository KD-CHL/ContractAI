from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from contract_guard.config import Settings
from contract_guard.main import create_app

OWNER_PASSWORD = "ContractGuard1!"
REVIEWER_PASSWORD = "ReviewerAccount1!"
VIEWER_PASSWORD = "ViewerAccount1!"


class OperationsWorkflow:
    async def areview(
        self,
        text: str,
        contract_id: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        return {
            "report_id": "operations-report",
            "contract_id": contract_id or "generated-contract",
            "findings": [
                {
                    "finding_id": "risk-unlimited-liability",
                    "title": "责任范围可能未设上限",
                    "description": "责任范围需要人工确认",
                    "risk_level": "high",
                    "recommendation": "明确责任上限",
                    "evidence": [{"quote": "承担无限责任"}],
                }
            ],
            "obligations": [
                {
                    "obligation_id": "obligation-payment",
                    "obligor": "甲方",
                    "action": "在验收后十日内付款",
                    "due_expression": "验收后十日内",
                    "evidence": {"quote": "甲方应在验收后十日内付款"},
                }
            ],
            "summary": {
                "total_findings": 1,
                "highest_risk_level": "high",
            },
            "quality": {"evidence_coverage": 1.0, "llm_review_performed": False},
        }


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "风险运营测试部",
            "display_name": "所有者",
            "email": "operations-owner@example.com",
            "password": OWNER_PASSWORD,
        },
    )
    assert response.status_code == 201
    return response.json()


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return _headers(response.json()["access_token"])


def test_operations_work_queue_rbac_and_approval_gate(tmp_path: Any) -> None:
    app = create_app(
        settings=Settings(
            sqlite_path=str(tmp_path / "operations.db"),
            auth_required=True,
            registration_enabled=True,
        ),
        workflow=OperationsWorkflow(),
    )
    with TestClient(app) as client:
        owner = _register(client)
        owner_headers = _headers(owner["access_token"])
        reviewer = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "email": "operations-reviewer@example.com",
                "display_name": "处置审阅员",
                "password": REVIEWER_PASSWORD,
                "role": "reviewer",
            },
        )
        viewer = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "email": "operations-viewer@example.com",
                "display_name": "只读同事",
                "password": VIEWER_PASSWORD,
                "role": "viewer",
            },
        )
        assert reviewer.status_code == 201
        assert viewer.status_code == 201

        created = client.post(
            "/api/v1/reviews/text",
            headers=owner_headers,
            json={
                "text": "乙方承担无限责任。甲方应在验收后十日内付款。",
                "filename": "运营闭环合同.txt",
                "contract_id": "OPS-001",
            },
        )
        assert created.status_code == 201
        review = created.json()
        review_id = review["review_id"]
        assert review["state_version"] == 1

        work_items = client.get(
            f"/api/v1/reviews/{review_id}/work-items",
            headers=owner_headers,
        )
        assert work_items.status_code == 200
        assert len(work_items.json()["items"]) == 2
        by_kind = {item["kind"]: item for item in work_items.json()["items"]}
        finding = by_kind["finding"]
        obligation = by_kind["obligation"]
        assert finding["status"] == "open"
        assert obligation["status"] == "pending"
        assert finding["document_name"] == "运营闭环合同.txt"

        summary = client.get("/api/v1/operations/summary", headers=owner_headers)
        queue = client.get(
            "/api/v1/work-items?kind=finding&risk_level=high",
            headers=owner_headers,
        )
        assert summary.status_code == 200
        assert summary.json()["high_risk_open"] == 1
        assert queue.status_code == 200
        assert queue.json()["total"] == 1

        submitted = client.patch(
            f"/api/v1/reviews/{review_id}/decision",
            headers=owner_headers,
            json={"expected_version": 1, "status": "in_review"},
        )
        blocked = client.patch(
            f"/api/v1/reviews/{review_id}/decision",
            headers=owner_headers,
            json={"expected_version": 2, "status": "approved"},
        )
        assert submitted.status_code == 200
        assert submitted.json()["state_version"] == 2
        assert blocked.status_code == 409
        assert blocked.json()["detail"] == (
            "审批被阻塞：仍有 1 个高风险工作项未解决或接受，请先完成处置后再批准。"
        )

        viewer_headers = _login(
            client,
            "operations-viewer@example.com",
            VIEWER_PASSWORD,
        )
        viewer_can_read = client.get("/api/v1/work-items", headers=viewer_headers)
        viewer_cannot_update = client.patch(
            f"/api/v1/work-items/{finding['work_item_id']}",
            headers=viewer_headers,
            json={"expected_version": 1, "status": "in_progress"},
        )
        assert viewer_can_read.status_code == 200
        assert viewer_cannot_update.status_code == 403

        reviewer_headers = _login(
            client,
            "operations-reviewer@example.com",
            REVIEWER_PASSWORD,
        )
        reviewer_id = reviewer.json()["user_id"]
        claimed = client.patch(
            f"/api/v1/work-items/{finding['work_item_id']}",
            headers=reviewer_headers,
            json={
                "expected_version": 1,
                "assignee_user_id": reviewer_id,
                "status": "in_progress",
                "due_at": "2030-07-20T09:00:00+08:00",
            },
        )
        assert claimed.status_code == 200
        assert claimed.json()["state_version"] == 2
        assert claimed.json()["assignee_user_id"] == reviewer_id

        forbidden_accept = client.patch(
            f"/api/v1/work-items/{finding['work_item_id']}",
            headers=reviewer_headers,
            json={
                "expected_version": 2,
                "status": "accepted",
                "note": "业务接受此风险",
            },
        )
        stale = client.patch(
            f"/api/v1/work-items/{finding['work_item_id']}",
            headers=reviewer_headers,
            json={"expected_version": 1, "status": "resolved", "note": "已修改条款"},
        )
        resolved = client.patch(
            f"/api/v1/work-items/{finding['work_item_id']}",
            headers=reviewer_headers,
            json={"expected_version": 2, "status": "resolved", "note": "已写入责任上限"},
        )
        assert forbidden_accept.status_code == 403
        assert stale.status_code == 409
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"
        assert resolved.json()["completed_at"] is not None

        approved = client.patch(
            f"/api/v1/reviews/{review_id}/decision",
            headers=owner_headers,
            json={"expected_version": 2, "status": "approved"},
        )
        events = client.get(
            f"/api/v1/work-items/{finding['work_item_id']}/events",
            headers=owner_headers,
        )
        audit = client.get("/api/v1/audit-logs", headers=owner_headers)
        assert approved.status_code == 200
        assert approved.json()["decision_status"] == "approved"
        assert events.status_code == 200
        assert len(events.json()["items"]) >= 3
        actions = {item["action"] for item in audit.json()["items"]}
        assert "work_item.updated" in actions
        assert "review.decision_changed" in actions


def test_operations_reject_invalid_assignee_and_naive_due_at(tmp_path: Any) -> None:
    app = create_app(
        settings=Settings(
            sqlite_path=str(tmp_path / "operations-validation.db"),
            auth_required=True,
        ),
        workflow=OperationsWorkflow(),
    )
    with TestClient(app) as client:
        owner = _register(client)
        headers = _headers(owner["access_token"])
        viewer = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "email": "assignee-viewer@example.com",
                "display_name": "不可指派成员",
                "password": VIEWER_PASSWORD,
                "role": "viewer",
            },
        )
        created = client.post(
            "/api/v1/reviews/text",
            headers=headers,
            json={"text": "承担无限责任", "filename": "校验合同.txt"},
        )
        item = client.get(
            f"/api/v1/reviews/{created.json()['review_id']}/work-items",
            headers=headers,
        ).json()["items"][0]

        invalid_assignee = client.patch(
            f"/api/v1/work-items/{item['work_item_id']}",
            headers=headers,
            json={
                "expected_version": item["state_version"],
                "assignee_user_id": viewer.json()["user_id"],
            },
        )
        naive_due = client.patch(
            f"/api/v1/work-items/{item['work_item_id']}",
            headers=headers,
            json={"expected_version": item["state_version"], "due_at": "2030-07-20T09:00:00"},
        )
        assert invalid_assignee.status_code == 400
        assert naive_due.status_code == 422


def test_reviewer_can_submit_draft_and_rejected_but_cannot_reopen_approved(
    tmp_path: Any,
) -> None:
    app = create_app(
        settings=Settings(
            sqlite_path=str(tmp_path / "reviewer-decision-permissions.db"),
            auth_required=True,
        ),
        workflow=OperationsWorkflow(),
    )
    with TestClient(app) as client:
        owner = _register(client)
        owner_headers = _headers(owner["access_token"])
        reviewer = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "email": "decision-reviewer@example.com",
                "display_name": "审批提交人",
                "password": REVIEWER_PASSWORD,
                "role": "reviewer",
            },
        )
        assert reviewer.status_code == 201
        reviewer_headers = _login(
            client,
            "decision-reviewer@example.com",
            REVIEWER_PASSWORD,
        )

        created = client.post(
            "/api/v1/reviews/text",
            headers=owner_headers,
            json={"text": "乙方承担无限责任。", "filename": "审批权限合同.txt"},
        )
        assert created.status_code == 201
        review_id = created.json()["review_id"]

        submitted = client.patch(
            f"/api/v1/reviews/{review_id}/decision",
            headers=reviewer_headers,
            json={"expected_version": 1, "status": "in_review"},
        )
        rejected = client.patch(
            f"/api/v1/reviews/{review_id}/decision",
            headers=owner_headers,
            json={
                "expected_version": 2,
                "status": "rejected",
                "note": "请补充责任上限",
            },
        )
        resubmitted = client.patch(
            f"/api/v1/reviews/{review_id}/decision",
            headers=reviewer_headers,
            json={"expected_version": 3, "status": "in_review"},
        )
        assert submitted.status_code == 200
        assert rejected.status_code == 200
        assert resubmitted.status_code == 200

        finding = client.get(
            f"/api/v1/reviews/{review_id}/work-items",
            headers=owner_headers,
        ).json()["items"][0]
        accepted = client.patch(
            f"/api/v1/work-items/{finding['work_item_id']}",
            headers=owner_headers,
            json={
                "expected_version": finding["state_version"],
                "status": "accepted",
                "note": "所有者确认接受该风险",
            },
        )
        approved = client.patch(
            f"/api/v1/reviews/{review_id}/decision",
            headers=owner_headers,
            json={"expected_version": 4, "status": "approved"},
        )
        reviewer_reopen = client.patch(
            f"/api/v1/reviews/{review_id}/decision",
            headers=reviewer_headers,
            json={"expected_version": 5, "status": "in_review"},
        )

        assert accepted.status_code == 200
        assert approved.status_code == 200
        assert approved.json()["decision_status"] == "approved"
        assert reviewer_reopen.status_code == 403
        assert reviewer_reopen.json()["detail"] == (
            "审阅员只能提交草稿或重新提交已驳回的审阅；已批准审阅只能由管理员重新打开"
        )
