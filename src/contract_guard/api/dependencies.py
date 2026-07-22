"""FastAPI dependency helpers for request scope and app services."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from contract_guard.config import Settings
from contract_guard.services.cache import ReviewCache
from contract_guard.services.documents import DocumentService
from contract_guard.services.events import EventBus
from contract_guard.services.identity import (
    AuthenticationFailed,
    IdentityUser,
    SQLiteIdentityService,
    UserRole,
)
from contract_guard.services.storage import ReviewRepository


@dataclass(frozen=True, slots=True)
class TenantScope:
    org_id: str
    session_id: str
    user_id: str | None = None
    role: UserRole = UserRole.OWNER
    authenticated: bool = False


def _scope_value(value: str | None, default: str, *, label: str) -> str:
    resolved = (value or default).strip()
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} cannot be empty",
        )
    if len(resolved) > 200 or any(ord(character) < 32 for character in resolved):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} is invalid",
        )
    return resolved


def get_tenant_scope(request: Request) -> TenantScope:
    settings: Settings = request.app.state.settings
    identity: SQLiteIdentityService | None = getattr(request.app.state, "identity", None)
    authorization = request.headers.get("authorization", "").strip()
    access_token = ""
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.casefold() != "bearer" or not value.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="登录凭据格式不正确",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = value.strip()
    else:
        access_token = request.cookies.get("contractguard_access", "").strip()

    if access_token:
        if identity is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="身份服务暂时不可用",
            )
        try:
            user, auth_session_id = identity.authenticate(access_token)
        except AuthenticationFailed as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        request.state.user = user
        request.state.auth_session_id = auth_session_id
        request.state.access_token = access_token
        return TenantScope(
            org_id=user.org_id,
            # A stable user scope lets a user recover reviews after signing in
            # from a new browser session while retaining legacy repository APIs.
            session_id=user.id,
            user_id=user.id,
            role=user.role,
            authenticated=True,
        )

    if settings.auth_required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    headers = request.headers if settings.legacy_tenant_headers_enabled else {}
    org_id = headers.get("x-org-id") or headers.get("x-organization-id")
    session_id = headers.get("x-session-id")
    return TenantScope(
        org_id=_scope_value(org_id, settings.default_org_id, label="X-Org-ID"),
        session_id=_scope_value(session_id, settings.default_session_id, label="X-Session-ID"),
    )


def get_identity_service(request: Request) -> SQLiteIdentityService:
    identity: SQLiteIdentityService | None = getattr(request.app.state, "identity", None)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="身份服务暂时不可用",
        )
    return identity


def get_current_user(
    request: Request,
    scope: TenantScope = Depends(get_tenant_scope),
) -> IdentityUser:
    user: IdentityUser | None = getattr(request.state, "user", None)
    if user is None or not scope.authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return user


def require_roles(*roles: UserRole) -> Callable[..., TenantScope]:
    allowed = frozenset(roles)

    def dependency(scope: TenantScope = Depends(get_tenant_scope)) -> TenantScope:
        # Legacy scope exists only when authentication is explicitly disabled;
        # it retains owner-equivalent behavior for tests and local migrations.
        if scope.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="你没有执行此操作的权限",
            )
        return scope

    return dependency


def require_authenticated_roles(*roles: UserRole) -> Callable[..., TenantScope]:
    """Require a real authenticated actor, never a legacy header scope."""

    allowed = frozenset(roles)

    def dependency(scope: TenantScope = Depends(get_tenant_scope)) -> TenantScope:
        if not scope.authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="请先登录",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if scope.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="你没有执行此操作的权限",
            )
        return scope

    return dependency


def get_repository(request: Request) -> ReviewRepository:
    return request.app.state.repository


def get_review_cache(request: Request) -> ReviewCache:
    return request.app.state.review_cache


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service


def get_event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus


def get_review_workflow(request: Request) -> Any:
    return request.app.state.review_workflow
