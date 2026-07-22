"""Analytics aggregation endpoints for ContractGuard."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from contract_guard.api.analytics_schemas import (
    AnalyticsOverview,
    CategoryBreakdown,
    EfficiencyMetrics,
    RiskTrendPoint,
    WorkloadItem,
)
from contract_guard.api.dependencies import (
    TenantScope,
    get_repository,
    get_tenant_scope,
)
from contract_guard.services.storage import SQLiteReviewRepository

router = APIRouter(tags=["analytics"], prefix="/analytics")

_COMPLETED_DECISIONS = ("approved", "rejected")
_OPEN_WORK_STATUSES = ("pending", "in_progress")
_COMPLETED_WORK_STATUSES = ("resolved", "accepted", "completed", "waived")
_RISK_LEVELS = ("critical", "high", "medium", "low", "info")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _get_connection(repository: SQLiteReviewRepository) -> Any:
    """Access the underlying SQLite connection from the repository."""
    conn = getattr(repository, "_connection", None)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service unavailable",
        )
    return conn


def _get_lock(repository: SQLiteReviewRepository) -> Any:
    """Access the repository's threading lock."""
    return getattr(repository, "_lock", None)


def _parse_report_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
        return decoded if isinstance(decoded, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _extract_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    findings = report.get("findings", [])
    if isinstance(findings, dict):
        findings = findings.get("items", [])
    if not isinstance(findings, list):
        return []
    return [f for f in findings if isinstance(f, dict)]


@router.get("/overview", response_model=AnalyticsOverview, summary="Analytics overview")
async def analytics_overview(
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> AnalyticsOverview:
    conn = _get_connection(repository)
    lock = _get_lock(repository)
    org_id = scope.org_id
    now = _utc_now()
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()

    with lock:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_reviews,
                COALESCE(
                    AVG(
                        CASE WHEN status = 'completed'
                        THEN (julianday(updated_at) - julianday(created_at)) * 86400.0
                        END
                    ), 0
                ) AS avg_review_seconds,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0)
                    AS completed_reviews,
                COALESCE(SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END), 0)
                    AS reviews_this_week,
                COALESCE(SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END), 0)
                    AS reviews_this_month
            FROM reviews
            WHERE org_id = ? AND deleted_at IS NULL
            """,
            (week_ago, month_ago, org_id),
        ).fetchone()

        open_risks = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM work_items
                JOIN reviews ON reviews.id = work_items.review_id
                WHERE work_items.org_id = ? AND reviews.org_id = ?
                  AND reviews.deleted_at IS NULL
                  AND work_items.kind = 'finding'
                  AND work_items.completed_at IS NULL
                """,
                (org_id, org_id),
            ).fetchone()[0]
        )

    total_reviews = int(row["total_reviews"])
    completed_reviews = int(row["completed_reviews"])
    completion_rate = (completed_reviews / total_reviews * 100.0) if total_reviews > 0 else 0.0

    return AnalyticsOverview(
        total_reviews=total_reviews,
        avg_review_seconds=round(float(row["avg_review_seconds"]), 2),
        open_risks=open_risks,
        completion_rate=round(completion_rate, 2),
        reviews_this_week=int(row["reviews_this_week"]),
        reviews_this_month=int(row["reviews_this_month"]),
    )


@router.get(
    "/risk-trends",
    response_model=list[RiskTrendPoint],
    summary="Risk level trends over time",
)
async def risk_trends(
    days: int = Query(default=30, ge=1, le=365),
    period: str = Query(default="day", pattern="^(day|week)$"),
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> list[RiskTrendPoint]:
    conn = _get_connection(repository)
    lock = _get_lock(repository)
    org_id = scope.org_id
    now = _utc_now()
    since = (now - timedelta(days=days)).isoformat()

    with lock:
        rows = conn.execute(
            """
            SELECT report_json, created_at FROM reviews
            WHERE org_id = ? AND deleted_at IS NULL
              AND status = 'completed' AND created_at >= ?
            ORDER BY created_at ASC
            """,
            (org_id, since),
        ).fetchall()

    buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    )

    for row in rows:
        report = _parse_report_json(row["report_json"])
        findings = _extract_findings(report)
        created_at_str = str(row["created_at"])
        try:
            created_dt = datetime.fromisoformat(created_at_str)
        except (ValueError, TypeError):
            continue

        if period == "week":
            iso_cal = created_dt.isocalendar()
            bucket_key = f"{iso_cal[0]}-W{iso_cal[1]:02d}"
        else:
            bucket_key = created_dt.strftime("%Y-%m-%d")

        for finding in findings:
            risk_level = str(finding.get("risk_level", "info")).lower().strip()
            if risk_level not in _RISK_LEVELS:
                risk_level = "info"
            buckets[bucket_key][risk_level] += 1

    result = [
        RiskTrendPoint(
            date=date_key,
            critical=counts["critical"],
            high=counts["high"],
            medium=counts["medium"],
            low=counts["low"],
            info=counts["info"],
        )
        for date_key, counts in sorted(buckets.items())
    ]
    return result


@router.get(
    "/efficiency",
    response_model=EfficiencyMetrics,
    summary="Review efficiency metrics",
)
async def efficiency_metrics(
    days: int = Query(default=90, ge=1, le=365),
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> EfficiencyMetrics:
    conn = _get_connection(repository)
    lock = _get_lock(repository)
    org_id = scope.org_id
    now = _utc_now()
    since = (now - timedelta(days=days)).isoformat()

    with lock:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_reviews,
                COALESCE(SUM(CASE
                    WHEN decision_status IN ('approved', 'rejected')
                         OR status = 'completed'
                    THEN 1 ELSE 0 END), 0) AS completed_reviews,
                COALESCE(
                    AVG(
                        CASE WHEN decision_status IN ('approved', 'rejected')
                                  OR status = 'completed'
                        THEN (julianday(updated_at) - julianday(created_at)) * 86400.0
                        END
                    ), 0
                ) AS avg_review_seconds
            FROM reviews
            WHERE org_id = ? AND deleted_at IS NULL AND created_at >= ?
            """,
            (org_id, since),
        ).fetchone()

    total_reviews = int(row["total_reviews"])
    completed_reviews = int(row["completed_reviews"])
    completion_rate = (completed_reviews / total_reviews * 100.0) if total_reviews > 0 else 0.0

    return EfficiencyMetrics(
        avg_review_seconds=round(float(row["avg_review_seconds"]), 2),
        total_reviews=total_reviews,
        completed_reviews=completed_reviews,
        completion_rate=round(completion_rate, 2),
        period_days=days,
    )


@router.get(
    "/workload",
    response_model=list[WorkloadItem],
    summary="Workload distribution by assignee",
)
async def workload_distribution(
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> list[WorkloadItem]:
    conn = _get_connection(repository)
    lock = _get_lock(repository)
    org_id = scope.org_id
    now_iso = _utc_now().isoformat()

    with lock:
        rows = conn.execute(
            """
            SELECT
                COALESCE(users.display_name, work_items.assignee_user_id) AS assignee_name,
                COALESCE(SUM(CASE
                    WHEN work_items.status IN ('pending', 'in_progress')
                    THEN 1 ELSE 0 END), 0) AS open_count,
                COALESCE(SUM(CASE
                    WHEN work_items.status IN ('resolved', 'accepted', 'completed', 'waived')
                    THEN 1 ELSE 0 END), 0) AS completed_count,
                COALESCE(SUM(CASE
                    WHEN work_items.due_at IS NOT NULL
                         AND work_items.due_at < ?
                         AND work_items.completed_at IS NULL
                    THEN 1 ELSE 0 END), 0) AS overdue_count
            FROM work_items
            JOIN reviews ON reviews.id = work_items.review_id
            LEFT JOIN users ON users.id = work_items.assignee_user_id
                AND users.org_id = work_items.org_id
            WHERE work_items.org_id = ? AND reviews.org_id = ?
              AND reviews.deleted_at IS NULL
              AND work_items.assignee_user_id IS NOT NULL
            GROUP BY work_items.assignee_user_id
            ORDER BY open_count DESC, overdue_count DESC
            """,
            (now_iso, org_id, org_id),
        ).fetchall()

    return [
        WorkloadItem(
            assignee_name=str(row["assignee_name"] or "Unassigned"),
            open_count=int(row["open_count"]),
            completed_count=int(row["completed_count"]),
            overdue_count=int(row["overdue_count"]),
        )
        for row in rows
    ]


@router.get(
    "/risk-categories",
    response_model=list[CategoryBreakdown],
    summary="Risk findings grouped by category",
)
async def risk_categories(
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> list[CategoryBreakdown]:
    conn = _get_connection(repository)
    lock = _get_lock(repository)
    org_id = scope.org_id

    with lock:
        rows = conn.execute(
            """
            SELECT report_json FROM reviews
            WHERE org_id = ? AND deleted_at IS NULL AND status = 'completed'
            """,
            (org_id,),
        ).fetchall()

    category_counts: dict[str, int] = defaultdict(int)
    total_findings = 0

    for row in rows:
        report = _parse_report_json(row["report_json"])
        findings = _extract_findings(report)
        for finding in findings:
            category = (
                finding.get("category")
                or finding.get("rule_id")
                or "uncategorized"
            )
            category = str(category).strip() or "uncategorized"
            category_counts[category] += 1
            total_findings += 1

    if total_findings == 0:
        return []

    result = [
        CategoryBreakdown(
            category=category,
            count=count,
            percentage=round(count / total_findings * 100.0, 2),
        )
        for category, count in sorted(
            category_counts.items(), key=lambda item: item[1], reverse=True
        )
    ]
    return result


__all__ = ["router"]
