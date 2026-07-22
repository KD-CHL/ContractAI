"""Review history, dashboard, lifecycle, and export endpoints."""

from __future__ import annotations

import html
import math
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse

from contract_guard.api.dependencies import (
    TenantScope,
    get_identity_service,
    get_repository,
    get_tenant_scope,
    require_roles,
)
from contract_guard.api.schemas import (
    DashboardResponse,
    DeleteReviewResponse,
    ReviewListItem,
    ReviewListResponse,
)
from contract_guard.services.identity import SQLiteIdentityService, UserRole
from contract_guard.services.storage import ReviewRepository, StoredReview

router = APIRouter(tags=["workspace"])


def _can_manage_all(scope: TenantScope) -> bool:
    return not scope.authenticated or scope.role.can_view_all_reviews


def _can_manage_all_lifecycle(scope: TenantScope) -> bool:
    return not scope.authenticated or scope.role.can_manage_all_reviews


def _catalog(repository: ReviewRepository) -> Any:
    required = ("list_reviews", "get_review_for_actor", "review_statistics")
    if any(not callable(getattr(repository, name, None)) for name in required):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="审阅目录暂时不可用",
        )
    return repository


def _list_item(review: StoredReview) -> ReviewListItem:
    summary = review.report.get("summary", {})
    if not isinstance(summary, Mapping):
        summary = {}
    highest = summary.get("highest_risk_level")
    return ReviewListItem(
        review_id=review.id,
        created_by_user_id=review.created_by_user_id,
        status=review.status,
        decision_status=review.decision_status,
        contract_id=review.contract_id,
        document_name=review.document_name,
        media_type=review.media_type,
        total_findings=int(summary.get("total_findings") or 0),
        highest_risk=str(highest) if highest else None,
        created_at=review.created_at,
        updated_at=review.updated_at,
        deleted_at=review.deleted_at,
    )


def _find_review(
    repository: ReviewRepository,
    review_id: str,
    scope: TenantScope,
    *,
    include_deleted: bool = False,
) -> StoredReview | None:
    getter = getattr(repository, "get_review_for_actor", None)
    if scope.authenticated and callable(getter):
        return getter(
            review_id,
            org_id=scope.org_id,
            user_id=scope.user_id,
            can_manage_all=_can_manage_all(scope),
            include_deleted=include_deleted,
        )
    return repository.get_review(review_id, org_id=scope.org_id, session_id=scope.session_id)


def _audit(
    identity: SQLiteIdentityService,
    request: Request,
    scope: TenantScope,
    *,
    action: str,
    resource_id: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    if not scope.authenticated:
        return
    identity.record_audit(
        org_id=scope.org_id,
        actor_user_id=scope.user_id,
        action=action,
        resource_type="review",
        resource_id=resource_id,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        details=details,
    )


@router.get("/dashboard/summary", response_model=DashboardResponse, summary="Workspace summary")
async def dashboard_summary(
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> DashboardResponse:
    catalog = _catalog(repository)
    statistics = catalog.review_statistics(
        org_id=scope.org_id,
        user_id=scope.user_id,
        can_manage_all=_can_manage_all(scope),
    )
    recent, _ = catalog.list_reviews(
        org_id=scope.org_id,
        user_id=scope.user_id,
        can_manage_all=_can_manage_all(scope),
        page=1,
        page_size=5,
        sort="updated_desc",
    )
    return DashboardResponse(
        total_reviews=statistics["total"],
        completed_reviews=statistics["completed"],
        high_risk_reviews=statistics["high_risk"],
        failed_reviews=statistics["failed"],
        status_counts=statistics["status_counts"],
        recent_reviews=[_list_item(item) for item in recent],
    )


@router.get("/reviews", response_model=ReviewListResponse, summary="List review history")
async def list_reviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    q: str | None = Query(default=None, max_length=256),
    review_status: str | None = Query(default=None, alias="status", max_length=32),
    include_deleted: bool = Query(default=False),
    sort: str = Query(default="updated_desc", max_length=32),
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> ReviewListResponse:
    catalog = _catalog(repository)
    try:
        reviews, total = catalog.list_reviews(
            org_id=scope.org_id,
            user_id=scope.user_id,
            can_manage_all=_can_manage_all(scope),
            page=page,
            page_size=page_size,
            query=q,
            status=review_status,
            include_deleted=include_deleted,
            sort=sort,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ReviewListResponse(
        items=[_list_item(item) for item in reviews],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.delete(
    "/reviews/{review_id}",
    response_model=DeleteReviewResponse,
    summary="Move a review to trash",
)
async def delete_review(
    review_id: str,
    request: Request,
    scope: TenantScope = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.REVIEWER)),
    repository: ReviewRepository = Depends(get_repository),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> DeleteReviewResponse:
    catalog = _catalog(repository)
    deleted = catalog.soft_delete_review(
        review_id,
        org_id=scope.org_id,
        user_id=scope.user_id,
        can_manage_all=_can_manage_all_lifecycle(scope),
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审阅记录不存在")
    _audit(identity, request, scope, action="review.deleted", resource_id=review_id)
    return DeleteReviewResponse(review_id=review_id, deleted=True, message="已移到回收站")


@router.post(
    "/reviews/{review_id}/restore",
    response_model=DeleteReviewResponse,
    summary="Restore a deleted review",
)
async def restore_review(
    review_id: str,
    request: Request,
    scope: TenantScope = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.REVIEWER)),
    repository: ReviewRepository = Depends(get_repository),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> DeleteReviewResponse:
    catalog = _catalog(repository)
    restored = catalog.restore_review(
        review_id,
        org_id=scope.org_id,
        user_id=scope.user_id,
        can_manage_all=_can_manage_all_lifecycle(scope),
    )
    if not restored:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回收站中没有这条记录")
    _audit(identity, request, scope, action="review.restored", resource_id=review_id)
    return DeleteReviewResponse(review_id=review_id, deleted=False, message="审阅记录已恢复")


@router.get("/reviews/{review_id}/export", summary="Export a stored review")
async def export_review(
    review_id: str,
    request: Request,
    export_format: str = Query(default="html", alias="format", pattern="^(html|json)$"),
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> Response:
    review = _find_review(repository, review_id, scope)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审阅记录不存在")
    _audit(
        identity,
        request,
        scope,
        action="review.exported",
        resource_id=review_id,
        details={"format": export_format},
    )
    if export_format == "json":
        response = JSONResponse(
            {
                "review_id": review.id,
                "contract_id": review.contract_id,
                "document_name": review.document_name,
                "status": review.status,
                "created_at": review.created_at.isoformat(),
                "updated_at": review.updated_at.isoformat(),
                "report": review.report,
            }
        )
        response.headers["Content-Disposition"] = (
            f'attachment; filename="contractguard-{review.id}.json"'
        )
        return response
    return _html_export(review)


def _html_export(review: StoredReview) -> HTMLResponse:
    report = review.report
    raw_findings = report.get("findings", [])
    findings: Sequence[Any] = raw_findings if isinstance(raw_findings, list) else []
    rows: list[str] = []
    for item in findings:
        if not isinstance(item, Mapping):
            continue
        evidence = item.get("evidence", [])
        quote = ""
        if isinstance(evidence, list) and evidence and isinstance(evidence[0], Mapping):
            quote = str(evidence[0].get("quote") or "")
        rows.append(
            "<article>"
            f"<p class='risk'>{html.escape(str(item.get('risk_level') or 'info'))}</p>"
            f"<h2>{html.escape(str(item.get('title') or '风险提示'))}</h2>"
            f"<p>{html.escape(str(item.get('description') or ''))}</p>"
            f"<blockquote>{html.escape(quote)}</blockquote>"
            f"<p><strong>建议：</strong>{html.escape(str(item.get('recommendation') or ''))}</p>"
            "</article>"
        )
    body = "".join(rows) or "<p>本次没有生成具备原文证据的风险提示。</p>"
    document_name = html.escape(review.document_name)
    updated_at = html.escape(review.updated_at.isoformat())
    review_id = html.escape(review.id)
    disclaimer = html.escape(str(report.get("disclaimer") or "本报告不构成法律意见。"))
    styles = "".join(
        (
            'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;',
            "color:#172033;max-width:860px;margin:48px auto;padding:0 24px;line-height:1.7}",
            "header{border-bottom:2px solid #172033;margin-bottom:32px}",
            "article{break-inside:avoid;border-bottom:1px solid #dce2ea;padding:20px 0}",
            ".risk{font-weight:700;text-transform:uppercase;color:#9a3412}",
            "blockquote{margin:12px 0;padding:12px 16px;background:#f3f6fa;",
            "border-left:4px solid #5267d8}",
            "small{color:#5f6b7c}@media print{body{margin:0;max-width:none}}",
        )
    )
    content = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{document_name} · ContractGuard 审阅报告</title>
<style>{styles}</style></head><body>
<header><p>ContractGuard · 可追溯合同预审</p><h1>{document_name}</h1>
<p>审阅时间：{updated_at} · 记录编号：{review_id}</p></header>
{body}<footer><small>{disclaimer}</small></footer>
</body></html>"""
    response = HTMLResponse(content)
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; img-src data:; frame-ancestors 'none'"
    )
    response.headers["Content-Disposition"] = f'inline; filename="contractguard-{review.id}.html"'
    return response


__all__ = ["router"]
