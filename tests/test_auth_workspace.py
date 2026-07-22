from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from contract_guard.config import Settings
from contract_guard.main import create_app

PASSWORD = "ContractGuard1!"
VIEWER_PASSWORD = "ViewerAccount1!"
REVIEWER_PASSWORD = "ReviewerAccount1!"


class WorkspaceWorkflow:
    async def areview(
        self,
        text: str,
        contract_id: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        high_risk = "无限责任" in text
        return {
            "report_id": "workspace-report",
            "contract_id": contract_id or "generated-contract",
            "findings": (
                [
                    {
                        "finding_id": "risk-1",
                        "title": "责任风险",
                        "description": "责任范围需要复核",
                        "risk_level": "high",
                        "recommendation": "明确责任上限",
                        "evidence": [{"quote": "无限责任"}],
                    }
                ]
                if high_risk
                else []
            ),
            "obligations": [],
            "summary": {
                "total_findings": 1 if high_risk else 0,
                "highest_risk_level": "high" if high_risk else None,
            },
            "quality": {"evidence_coverage": 1.0, "llm_review_performed": False},
        }


def _register(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "测试法务部",
            "display_name": "管理员",
            "email": "owner@example.com",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201
    return response.json()


def _app(tmp_path: Any) -> Any:
    return create_app(
        settings=Settings(
            sqlite_path=str(tmp_path / "workspace.db"),
            auth_required=True,
            registration_enabled=True,
        ),
        workflow=WorkspaceWorkflow(),
    )


def test_authentication_cookie_refresh_and_request_errors(tmp_path: Any) -> None:
    app = _app(tmp_path)
    with TestClient(app) as client:
        status_response = client.get("/api/v1/auth/status")
        unauthenticated = client.get("/api/v1/reviews")
        session = _register(client)

        assert status_response.json()["bootstrap_required"] is True
        assert unauthenticated.status_code == 401
        assert unauthenticated.json()["code"] == "UNAUTHENTICATED"
        assert unauthenticated.json()["requestId"] == unauthenticated.headers["x-request-id"]
        assert session["user"]["role"] == "owner"
        assert "contractguard_access=" in client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": PASSWORD},
        ).headers.get("set-cookie", "")

        current = client.get("/api/v1/auth/me")
        old_access = session["access_token"]
        refreshed = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": session["refresh_token"]},
        )
        old_access_result = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {old_access}"},
        )
        assert current.status_code == 200
        assert current.json()["user"]["email"] == "owner@example.com"
        assert refreshed.status_code == 200
        assert refreshed.json()["access_token"] != old_access
        assert old_access_result.status_code == 401

        logged_out = client.post("/api/v1/auth/logout")
        after_logout = client.get("/api/v1/auth/me")
        replayed_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": session["refresh_token"]},
        )
        assert logged_out.status_code == 200
        assert after_logout.status_code == 401
        assert replayed_refresh.status_code == 401


def test_workspace_rbac_history_delete_restore_and_audit(tmp_path: Any) -> None:
    app = _app(tmp_path)
    with TestClient(app) as client:
        owner = _register(client)
        owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}

        viewer = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "email": "viewer@example.com",
                "display_name": "业务同事",
                "password": VIEWER_PASSWORD,
                "role": "viewer",
            },
        )
        reviewer = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "email": "reviewer@example.com",
                "display_name": "法务审阅员",
                "password": REVIEWER_PASSWORD,
                "role": "reviewer",
            },
        )
        owner_review = client.post(
            "/api/v1/reviews/text",
            headers=owner_headers,
            json={
                "text": "乙方承担无限责任。",
                "contract_id": "OWNER-001",
                "filename": "所有者合同.txt",
            },
        )

        viewer_login = client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": VIEWER_PASSWORD},
        )
        viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}
        forbidden_members = client.get("/api/v1/users", headers=viewer_headers)
        visible_owner_review = client.get(
            f"/api/v1/reviews/{owner_review.json()['review_id']}",
            headers=viewer_headers,
        )
        forbidden_viewer_review = client.post(
            "/api/v1/reviews/text",
            headers=viewer_headers,
            json={
                "text": "甲方应在十日内付款。",
                "contract_id": "VIEWER-001",
                "filename": "业务合同.txt",
            },
        )
        reviewer_login = client.post(
            "/api/v1/auth/login",
            json={"email": "reviewer@example.com", "password": REVIEWER_PASSWORD},
        )
        reviewer_headers = {"Authorization": f"Bearer {reviewer_login.json()['access_token']}"}
        reviewer_review = client.post(
            "/api/v1/reviews/text",
            headers=reviewer_headers,
            json={
                "text": "甲方应在十日内付款。",
                "contract_id": "REVIEWER-001",
                "filename": "业务合同.txt",
            },
        )
        viewer_list = client.get("/api/v1/reviews", headers=viewer_headers)
        owner_list = client.get(
            "/api/v1/reviews?q=合同&status=completed",
            headers=owner_headers,
        )
        dashboard = client.get("/api/v1/dashboard/summary", headers=owner_headers)

        assert viewer.status_code == 201
        assert reviewer.status_code == 201
        assert owner_review.status_code == 201
        assert forbidden_members.status_code == 403
        assert visible_owner_review.status_code == 200
        assert forbidden_viewer_review.status_code == 403
        assert reviewer_review.status_code == 201
        assert viewer_list.json()["total"] == 2
        assert owner_list.json()["total"] == 2
        assert dashboard.json()["total_reviews"] == 2
        assert dashboard.json()["high_risk_reviews"] == 1

        reviewer_review_id = reviewer_review.json()["review_id"]
        forbidden_viewer_delete = client.delete(
            f"/api/v1/reviews/{reviewer_review_id}",
            headers=viewer_headers,
        )
        forbidden_cross_user_delete = client.delete(
            f"/api/v1/reviews/{owner_review.json()['review_id']}",
            headers=reviewer_headers,
        )
        deleted = client.delete(
            f"/api/v1/reviews/{reviewer_review_id}",
            headers=owner_headers,
        )
        deleted_detail = client.get(
            f"/api/v1/reviews/{reviewer_review_id}",
            headers=owner_headers,
        )
        active_list = client.get("/api/v1/reviews", headers=owner_headers)
        trash_list = client.get(
            "/api/v1/reviews?include_deleted=true",
            headers=owner_headers,
        )
        restored = client.post(
            f"/api/v1/reviews/{reviewer_review_id}/restore",
            headers=owner_headers,
        )
        exported = client.get(
            f"/api/v1/reviews/{owner_review.json()['review_id']}/export?format=json",
            headers=owner_headers,
        )
        audit = client.get("/api/v1/audit-logs", headers=owner_headers)

        assert forbidden_viewer_delete.status_code == 403
        assert forbidden_cross_user_delete.status_code == 404
        assert deleted.status_code == 200
        assert deleted_detail.status_code == 200
        assert deleted_detail.json()["deleted_at"] is not None
        assert active_list.json()["total"] == 1
        assert trash_list.json()["total"] == 2
        assert restored.status_code == 200
        assert exported.status_code == 200
        assert exported.headers["content-disposition"].endswith('.json"')
        actions = {item["action"] for item in audit.json()["items"]}
        assert {
            "identity.organization_registered",
            "identity.member_created",
            "review.created",
            "review.deleted",
            "review.restored",
            "review.exported",
        }.issubset(actions)


def test_registration_conflict_password_policy_and_owner_protection(tmp_path: Any) -> None:
    app = _app(tmp_path)
    with TestClient(app) as client:
        owner = _register(client)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}

        weak = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "email": "weak@example.com",
                "display_name": "弱密码用户",
                "password": "onlylowercase",
                "role": "viewer",
            },
        )
        conflict = client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "另一个组织",
                "display_name": "重复邮箱",
                "email": "OWNER@example.com",
                "password": PASSWORD,
            },
        )
        disable_owner = client.patch(
            f"/api/v1/users/{owner['user']['user_id']}",
            headers=headers,
            json={"status": "disabled"},
        )
        admin = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "email": "admin@example.com",
                "display_name": "组织管理员",
                "password": REVIEWER_PASSWORD,
                "role": "admin",
            },
        )
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": REVIEWER_PASSWORD},
        )
        promote_admin = client.patch(
            f"/api/v1/users/{admin.json()['user_id']}",
            headers={"Authorization": f"Bearer {admin_login.json()['access_token']}"},
            json={"role": "owner"},
        )

        assert weak.status_code == 422
        assert conflict.status_code == 409
        assert disable_owner.status_code == 403
        assert admin.status_code == 201
        assert promote_admin.status_code == 403


def test_legacy_header_scope_cannot_access_identity_admin(tmp_path: Any) -> None:
    app = create_app(
        settings=Settings(
            sqlite_path=str(tmp_path / "legacy.db"),
            auth_required=False,
        ),
        workflow=WorkspaceWorkflow(),
    )
    with TestClient(app) as client:
        headers = {"X-Org-ID": "target-org", "X-Session-ID": "anonymous"}

        assert client.get("/api/v1/users", headers=headers).status_code == 401
        assert client.get("/api/v1/audit-logs", headers=headers).status_code == 401
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 401


def test_change_password_revokes_sessions_and_requires_new_password(tmp_path: Any) -> None:
    app = _app(tmp_path)
    new_password = "ChangedPassword2!"
    with TestClient(app) as client:
        owner = _register(client)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}

        changed = client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": PASSWORD, "new_password": new_password},
        )
        stale_session = client.get("/api/v1/auth/me", headers=headers)
        old_login = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": PASSWORD},
        )
        new_login = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": new_password},
        )

        assert changed.status_code == 200
        assert stale_session.status_code == 401
        assert old_login.status_code == 401
        assert new_login.status_code == 200


def test_closed_registration_still_allows_only_the_first_owner(tmp_path: Any) -> None:
    app = create_app(
        settings=Settings(
            sqlite_path=str(tmp_path / "closed-registration.db"),
            auth_required=True,
            registration_enabled=False,
        ),
        workflow=WorkspaceWorkflow(),
    )
    with TestClient(app) as client:
        first = _register(client)
        second = client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "第二个组织",
                "display_name": "第二个所有者",
                "email": "second-owner@example.com",
                "password": PASSWORD,
            },
        )

        assert first["user"]["role"] == "owner"
        assert second.status_code == 403
