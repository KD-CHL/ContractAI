"""Operational work queue, work-item lifecycle, and review decision endpoints."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, Never

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from contract_guard.api.dependencies import (
    TenantScope,
    get_repository,
    get_tenant_scope,
    require_roles,
)
from contract_guard.api.operations_schemas import (
    OperationsSummaryResponse,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewWorkItemsResponse,
    WorkItemEventResponse,
    WorkItemEventsResponse,
    WorkItemListResponse,
    WorkItemResponse,
    WorkItemUpdateRequest,
)
from contract_guard.domain.operations import (
    UNSET,
    ApprovalBlocked,
    AssignmentError,
    InvalidDueAt,
    InvalidTransition,
    ReviewNotFound,
    StateConflict,
    WorkItemNotFound,
)
from contract_guard.services.identity import (
    IdentityUser,
    SQLiteIdentityService,
    UserRole,
    UserStatus,
)
from contract_guard.services.storage import (
    ReviewRepository,
    StoredReview,
    StoredWorkItem,
    StoredWorkItemEvent,
)

router = APIRouter(tags=["operations"])

_MUTATING_ROLES = (UserRole.OWNER, UserRole.ADMIN, UserRole.REVIEWER)
_PRIVILEGED_ROLES = frozenset({UserRole.OWNER, UserRole.ADMIN})
_PRIVILEGED_WORK_STATUSES = frozenset({"accepted", "waived"})
_FINAL_DECISIONS = frozenset({"approved", "rejected"})
_REVIEWER_SUBMITTABLE_DECISIONS = frozenset({"draft", "rejected"})


def _operations(repository: ReviewRepository) -> Any:
    required = (
        "get_work_item",
        "list_review_work_items",
        "list_work_item_events",
        "list_work_items",
        "operations_summary",
        "transition_review_decision",
        "update_work_item",
    )
    if any(not callable(getattr(repository, name, None)) for name in required):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="处置工作台暂时不可用",
        )
    return repository


def _identity(request: Request) -> SQLiteIdentityService | None:
    value = getattr(request.app.state, "identity", None)
    return value if isinstance(value, SQLiteIdentityService) else None


def _review_for_org(
    repository: ReviewRepository,
    review_id: str,
    scope: TenantScope,
) -> StoredReview | None:
    getter = getattr(repository, "get_review_for_actor", None)
    if callable(getter):
        return getter(
            review_id,
            org_id=scope.org_id,
            user_id=scope.user_id,
            can_manage_all=True,
            include_deleted=False,
        )
    return repository.get_review(review_id, org_id=scope.org_id, session_id=scope.session_id)


def _user(
    identity: SQLiteIdentityService | None,
    user_id: str | None,
    cache: dict[str, IdentityUser | None],
) -> IdentityUser | None:
    if not user_id or identity is None:
        return None
    if user_id not in cache:
        cache[user_id] = identity.get_user(user_id)
    return cache[user_id]


def _work_item_response(
    item: StoredWorkItem,
    *,
    repository: ReviewRepository,
    scope: TenantScope,
    identity: SQLiteIdentityService | None,
    review_names: dict[str, str],
    users: dict[str, IdentityUser | None],
) -> WorkItemResponse:
    if item.review_id not in review_names:
        review = _review_for_org(repository, item.review_id, scope)
        review_names[item.review_id] = review.document_name if review is not None else "审阅记录"
    assignee = _user(identity, item.assignee_user_id, users)
    kind = item.kind.value if hasattr(item.kind, "value") else str(item.kind)
    return WorkItemResponse(
        work_item_id=item.id,
        review_id=item.review_id,
        kind=kind,
        source_id=item.source_id,
        source_ordinal=item.source_ordinal,
        title=item.title,
        source_payload=item.source_payload,
        risk_level=item.risk_level,
        status=item.status,
        assignee_user_id=item.assignee_user_id,
        assignee_display_name=assignee.display_name if assignee else None,
        assignee_email=assignee.email if assignee else None,
        due_at=item.due_at,
        note=item.note,
        state_version=item.state_version,
        created_at=item.created_at,
        updated_at=item.updated_at,
        completed_at=item.completed_at,
        document_name=review_names[item.review_id],
    )


def _work_item_responses(
    items: Sequence[StoredWorkItem],
    *,
    repository: ReviewRepository,
    scope: TenantScope,
    identity: SQLiteIdentityService | None,
) -> list[WorkItemResponse]:
    review_names: dict[str, str] = {}
    users: dict[str, IdentityUser | None] = {}
    return [
        _work_item_response(
            item,
            repository=repository,
            scope=scope,
            identity=identity,
            review_names=review_names,
            users=users,
        )
        for item in items
    ]


def _audit(
    identity: SQLiteIdentityService | None,
    request: Request,
    scope: TenantScope,
    *,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    if identity is None or not scope.authenticated:
        return
    identity.record_audit(
        org_id=scope.org_id,
        actor_user_id=scope.user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        details=details,
    )


def _validate_assignee(
    identity: SQLiteIdentityService | None,
    scope: TenantScope,
    assignee_user_id: str | None,
) -> None:
    if assignee_user_id is None:
        return
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="成员目录暂时不可用",
        )
    assignee = identity.get_user(assignee_user_id)
    if (
        assignee is None
        or assignee.org_id != scope.org_id
        or assignee.status is not UserStatus.ACTIVE
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="负责人不可用")
    if assignee.role is UserRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只读成员不能被指派处置任务",
        )


def _handle_domain_error(exc: Exception) -> Never:
    if isinstance(exc, (WorkItemNotFound, ReviewNotFound)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, StateConflict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="内容已被其他成员更新，请刷新后重试",
        ) from exc
    if isinstance(exc, ApprovalBlocked):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, AssignmentError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, (InvalidTransition, InvalidDueAt, ValueError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get(
    "/operations/summary",
    response_model=OperationsSummaryResponse,
    summary="Operational work queue summary",
)
async def operations_summary(
    request: Request,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> OperationsSummaryResponse:
    operations = _operations(repository)
    counts = operations.operations_summary(org_id=scope.org_id, user_id=scope.user_id)
    return OperationsSummaryResponse(
        my_open=int(counts.get("assigned_to_me", 0)),
        overdue=int(counts.get("overdue", 0)),
        high_risk_open=int(counts.get("open_high_risk", 0)),
        pending_approvals=int(counts.get("pending_approvals", 0)),
        completed_this_week=int(counts.get("completed_this_week", 0)),
    )


@router.get(
    "/work-items",
    response_model=WorkItemListResponse,
    summary="List operational work items",
)
async def list_work_items(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    kind: str | None = Query(default=None, max_length=32),
    work_status: str | None = Query(default=None, alias="status", max_length=32),
    assignee: str | None = Query(default=None, max_length=128),
    overdue: bool = Query(default=False),
    risk_level: str | None = Query(default=None, max_length=32),
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> WorkItemListResponse:
    operations = _operations(repository)
    assignee_filter: Any = UNSET
    if assignee == "me":
        if not scope.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前模式没有登录成员，不能使用“我的待办”筛选",
            )
        assignee_filter = scope.user_id
    elif assignee == "unassigned":
        assignee_filter = None
    elif assignee:
        assignee_filter = assignee
    try:
        items, total = operations.list_work_items(
            org_id=scope.org_id,
            page=page,
            page_size=page_size,
            kind=kind,
            status=work_status,
            assignee_user_id=assignee_filter,
            overdue=overdue,
            risk_level=risk_level,
        )
    except Exception as exc:  # repository validates enum-like filters
        _handle_domain_error(exc)
    return WorkItemListResponse(
        items=_work_item_responses(
            items,
            repository=repository,
            scope=scope,
            identity=_identity(request),
        ),
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get(
    "/work-items/{work_item_id}",
    response_model=WorkItemResponse,
    summary="Get one operational work item",
)
async def get_work_item(
    work_item_id: str,
    request: Request,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> WorkItemResponse:
    operations = _operations(repository)
    item = operations.get_work_item(work_item_id, org_id=scope.org_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作项不存在")
    return _work_item_responses(
        [item], repository=repository, scope=scope, identity=_identity(request)
    )[0]


@router.get(
    "/reviews/{review_id}/work-items",
    response_model=ReviewWorkItemsResponse,
    summary="List work items for a review",
)
async def list_review_work_items(
    review_id: str,
    request: Request,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> ReviewWorkItemsResponse:
    operations = _operations(repository)
    if _review_for_org(repository, review_id, scope) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审阅记录不存在")
    items = operations.list_review_work_items(review_id, org_id=scope.org_id)
    return ReviewWorkItemsResponse(
        review_id=review_id,
        items=_work_item_responses(
            items,
            repository=repository,
            scope=scope,
            identity=_identity(request),
        ),
    )


@router.get(
    "/work-items/{work_item_id}/events",
    response_model=WorkItemEventsResponse,
    summary="List the work-item activity timeline",
)
async def list_work_item_events(
    work_item_id: str,
    request: Request,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> WorkItemEventsResponse:
    operations = _operations(repository)
    item = operations.get_work_item(work_item_id, org_id=scope.org_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作项不存在")
    events: Sequence[StoredWorkItemEvent] = operations.list_work_item_events(
        work_item_id, org_id=scope.org_id
    )
    identity = _identity(request)
    users: dict[str, IdentityUser | None] = {}
    return WorkItemEventsResponse(
        work_item_id=work_item_id,
        items=[
            WorkItemEventResponse(
                event_id=event.id,
                work_item_id=event.work_item_id,
                actor_user_id=event.actor_user_id,
                actor_display_name=(
                    actor.display_name
                    if (actor := _user(identity, event.actor_user_id, users)) is not None
                    else None
                ),
                action=event.action,
                from_status=event.from_status,
                to_status=event.to_status,
                changes=event.changes,
                note=event.note,
                state_version=event.state_version,
                created_at=event.created_at,
            )
            for event in events
        ],
    )


@router.patch(
    "/work-items/{work_item_id}",
    response_model=WorkItemResponse,
    summary="Update and progress a work item",
)
async def update_work_item(
    work_item_id: str,
    patch: WorkItemUpdateRequest,
    request: Request,
    scope: TenantScope = Depends(require_roles(*_MUTATING_ROLES)),
    repository: ReviewRepository = Depends(get_repository),
) -> WorkItemResponse:
    operations = _operations(repository)
    current = operations.get_work_item(work_item_id, org_id=scope.org_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作项不存在")
    fields = patch.model_fields_set
    requested_assignee: Any = patch.assignee_user_id if "assignee_user_id" in fields else UNSET
    if requested_assignee is not UNSET:
        _validate_assignee(_identity(request), scope, requested_assignee)

    if scope.role is UserRole.REVIEWER:
        if requested_assignee is not UNSET and requested_assignee not in {None, scope.user_id}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="审阅员只能把工作项领取给自己",
            )
        effective_assignee = (
            requested_assignee if requested_assignee is not UNSET else current.assignee_user_id
        )
        if effective_assignee != scope.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="请先领取工作项，再更新处置状态",
            )
        if patch.status in _PRIVILEGED_WORK_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="接受风险或豁免义务需要管理员确认",
            )

    try:
        updated = operations.update_work_item(
            work_item_id,
            org_id=scope.org_id,
            expected_version=patch.expected_version,
            status=patch.status if "status" in fields else UNSET,
            assignee_user_id=requested_assignee,
            due_at=patch.due_at if "due_at" in fields else UNSET,
            note=patch.note if "note" in fields else UNSET,
            actor_user_id=scope.user_id,
        )
    except Exception as exc:
        _handle_domain_error(exc)

    identity = _identity(request)
    _audit(
        identity,
        request,
        scope,
        action="work_item.updated",
        resource_type="work_item",
        resource_id=work_item_id,
        details={"kind": str(updated.kind), "status": updated.status},
    )
    return _work_item_responses([updated], repository=repository, scope=scope, identity=identity)[0]


@router.patch(
    "/reviews/{review_id}/decision",
    response_model=ReviewDecisionResponse,
    summary="Transition a review decision",
)
async def transition_review_decision(
    review_id: str,
    patch: ReviewDecisionRequest,
    request: Request,
    scope: TenantScope = Depends(require_roles(*_MUTATING_ROLES)),
    repository: ReviewRepository = Depends(get_repository),
) -> ReviewDecisionResponse:
    operations = _operations(repository)
    current = _review_for_org(repository, review_id, scope)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审阅记录不存在")
    target_status = patch.status.casefold()
    if scope.role is UserRole.REVIEWER and target_status != "in_review":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="审阅员可以提交或重新提交审批，最终决定需要管理员确认",
        )
    if (
        scope.role is UserRole.REVIEWER
        and current.decision_status not in _REVIEWER_SUBMITTABLE_DECISIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="审阅员只能提交草稿或重新提交已驳回的审阅；已批准审阅只能由管理员重新打开",
        )
    if target_status in _FINAL_DECISIONS and scope.role not in _PRIVILEGED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="最终审批需要管理员确认",
        )
    try:
        updated = operations.transition_review_decision(
            review_id,
            org_id=scope.org_id,
            expected_version=patch.expected_version,
            target_status=target_status,
            note=patch.note,
            actor_user_id=scope.user_id,
        )
    except Exception as exc:
        _handle_domain_error(exc)

    identity = _identity(request)
    _audit(
        identity,
        request,
        scope,
        action="review.decision_changed",
        resource_type="review",
        resource_id=review_id,
        details={"from": current.decision_status, "to": updated.decision_status},
    )
    return ReviewDecisionResponse(
        review_id=updated.id,
        previous_status=current.decision_status,
        decision_status=updated.decision_status,
        state_version=updated.state_version,
        updated_at=updated.updated_at,
    )


__all__ = ["router"]
