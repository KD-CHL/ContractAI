"""Contract template and clause library endpoints for ContractGuard."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from contract_guard.api.dependencies import (
    TenantScope,
    get_repository,
    get_tenant_scope,
)
from contract_guard.api.template_schemas import (
    Clause,
    ClauseCreate,
    ClauseListResponse,
    ClauseUpdate,
    ContractTemplate,
    TemplateCreate,
    TemplateListResponse,
    TemplateUpdate,
)
from contract_guard.services.storage import SQLiteReviewRepository

router = APIRouter(tags=["templates"])


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _get_connection(repository: SQLiteReviewRepository) -> Any:
    """Access the underlying SQLite connection from the repository."""
    conn = getattr(repository, "_connection", None)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="模板服务暂时不可用",
        )
    return conn


def _get_lock(repository: SQLiteReviewRepository) -> Any:
    """Access the repository's threading lock."""
    return getattr(repository, "_lock", None)


def _template_from_row(row: Any) -> ContractTemplate:
    return ContractTemplate(
        id=str(row["id"]),
        org_id=str(row["org_id"]),
        name=str(row["name"]),
        description=str(row["description"] or ""),
        category=str(row["category"] or ""),
        content_text=str(row["content_text"] or ""),
        created_by_user_id=(str(row["created_by_user_id"]) if row["created_by_user_id"] else None),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _clause_from_row(row: Any) -> Clause:
    return Clause(
        id=str(row["id"]),
        org_id=str(row["org_id"]),
        title=str(row["title"]),
        content_text=str(row["content_text"]),
        category=str(row["category"] or ""),
        risk_level=(str(row["risk_level"]) if row["risk_level"] else None),
        risk_annotation=str(row["risk_annotation"] or ""),
        created_by_user_id=(str(row["created_by_user_id"]) if row["created_by_user_id"] else None),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


# ─── Templates ───────────────────────────────────────────────────────────────


@router.get(
    "/templates",
    response_model=TemplateListResponse,
    summary="List contract templates",
)
async def list_templates(
    category: str | None = Query(default=None, max_length=64),
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> TemplateListResponse:
    conn = _get_connection(repository)
    lock = _get_lock(repository)
    org_id = scope.org_id

    where = ["org_id = ?", "deleted_at IS NULL"]
    params: list[Any] = [org_id]
    if category:
        where.append("category = ?")
        params.append(category)
    if search:
        where.append("(name LIKE ? OR description LIKE ? OR content_text LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    where_sql = " AND ".join(where)

    with lock:
        total = int(
            conn.execute(
                f"SELECT COUNT(*) FROM contract_templates WHERE {where_sql}",
                params,
            ).fetchone()[0]
        )
        rows = conn.execute(
            f"""
            SELECT * FROM contract_templates
            WHERE {where_sql}
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()

    return TemplateListResponse(
        items=[_template_from_row(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/templates",
    response_model=ContractTemplate,
    status_code=status.HTTP_201_CREATED,
    summary="Create a contract template",
)
async def create_template(
    payload: TemplateCreate,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> ContractTemplate:
    conn = _get_connection(repository)
    lock = _get_lock(repository)
    now = _utc_now_iso()
    template_id = str(uuid4())

    with lock:
        conn.execute(
            """
            INSERT INTO contract_templates (
                id, org_id, name, description, category, content_text,
                created_by_user_id, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                template_id,
                scope.org_id,
                payload.name.strip(),
                payload.description,
                payload.category,
                payload.content_text,
                scope.user_id,
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM contract_templates WHERE id = ?",
            (template_id,),
        ).fetchone()

    return _template_from_row(row)


@router.get(
    "/templates/{template_id}",
    response_model=ContractTemplate,
    summary="Get one contract template",
)
async def get_template(
    template_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> ContractTemplate:
    conn = _get_connection(repository)
    lock = _get_lock(repository)

    with lock:
        row = conn.execute(
            """
            SELECT * FROM contract_templates
            WHERE id = ? AND org_id = ? AND deleted_at IS NULL
            """,
            (template_id, scope.org_id),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return _template_from_row(row)


@router.patch(
    "/templates/{template_id}",
    response_model=ContractTemplate,
    summary="Update a contract template",
)
async def update_template(
    template_id: str,
    payload: TemplateUpdate,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> ContractTemplate:
    conn = _get_connection(repository)
    lock = _get_lock(repository)

    updates: list[str] = []
    params: list[Any] = []
    if "name" in payload.model_fields_set and payload.name is not None:
        updates.append("name = ?")
        params.append(payload.name.strip())
    if "description" in payload.model_fields_set and payload.description is not None:
        updates.append("description = ?")
        params.append(payload.description)
    if "category" in payload.model_fields_set and payload.category is not None:
        updates.append("category = ?")
        params.append(payload.category)
    if "content_text" in payload.model_fields_set and payload.content_text is not None:
        updates.append("content_text = ?")
        params.append(payload.content_text)

    with lock:
        existing = conn.execute(
            """
            SELECT id FROM contract_templates
            WHERE id = ? AND org_id = ? AND deleted_at IS NULL
            """,
            (template_id, scope.org_id),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")

        if updates:
            updates.append("updated_at = ?")
            params.append(_utc_now_iso())
            params.extend([template_id, scope.org_id])
            conn.execute(
                f"""
                UPDATE contract_templates
                SET {", ".join(updates)}
                WHERE id = ? AND org_id = ? AND deleted_at IS NULL
                """,
                params,
            )
            conn.commit()

        row = conn.execute(
            "SELECT * FROM contract_templates WHERE id = ?",
            (template_id,),
        ).fetchone()

    return _template_from_row(row)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a contract template",
)
async def delete_template(
    template_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> None:
    conn = _get_connection(repository)
    lock = _get_lock(repository)

    with lock:
        cursor = conn.execute(
            """
            UPDATE contract_templates
            SET deleted_at = ?, updated_at = ?
            WHERE id = ? AND org_id = ? AND deleted_at IS NULL
            """,
            (_utc_now_iso(), _utc_now_iso(), template_id, scope.org_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")


# ─── Clauses ─────────────────────────────────────────────────────────────────


@router.get(
    "/clauses",
    response_model=ClauseListResponse,
    summary="List clause library entries",
)
async def list_clauses(
    category: str | None = Query(default=None, max_length=64),
    risk_level: str | None = Query(default=None, max_length=32),
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> ClauseListResponse:
    conn = _get_connection(repository)
    lock = _get_lock(repository)
    org_id = scope.org_id

    where = ["org_id = ?"]
    params: list[Any] = [org_id]
    if category:
        where.append("category = ?")
        params.append(category)
    if risk_level:
        where.append("risk_level = ?")
        params.append(risk_level)
    if search:
        where.append("(title LIKE ? OR content_text LIKE ? OR risk_annotation LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    where_sql = " AND ".join(where)

    with lock:
        total = int(
            conn.execute(
                f"SELECT COUNT(*) FROM clause_library WHERE {where_sql}",
                params,
            ).fetchone()[0]
        )
        rows = conn.execute(
            f"""
            SELECT * FROM clause_library
            WHERE {where_sql}
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()

    return ClauseListResponse(
        items=[_clause_from_row(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/clauses",
    response_model=Clause,
    status_code=status.HTTP_201_CREATED,
    summary="Create a clause library entry",
)
async def create_clause(
    payload: ClauseCreate,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> Clause:
    conn = _get_connection(repository)
    lock = _get_lock(repository)
    now = _utc_now_iso()
    clause_id = str(uuid4())

    with lock:
        conn.execute(
            """
            INSERT INTO clause_library (
                id, org_id, title, content_text, category, risk_level,
                risk_annotation, created_by_user_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clause_id,
                scope.org_id,
                payload.title.strip(),
                payload.content_text,
                payload.category,
                payload.risk_level,
                payload.risk_annotation,
                scope.user_id,
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM clause_library WHERE id = ?",
            (clause_id,),
        ).fetchone()

    return _clause_from_row(row)


@router.get(
    "/clauses/{clause_id}",
    response_model=Clause,
    summary="Get one clause library entry",
)
async def get_clause(
    clause_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> Clause:
    conn = _get_connection(repository)
    lock = _get_lock(repository)

    with lock:
        row = conn.execute(
            "SELECT * FROM clause_library WHERE id = ? AND org_id = ?",
            (clause_id, scope.org_id),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="条款不存在")
    return _clause_from_row(row)


@router.patch(
    "/clauses/{clause_id}",
    response_model=Clause,
    summary="Update a clause library entry",
)
async def update_clause(
    clause_id: str,
    payload: ClauseUpdate,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> Clause:
    conn = _get_connection(repository)
    lock = _get_lock(repository)

    updates: list[str] = []
    params: list[Any] = []
    if "title" in payload.model_fields_set and payload.title is not None:
        updates.append("title = ?")
        params.append(payload.title.strip())
    if "content_text" in payload.model_fields_set and payload.content_text is not None:
        updates.append("content_text = ?")
        params.append(payload.content_text)
    if "category" in payload.model_fields_set and payload.category is not None:
        updates.append("category = ?")
        params.append(payload.category)
    if "risk_level" in payload.model_fields_set:
        updates.append("risk_level = ?")
        params.append(payload.risk_level)
    if "risk_annotation" in payload.model_fields_set and payload.risk_annotation is not None:
        updates.append("risk_annotation = ?")
        params.append(payload.risk_annotation)

    with lock:
        existing = conn.execute(
            "SELECT id FROM clause_library WHERE id = ? AND org_id = ?",
            (clause_id, scope.org_id),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="条款不存在")

        if updates:
            updates.append("updated_at = ?")
            params.append(_utc_now_iso())
            params.extend([clause_id, scope.org_id])
            conn.execute(
                f"""
                UPDATE clause_library
                SET {", ".join(updates)}
                WHERE id = ? AND org_id = ?
                """,
                params,
            )
            conn.commit()

        row = conn.execute(
            "SELECT * FROM clause_library WHERE id = ?",
            (clause_id,),
        ).fetchone()

    return _clause_from_row(row)


@router.delete(
    "/clauses/{clause_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a clause library entry",
)
async def delete_clause(
    clause_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: SQLiteReviewRepository = Depends(get_repository),
) -> None:
    conn = _get_connection(repository)
    lock = _get_lock(repository)

    with lock:
        cursor = conn.execute(
            "DELETE FROM clause_library WHERE id = ? AND org_id = ?",
            (clause_id, scope.org_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="条款不存在")


__all__ = ["router"]
