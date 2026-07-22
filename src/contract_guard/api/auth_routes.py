"""Authentication, organization member, and audit endpoints."""

from __future__ import annotations

import hashlib
import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from contract_guard.api.auth_schemas import (
    AuditListResponse,
    AuditRecordResponse,
    AuthSessionResponse,
    AuthStatusResponse,
    ChangePasswordRequest,
    CreateUserRequest,
    CurrentUserResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)
from contract_guard.api.dependencies import (
    TenantScope,
    get_current_user,
    get_identity_service,
    require_authenticated_roles,
)
from contract_guard.config import Settings
from contract_guard.services.identity import (
    AuthenticatedSession,
    AuthenticationFailed,
    IdentityConflict,
    IdentityUser,
    PermissionDenied,
    RegistrationClosed,
    SQLiteIdentityService,
    UserRole,
)

router = APIRouter(tags=["identity"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _user_response(user: IdentityUser) -> UserResponse:
    return UserResponse(
        user_id=user.id,
        org_id=user.org_id,
        organization_name=user.organization_name,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _session_response(session: AuthenticatedSession) -> AuthSessionResponse:
    return AuthSessionResponse(
        user=_user_response(session.user),
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_at=session.access_expires_at,
        refresh_expires_at=session.refresh_expires_at,
    )


def _set_session_cookies(
    response: Response,
    session: AuthenticatedSession,
    settings: Settings,
) -> None:
    response.set_cookie(
        "contractguard_access",
        session.access_token,
        max_age=settings.auth_access_ttl_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        "contractguard_refresh",
        session.refresh_token,
        max_age=settings.auth_refresh_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie("contractguard_access", path="/", httponly=True, samesite="strict")
    response.delete_cookie("contractguard_refresh", path="/", httponly=True, samesite="strict")


@router.get("/auth/status", response_model=AuthStatusResponse, summary="Get sign-in status")
async def auth_status(
    request: Request,
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> AuthStatusResponse:
    settings: Settings = request.app.state.settings
    return AuthStatusResponse(
        auth_required=settings.auth_required,
        bootstrap_required=identity.bootstrap_required(),
        registration_enabled=settings.registration_enabled or identity.bootstrap_required(),
    )


@router.post(
    "/auth/register",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization and owner account",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> AuthSessionResponse:
    try:
        session = identity.register_organization(
            organization_name=payload.organization_name,
            display_name=payload.display_name,
            email=payload.email,
            password=payload.password,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except RegistrationClosed as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except IdentityConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    settings: Settings = request.app.state.settings
    _set_session_cookies(response, session, settings)
    identity.record_audit(
        org_id=session.user.org_id,
        actor_user_id=session.user.id,
        action="identity.organization_registered",
        resource_type="organization",
        resource_id=session.user.org_id,
        request_id=_request_id(request),
        ip_address=_client_ip(request),
    )
    return _session_response(session)


@router.post("/auth/login", response_model=AuthSessionResponse, summary="Sign in")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> AuthSessionResponse:
    limiter = request.app.state.login_rate_limiter
    rate_key = hashlib.sha256(
        f"{_client_ip(request) or 'unknown'}|{payload.email.casefold()}".encode()
    ).hexdigest()
    retry_after = limiter.retry_after(rate_key)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录尝试过多，请稍后再试",
            headers={"Retry-After": str(retry_after)},
        )
    try:
        session = identity.login(
            email=payload.email,
            password=payload.password,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except AuthenticationFailed as exc:
        limiter.record_failure(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    limiter.reset(rate_key)
    settings: Settings = request.app.state.settings
    _set_session_cookies(response, session, settings)
    identity.record_audit(
        org_id=session.user.org_id,
        actor_user_id=session.user.id,
        action="identity.login",
        resource_type="auth_session",
        resource_id=session.session_id,
        request_id=_request_id(request),
        ip_address=_client_ip(request),
    )
    return _session_response(session)


@router.post("/auth/refresh", response_model=AuthSessionResponse, summary="Refresh a session")
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> AuthSessionResponse:
    token = (payload.refresh_token if payload else None) or request.cookies.get(
        "contractguard_refresh", ""
    )
    try:
        session = identity.refresh(
            token,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except AuthenticationFailed as exc:
        _clear_session_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    settings: Settings = request.app.state.settings
    _set_session_cookies(response, session, settings)
    return _session_response(session)


@router.post("/auth/logout", response_model=MessageResponse, summary="Sign out")
async def logout(
    request: Request,
    response: Response,
    scope: TenantScope = Depends(require_authenticated_roles(*tuple(UserRole))),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> MessageResponse:
    identity.revoke(getattr(request.state, "access_token", ""))
    identity.record_audit(
        org_id=scope.org_id,
        actor_user_id=scope.user_id,
        action="identity.logout",
        resource_type="auth_session",
        resource_id=getattr(request.state, "auth_session_id", None),
        request_id=_request_id(request),
        ip_address=_client_ip(request),
    )
    _clear_session_cookies(response)
    return MessageResponse(message="已安全退出")


@router.get("/auth/me", response_model=CurrentUserResponse, summary="Get current user")
async def me(user: IdentityUser = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(user=_user_response(user))


@router.post(
    "/auth/change-password",
    response_model=MessageResponse,
    summary="Change the current password",
)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    user: IdentityUser = Depends(get_current_user),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> MessageResponse:
    try:
        identity.change_password(
            user.id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except AuthenticationFailed as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    identity.record_audit(
        org_id=user.org_id,
        actor_user_id=user.id,
        action="identity.password_changed",
        resource_type="user",
        resource_id=user.id,
        request_id=_request_id(request),
        ip_address=_client_ip(request),
    )
    _clear_session_cookies(response)
    return MessageResponse(message="密码已修改，请重新登录")


@router.get("/users", response_model=UserListResponse, summary="List organization members")
async def list_users(
    scope: TenantScope = Depends(require_authenticated_roles(UserRole.OWNER, UserRole.ADMIN)),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> UserListResponse:
    users = identity.list_users(scope.org_id)
    return UserListResponse(items=[_user_response(user) for user in users], total=len(users))


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization member",
)
async def create_user(
    payload: CreateUserRequest,
    request: Request,
    scope: TenantScope = Depends(require_authenticated_roles(UserRole.OWNER, UserRole.ADMIN)),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> UserResponse:
    try:
        user = identity.create_user(
            org_id=scope.org_id,
            email=payload.email,
            display_name=payload.display_name,
            password=payload.password,
            role=payload.role,
        )
    except IdentityConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PermissionDenied as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    identity.record_audit(
        org_id=scope.org_id,
        actor_user_id=scope.user_id,
        action="identity.member_created",
        resource_type="user",
        resource_id=user.id,
        request_id=_request_id(request),
        ip_address=_client_ip(request),
        details={"role": user.role.value},
    )
    return _user_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse, summary="Update a member")
async def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    request: Request,
    scope: TenantScope = Depends(require_authenticated_roles(UserRole.OWNER, UserRole.ADMIN)),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> UserResponse:
    try:
        user = identity.update_user(
            org_id=scope.org_id,
            user_id=user_id,
            role=payload.role,
            status=payload.status,
            display_name=payload.display_name,
        )
    except PermissionDenied as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在")
    identity.record_audit(
        org_id=scope.org_id,
        actor_user_id=scope.user_id,
        action="identity.member_updated",
        resource_type="user",
        resource_id=user.id,
        request_id=_request_id(request),
        ip_address=_client_ip(request),
        details={"role": user.role.value, "status": user.status.value},
    )
    return _user_response(user)


@router.get("/audit-logs", response_model=AuditListResponse, summary="List audit records")
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    action: str | None = Query(default=None, max_length=120),
    scope: TenantScope = Depends(require_authenticated_roles(UserRole.OWNER, UserRole.ADMIN)),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> AuditListResponse:
    records, total = identity.list_audit(
        org_id=scope.org_id,
        page=page,
        page_size=page_size,
        action=action,
    )
    return AuditListResponse(
        items=[
            AuditRecordResponse(
                audit_id=item.id,
                actor_user_id=item.actor_user_id,
                action=item.action,
                resource_type=item.resource_type,
                resource_id=item.resource_id,
                outcome=item.outcome,
                request_id=item.request_id,
                details=item.details,
                created_at=item.created_at,
            )
            for item in records
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


__all__ = ["router"]
