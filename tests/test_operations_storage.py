from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from contract_guard.domain.operations import (
    ApprovalBlocked,
    InvalidDueAt,
    InvalidTransition,
    StateConflict,
    WorkItemKind,
)
from contract_guard.services.storage import SQLiteReviewRepository


def _completed_review(repository: SQLiteReviewRepository) -> tuple[str, str, str]:
    review = repository.create_review(
        org_id="org-a",
        session_id="session-a",
        fingerprint="operations-fingerprint",
        document_name="operations-contract.txt",
        media_type="text/plain",
    )
    report = {
        "findings": [
            {
                "finding_id": "duplicate-id",
                "title": "无限责任",
                "risk_level": "high",
                "description": "责任范围没有上限",
            },
            {
                "finding_id": "duplicate-id",
                "title": "低风险提示",
                "risk_level": "low",
            },
        ],
        "obligations": [
            {
                "action": "在十日内付款",
                "obligor": "甲方",
                "due_expression": "十日内",
            }
        ],
    }
    repository.update_review(
        review.id,
        org_id="org-a",
        session_id="session-a",
        status="completed",
        report=report,
    )
    # Replaying the same completion must not duplicate work or materialization events.
    repository.update_review(
        review.id,
        org_id="org-a",
        session_id="session-a",
        status="completed",
        report=report,
    )
    return review.id, "org-a", "session-a"


def test_completed_review_materializes_idempotent_work_items_and_events() -> None:
    repository = SQLiteReviewRepository(":memory:")
    review_id, org_id, _ = _completed_review(repository)

    items = repository.list_review_work_items(review_id, org_id=org_id)

    assert len(items) == 3
    findings = [item for item in items if item.kind is WorkItemKind.FINDING]
    obligation = next(item for item in items if item.kind is WorkItemKind.OBLIGATION)
    assert [item.source_ordinal for item in findings] == [0, 1]
    assert [item.source_id for item in findings] == ["duplicate-id", "duplicate-id"]
    assert [item.status for item in findings] == ["open", "open"]
    assert obligation.source_id is None
    assert obligation.status == "pending"
    assert sum(len(repository.list_work_item_events(item.id, org_id=org_id)) for item in items) == 3


def test_work_item_update_validates_due_date_transition_and_state_version() -> None:
    repository = SQLiteReviewRepository(":memory:")
    review_id, org_id, _ = _completed_review(repository)
    finding = next(
        item
        for item in repository.list_review_work_items(review_id, org_id=org_id)
        if item.kind is WorkItemKind.FINDING and item.risk_level == "high"
    )

    with pytest.raises(InvalidDueAt):
        repository.update_work_item(
            finding.id,
            org_id=org_id,
            expected_version=1,
            due_at=datetime(2027, 1, 1),
        )
    with pytest.raises(InvalidTransition):
        repository.update_work_item(
            finding.id,
            org_id=org_id,
            expected_version=1,
            status="resolved",
        )

    due_at = datetime.now(UTC) + timedelta(days=2)
    assigned = repository.update_work_item(
        finding.id,
        org_id=org_id,
        expected_version=1,
        assignee_user_id="reviewer-a",
        due_at=due_at,
        actor_user_id="owner-a",
    )
    resolved = repository.update_work_item(
        finding.id,
        org_id=org_id,
        expected_version=assigned.state_version,
        status="resolved",
        note="已通过补充协议设置责任上限",
        actor_user_id="reviewer-a",
    )

    assert assigned.due_at == due_at
    assert resolved.status == "resolved"
    assert resolved.completed_at is not None
    assert resolved.state_version == 3
    events = repository.list_work_item_events(finding.id, org_id=org_id)
    assert [event.action for event in events] == [
        "materialized",
        "assigned",
        "status_changed",
    ]
    with pytest.raises(StateConflict) as conflict:
        repository.update_work_item(
            finding.id,
            org_id=org_id,
            expected_version=1,
            note="stale",
        )
    assert conflict.value.current == 3


def test_queue_filters_summary_and_soft_delete_visibility() -> None:
    repository = SQLiteReviewRepository(":memory:")
    review_id, org_id, _ = _completed_review(repository)
    obligation = next(
        item
        for item in repository.list_review_work_items(review_id, org_id=org_id)
        if item.kind is WorkItemKind.OBLIGATION
    )
    overdue_at = datetime.now(UTC) - timedelta(days=1)
    repository.update_work_item(
        obligation.id,
        org_id=org_id,
        expected_version=1,
        assignee_user_id="reviewer-a",
        due_at=overdue_at,
    )

    overdue_items, overdue_total = repository.list_work_items(
        org_id=org_id,
        overdue=True,
        assignee_user_id="reviewer-a",
    )
    summary = repository.operations_summary(org_id=org_id, user_id="reviewer-a")

    assert overdue_total == 1
    assert [item.id for item in overdue_items] == [obligation.id]
    assert summary == {
        "assigned_to_me": 1,
        "overdue": 1,
        "open_findings": 2,
        "pending_obligations": 1,
        "open_high_risk": 1,
        "pending_approvals": 0,
        "completed_this_week": 0,
    }

    assert repository.soft_delete_review(
        review_id,
        org_id=org_id,
        user_id=None,
        can_manage_all=True,
    )
    hidden, total = repository.list_work_items(org_id=org_id)
    assert hidden == ()
    assert total == 0
    assert repository.operations_summary(org_id=org_id, user_id="reviewer-a")["overdue"] == 0


def test_review_decision_requires_completed_valid_flow_and_closed_high_risks() -> None:
    repository = SQLiteReviewRepository(":memory:")
    review_id, org_id, _ = _completed_review(repository)

    in_review = repository.transition_review_decision(
        review_id,
        org_id=org_id,
        expected_version=1,
        target_status="in_review",
        actor_user_id="reviewer-a",
    )
    assert in_review.decision_status == "in_review"
    assert in_review.state_version == 2

    with pytest.raises(ApprovalBlocked) as blocked:
        repository.transition_review_decision(
            review_id,
            org_id=org_id,
            expected_version=2,
            target_status="approved",
            actor_user_id="owner-a",
        )
    assert len(blocked.value.blocker_ids) == 1
    assert str(blocked.value) == (
        "审批被阻塞：仍有 1 个高风险工作项未解决或接受，请先完成处置后再批准。"
    )

    high_risk = next(
        item
        for item in repository.list_review_work_items(review_id, org_id=org_id)
        if item.risk_level == "high"
    )
    repository.update_work_item(
        high_risk.id,
        org_id=org_id,
        expected_version=1,
        status="accepted",
        note="所有者确认接受该风险",
        actor_user_id="owner-a",
    )
    approved = repository.transition_review_decision(
        review_id,
        org_id=org_id,
        expected_version=2,
        target_status="approved",
        actor_user_id="owner-a",
    )
    assert approved.decision_status == "approved"
    assert approved.state_version == 3


def test_rejected_review_requires_note() -> None:
    repository = SQLiteReviewRepository(":memory:")
    review_id, org_id, _ = _completed_review(repository)
    repository.transition_review_decision(
        review_id,
        org_id=org_id,
        expected_version=1,
        target_status="in_review",
    )

    with pytest.raises(InvalidTransition):
        repository.transition_review_decision(
            review_id,
            org_id=org_id,
            expected_version=2,
            target_status="rejected",
        )
    rejected = repository.transition_review_decision(
        review_id,
        org_id=org_id,
        expected_version=2,
        target_status="rejected",
        note="请先补齐责任上限",
    )
    assert rejected.decision_status == "rejected"
