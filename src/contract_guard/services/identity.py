"""Local identity, session, RBAC, and audit persistence.

The built-in implementation deliberately uses opaque random session tokens.
Only SHA-256 token digests are persisted, while passwords use salted scrypt.
It is suitable for the single-node SQLite deployment and keeps the public API
independent from a particular external identity provider.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _opaque_token() -> str:
    return secrets.token_urlsafe(48)


def _hash_metadata(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def normalize_email(value: str) -> str:
    normalized = value.strip().casefold()
    if len(normalized) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
        raise ValueError("请输入有效的邮箱地址")
    return normalized


def validate_password(value: str) -> None:
    if len(value) < 12:
        raise ValueError("密码至少需要 12 位")
    if len(value) > 256:
        raise ValueError("密码不能超过 256 位")
    categories = sum(
        (
            any(character.islower() for character in value),
            any(character.isupper() for character in value),
            any(character.isdigit() for character in value),
            any(not character.isalnum() for character in value),
        )
    )
    if categories < 3:
        raise ValueError("密码需包含大写字母、小写字母、数字或符号中的至少三类")


def hash_password(value: str) -> str:
    validate_password(value)
    salt = secrets.token_bytes(16)
    n, r, p = 2**14, 8, 1
    digest = hashlib.scrypt(value.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32)
    return "$".join(
        (
            "scrypt",
            str(n),
            str(r),
            str(p),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_password(value: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.scrypt(
            value.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


class UserRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    REVIEWER = "reviewer"
    VIEWER = "viewer"

    @property
    def can_manage_members(self) -> bool:
        return self in {self.OWNER, self.ADMIN}

    @property
    def can_view_all_reviews(self) -> bool:
        # Reviews are organization records.  Viewer is therefore a genuinely
        # read-only organization role instead of a user who sees an empty
        # workspace because they are not allowed to create records.
        return True

    @property
    def can_manage_all_reviews(self) -> bool:
        return self in {self.OWNER, self.ADMIN}


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class IdentityUser:
    id: str
    org_id: str
    organization_name: str
    email: str
    display_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user: IdentityUser
    session_id: str
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuditRecord:
    id: str
    org_id: str
    actor_user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    outcome: str
    request_id: str | None
    details: dict[str, Any]
    created_at: datetime


class IdentityError(RuntimeError):
    """Base class for safe, user-facing identity failures."""


class AuthenticationFailed(IdentityError):
    pass


class RegistrationClosed(IdentityError):
    pass


class IdentityConflict(IdentityError):
    pass


class PermissionDenied(IdentityError):
    pass


class SQLiteIdentityService:
    """Identity service backed by the application's migrated SQLite database."""

    def __init__(
        self,
        path: str | Path,
        *,
        access_ttl_minutes: int = 480,
        refresh_ttl_days: int = 30,
        registration_enabled: bool = True,
    ) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            self.path = str(Path(self.path).expanduser().resolve())
        self.access_ttl = timedelta(minutes=access_ttl_minutes)
        self.refresh_ttl = timedelta(days=refresh_ttl_days)
        self.registration_enabled = registration_enabled
        self._lock = RLock()
        self._connection = sqlite3.connect(
            self.path,
            check_same_thread=False,
            isolation_level=None,
            timeout=10,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 10000")

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def bootstrap_required(self) -> bool:
        with self._lock:
            row = self._connection.execute("SELECT COUNT(*) FROM users").fetchone()
        return not row or int(row[0]) == 0

    def register_organization(
        self,
        *,
        organization_name: str,
        display_name: str,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthenticatedSession:
        organization_name = organization_name.strip()
        display_name = display_name.strip()
        if not 2 <= len(organization_name) <= 120:
            raise ValueError("组织名称需为 2 至 120 个字符")
        if not 2 <= len(display_name) <= 80:
            raise ValueError("姓名需为 2 至 80 个字符")
        normalized_email = normalize_email(email)
        encoded_password = hash_password(password)
        now = _utc_now()
        user_id = str(uuid4())
        org_id = ""

        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                user_count = int(
                    self._connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                )
                bootstrap = user_count == 0
                if not self.registration_enabled and not bootstrap:
                    raise RegistrationClosed("当前服务未开放自助注册，请联系管理员")
                legacy_org_id = self._single_unclaimed_organization() if bootstrap else None
                org_id = legacy_org_id or str(uuid4())
                slug = self._unique_slug(organization_name, exclude_org_id=legacy_org_id)
                self._ensure_email_available(normalized_email)
                if legacy_org_id:
                    self._connection.execute(
                        """
                        UPDATE organizations
                        SET name = ?, slug = ?, status = 'active', updated_at = ?
                        WHERE id = ?
                        """,
                        (organization_name, slug, _iso(now), legacy_org_id),
                    )
                else:
                    self._connection.execute(
                        """
                        INSERT INTO organizations (id, name, slug, status, created_at, updated_at)
                        VALUES (?, ?, ?, 'active', ?, ?)
                        """,
                        (org_id, organization_name, slug, _iso(now), _iso(now)),
                    )
                self._connection.execute(
                    """
                    INSERT INTO users (
                        id, org_id, email, display_name, password_hash, role, status,
                        password_changed_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'owner', 'active', ?, ?, ?)
                    """,
                    (
                        user_id,
                        org_id,
                        normalized_email,
                        display_name,
                        encoded_password,
                        _iso(now),
                        _iso(now),
                        _iso(now),
                    ),
                )
                self._connection.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                self._connection.execute("ROLLBACK")
                raise IdentityConflict("该邮箱已被使用") from exc
            except Exception:
                self._connection.execute("ROLLBACK")
                raise
        user = self.get_user(user_id)
        if user is None:  # pragma: no cover - database invariant
            raise RuntimeError("registered user could not be read back")
        return self._issue_session(user, ip_address=ip_address, user_agent=user_agent)

    def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthenticatedSession:
        try:
            normalized_email = normalize_email(email)
        except ValueError as exc:
            raise AuthenticationFailed("邮箱或密码不正确") from exc
        with self._lock:
            row = self._connection.execute(
                """
                SELECT users.*, organizations.name AS organization_name,
                       organizations.status AS organization_status
                FROM users
                JOIN organizations ON organizations.id = users.org_id
                WHERE users.email = ?
                """,
                (normalized_email,),
            ).fetchone()
        if row is None or not verify_password(password, str(row["password_hash"])):
            # Keep a meaningful amount of password work on unknown-user paths.
            if row is None:
                hashlib.scrypt(
                    password.encode("utf-8"),
                    salt=b"contractguard-login",
                    n=2**14,
                    r=8,
                    p=1,
                    dklen=32,
                )
            raise AuthenticationFailed("邮箱或密码不正确")
        if row["status"] != UserStatus.ACTIVE.value or row["organization_status"] != "active":
            raise AuthenticationFailed("账户当前不可用，请联系管理员")
        user = self._row_to_user(row)
        return self._issue_session(user, ip_address=ip_address, user_agent=user_agent)

    def authenticate(self, access_token: str) -> tuple[IdentityUser, str]:
        if not access_token:
            raise AuthenticationFailed("请先登录")
        digest = _token_digest(access_token)
        now = _utc_now()
        with self._lock:
            row = self._connection.execute(
                """
                SELECT users.*, organizations.name AS organization_name,
                       organizations.status AS organization_status,
                       auth_sessions.id AS auth_session_id,
                       auth_sessions.access_expires_at,
                       auth_sessions.revoked_at
                FROM auth_sessions
                JOIN users ON users.id = auth_sessions.user_id
                JOIN organizations ON organizations.id = users.org_id
                WHERE auth_sessions.access_token_hash = ?
                """,
                (digest,),
            ).fetchone()
        if (
            row is None
            or row["revoked_at"] is not None
            or datetime.fromisoformat(str(row["access_expires_at"])) <= now
            or row["status"] != UserStatus.ACTIVE.value
            or row["organization_status"] != "active"
        ):
            raise AuthenticationFailed("登录状态已失效，请重新登录")
        return self._row_to_user(row), str(row["auth_session_id"])

    def refresh(
        self,
        refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthenticatedSession:
        if not refresh_token:
            raise AuthenticationFailed("刷新凭据已失效，请重新登录")
        digest = _token_digest(refresh_token)
        now = _utc_now()
        with self._lock:
            row = self._connection.execute(
                """
                SELECT users.*, organizations.name AS organization_name,
                       organizations.status AS organization_status,
                       auth_sessions.id AS auth_session_id,
                       auth_sessions.refresh_expires_at,
                       auth_sessions.revoked_at
                FROM auth_sessions
                JOIN users ON users.id = auth_sessions.user_id
                JOIN organizations ON organizations.id = users.org_id
                WHERE auth_sessions.refresh_token_hash = ?
                """,
                (digest,),
            ).fetchone()
        if (
            row is None
            or row["revoked_at"] is not None
            or datetime.fromisoformat(str(row["refresh_expires_at"])) <= now
            or row["status"] != UserStatus.ACTIVE.value
            or row["organization_status"] != "active"
        ):
            raise AuthenticationFailed("刷新凭据已失效，请重新登录")
        user = self._row_to_user(row)
        return self._issue_session(
            user,
            session_id=str(row["auth_session_id"]),
            rotate=True,
            expected_refresh_digest=digest,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def revoke(self, access_token: str) -> None:
        if not access_token:
            return
        with self._lock:
            self._connection.execute(
                "UPDATE auth_sessions SET revoked_at = ? WHERE access_token_hash = ?",
                (_iso(_utc_now()), _token_digest(access_token)),
            )

    def get_user(self, user_id: str) -> IdentityUser | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT users.*, organizations.name AS organization_name
                FROM users JOIN organizations ON organizations.id = users.org_id
                WHERE users.id = ?
                """,
                (user_id,),
            ).fetchone()
        return self._row_to_user(row) if row is not None else None

    def list_users(self, org_id: str) -> Sequence[IdentityUser]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT users.*, organizations.name AS organization_name
                FROM users JOIN organizations ON organizations.id = users.org_id
                WHERE users.org_id = ? ORDER BY users.created_at ASC
                """,
                (org_id,),
            ).fetchall()
        return tuple(self._row_to_user(row) for row in rows)

    def create_user(
        self,
        *,
        org_id: str,
        email: str,
        display_name: str,
        password: str,
        role: UserRole,
    ) -> IdentityUser:
        if role is UserRole.OWNER:
            raise PermissionDenied("不能通过成员接口创建所有者")
        normalized_email = normalize_email(email)
        display_name = display_name.strip()
        if not 2 <= len(display_name) <= 80:
            raise ValueError("姓名需为 2 至 80 个字符")
        encoded = hash_password(password)
        user_id = str(uuid4())
        now = _utc_now()
        with self._lock:
            try:
                self._ensure_email_available(normalized_email)
                self._connection.execute(
                    """
                    INSERT INTO users (
                        id, org_id, email, display_name, password_hash, role, status,
                        password_changed_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                    """,
                    (
                        user_id,
                        org_id,
                        normalized_email,
                        display_name,
                        encoded,
                        role.value,
                        _iso(now),
                        _iso(now),
                        _iso(now),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise IdentityConflict("该邮箱已被使用") from exc
        user = self.get_user(user_id)
        if user is None:  # pragma: no cover - database invariant
            raise RuntimeError("created user could not be read back")
        return user

    def update_user(
        self,
        *,
        org_id: str,
        user_id: str,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        display_name: str | None = None,
    ) -> IdentityUser | None:
        current = self.get_user(user_id)
        if current is None or current.org_id != org_id:
            return None
        if current.role is UserRole.OWNER and role not in {None, UserRole.OWNER}:
            raise PermissionDenied("组织所有者不能被降级")
        if current.role is UserRole.OWNER and status is UserStatus.DISABLED:
            raise PermissionDenied("组织所有者不能被禁用")
        if current.role is not UserRole.OWNER and role is UserRole.OWNER:
            raise PermissionDenied("成员接口不能转移组织所有权")
        resolved_name = current.display_name if display_name is None else display_name.strip()
        if not 2 <= len(resolved_name) <= 80:
            raise ValueError("姓名需为 2 至 80 个字符")
        resolved_role = role or current.role
        resolved_status = status or current.status
        with self._lock:
            self._connection.execute(
                """
                UPDATE users SET display_name = ?, role = ?, status = ?, updated_at = ?
                WHERE id = ? AND org_id = ?
                """,
                (
                    resolved_name,
                    resolved_role.value,
                    resolved_status.value,
                    _iso(_utc_now()),
                    user_id,
                    org_id,
                ),
            )
            if resolved_status is UserStatus.DISABLED:
                self._connection.execute(
                    """
                    UPDATE auth_sessions SET revoked_at = ?
                    WHERE user_id = ? AND revoked_at IS NULL
                    """,
                    (_iso(_utc_now()), user_id),
                )
        return self.get_user(user_id)

    def change_password(self, user_id: str, *, current_password: str, new_password: str) -> None:
        with self._lock:
            row = self._connection.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None or not verify_password(current_password, str(row["password_hash"])):
            raise AuthenticationFailed("当前密码不正确")
        encoded = hash_password(new_password)
        now = _iso(_utc_now())
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute(
                    """
                    UPDATE users SET password_hash = ?, password_changed_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (encoded, now, now, user_id),
                )
                self._connection.execute(
                    """
                    UPDATE auth_sessions SET revoked_at = ?
                    WHERE user_id = ? AND revoked_at IS NULL
                    """,
                    (now, user_id),
                )
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise

    def record_audit(
        self,
        *,
        org_id: str,
        actor_user_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        outcome: str = "success",
        request_id: str | None = None,
        ip_address: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> str:
        identifier = str(uuid4())
        safe_details = dict(details or {})
        for forbidden in ("password", "token", "secret", "contract_text", "text"):
            safe_details.pop(forbidden, None)
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO audit_logs (
                    id, org_id, actor_user_id, action, resource_type, resource_id,
                    outcome, request_id, ip_hash, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identifier,
                    org_id,
                    actor_user_id,
                    action,
                    resource_type,
                    resource_id,
                    outcome,
                    request_id,
                    _hash_metadata(ip_address),
                    json.dumps(safe_details, ensure_ascii=False, separators=(",", ":")),
                    _iso(_utc_now()),
                ),
            )
        return identifier

    def list_audit(
        self,
        *,
        org_id: str,
        page: int = 1,
        page_size: int = 50,
        action: str | None = None,
    ) -> tuple[Sequence[AuditRecord], int]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        clauses = ["org_id = ?"]
        parameters: list[Any] = [org_id]
        if action:
            clauses.append("action = ?")
            parameters.append(action)
        where = " AND ".join(clauses)
        with self._lock:
            total = int(
                self._connection.execute(
                    f"SELECT COUNT(*) FROM audit_logs WHERE {where}",  # noqa: S608
                    parameters,
                ).fetchone()[0]
            )
            rows = self._connection.execute(
                f"""
                SELECT * FROM audit_logs WHERE {where}
                ORDER BY created_at DESC LIMIT ? OFFSET ?
                """,  # noqa: S608
                (*parameters, page_size, (page - 1) * page_size),
            ).fetchall()
        return tuple(self._row_to_audit(row) for row in rows), total

    def _issue_session(
        self,
        user: IdentityUser,
        *,
        session_id: str | None = None,
        rotate: bool = False,
        expected_refresh_digest: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthenticatedSession:
        access_token = _opaque_token()
        refresh_token = _opaque_token()
        now = _utc_now()
        access_expires = now + self.access_ttl
        refresh_expires = now + self.refresh_ttl
        identifier = session_id or str(uuid4())
        with self._lock:
            if rotate:
                if expected_refresh_digest is None:
                    raise AuthenticationFailed("刷新凭据已失效，请重新登录")
                cursor = self._connection.execute(
                    """
                    UPDATE auth_sessions SET access_token_hash = ?, refresh_token_hash = ?,
                        access_expires_at = ?, refresh_expires_at = ?, revoked_at = NULL,
                        last_seen_at = ?, ip_hash = ?, user_agent_hash = ?
                    WHERE id = ? AND user_id = ? AND refresh_token_hash = ?
                        AND revoked_at IS NULL
                    """,
                    (
                        _token_digest(access_token),
                        _token_digest(refresh_token),
                        _iso(access_expires),
                        _iso(refresh_expires),
                        _iso(now),
                        _hash_metadata(ip_address),
                        _hash_metadata(user_agent),
                        identifier,
                        user.id,
                        expected_refresh_digest,
                    ),
                )
                if cursor.rowcount == 0:
                    raise AuthenticationFailed("刷新凭据已失效，请重新登录")
            else:
                self._connection.execute(
                    """
                    INSERT INTO auth_sessions (
                        id, user_id, access_token_hash, refresh_token_hash,
                        access_expires_at, refresh_expires_at, revoked_at,
                        created_at, last_seen_at, ip_hash, user_agent_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                    """,
                    (
                        identifier,
                        user.id,
                        _token_digest(access_token),
                        _token_digest(refresh_token),
                        _iso(access_expires),
                        _iso(refresh_expires),
                        _iso(now),
                        _iso(now),
                        _hash_metadata(ip_address),
                        _hash_metadata(user_agent),
                    ),
                )
        return AuthenticatedSession(
            user=user,
            session_id=identifier,
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires,
            refresh_expires_at=refresh_expires,
        )

    def _single_unclaimed_organization(self) -> str | None:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT organizations.id
                FROM organizations
                LEFT JOIN users ON users.org_id = organizations.id
                GROUP BY organizations.id
                HAVING COUNT(users.id) = 0
                """
            ).fetchall()
        return str(rows[0]["id"]) if len(rows) == 1 else None

    def _unique_slug(self, name: str, *, exclude_org_id: str | None = None) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or "organization"
        base = base[:48]
        candidate = base
        with self._lock:
            index = 1
            while self._connection.execute(
                "SELECT 1 FROM organizations WHERE slug = ? AND id != ?",
                (candidate, exclude_org_id or ""),
            ).fetchone():
                index += 1
                candidate = f"{base[:42]}-{index}"
        return candidate

    def _ensure_email_available(self, email: str) -> None:
        row = self._connection.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if row is not None:
            raise IdentityConflict("该邮箱已被使用")

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> IdentityUser:
        return IdentityUser(
            id=str(row["id"]),
            org_id=str(row["org_id"]),
            organization_name=str(row["organization_name"]),
            email=str(row["email"]),
            display_name=str(row["display_name"]),
            role=UserRole(str(row["role"])),
            status=UserStatus(str(row["status"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    @staticmethod
    def _row_to_audit(row: sqlite3.Row) -> AuditRecord:
        details = json.loads(str(row["details_json"] or "{}"))
        return AuditRecord(
            id=str(row["id"]),
            org_id=str(row["org_id"]),
            actor_user_id=(str(row["actor_user_id"]) if row["actor_user_id"] else None),
            action=str(row["action"]),
            resource_type=str(row["resource_type"]),
            resource_id=(str(row["resource_id"]) if row["resource_id"] else None),
            outcome=str(row["outcome"]),
            request_id=(str(row["request_id"]) if row["request_id"] else None),
            details=details if isinstance(details, dict) else {},
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )


__all__ = [
    "AuditRecord",
    "AuthenticatedSession",
    "AuthenticationFailed",
    "IdentityConflict",
    "IdentityError",
    "IdentityUser",
    "PermissionDenied",
    "RegistrationClosed",
    "SQLiteIdentityService",
    "UserRole",
    "UserStatus",
    "hash_password",
    "normalize_email",
    "validate_password",
    "verify_password",
]
