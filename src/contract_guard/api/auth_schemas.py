"""Typed schemas for local authentication, members, and audit records."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contract_guard.services.identity import UserRole, UserStatus


class AuthModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AuthStatusResponse(AuthModel):
    auth_required: bool
    bootstrap_required: bool
    registration_enabled: bool


class RegisterRequest(AuthModel):
    organization_name: str = Field(min_length=2, max_length=120)
    display_name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(AuthModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(AuthModel):
    refresh_token: str | None = Field(default=None, min_length=20, max_length=512)


class ChangePasswordRequest(AuthModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)

    @model_validator(mode="after")
    def password_must_change(self) -> ChangePasswordRequest:
        if self.current_password == self.new_password:
            raise ValueError("新密码不能与当前密码相同")
        return self


class UserResponse(AuthModel):
    user_id: str
    org_id: str
    organization_name: str
    email: str
    display_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime


class AuthSessionResponse(AuthModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    refresh_expires_at: datetime


class CurrentUserResponse(AuthModel):
    user: UserResponse


class MessageResponse(AuthModel):
    message: str


class CreateUserRequest(AuthModel):
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=12, max_length=256)
    role: UserRole = UserRole.REVIEWER


class UpdateUserRequest(AuthModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=80)
    role: UserRole | None = None
    status: UserStatus | None = None

    @model_validator(mode="after")
    def require_change(self) -> UpdateUserRequest:
        if self.display_name is None and self.role is None and self.status is None:
            raise ValueError("至少需要修改一个字段")
        return self


class UserListResponse(AuthModel):
    items: list[UserResponse]
    total: int = Field(ge=0)


class AuditRecordResponse(AuthModel):
    audit_id: str
    actor_user_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    outcome: str
    request_id: str | None = None
    details: dict[str, object]
    created_at: datetime


class AuditListResponse(AuthModel):
    items: list[AuditRecordResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)


__all__ = [
    "AuditListResponse",
    "AuditRecordResponse",
    "AuthSessionResponse",
    "AuthStatusResponse",
    "ChangePasswordRequest",
    "CreateUserRequest",
    "CurrentUserResponse",
    "LoginRequest",
    "MessageResponse",
    "RefreshRequest",
    "RegisterRequest",
    "UpdateUserRequest",
    "UserListResponse",
    "UserResponse",
]
