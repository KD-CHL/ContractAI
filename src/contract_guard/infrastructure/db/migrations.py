"""Transactional, versioned SQLite migrations for ContractGuard.

The migration runner deliberately has no dependency on the application repository.
It can therefore upgrade a database before the web process starts and can adopt the
unversioned V1 schema created by earlier ContractGuard releases without rewriting or
dropping existing rows.

Destructive down migrations are intentionally unsupported. Operational rollback is
performed by :func:`restore_database`, which validates a known-good backup and creates
an automatic safety snapshot before replacing an existing destination.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from uuid import NAMESPACE_URL, uuid4, uuid5


class MigrationError(RuntimeError):
    """Raised when a migration or database safety operation cannot complete."""


@dataclass(frozen=True, slots=True)
class AppliedMigration:
    """One migration recorded in ``schema_migrations``."""

    version: int
    name: str
    checksum: str
    applied_at: str


@dataclass(frozen=True, slots=True)
class MigrationResult:
    """Outcome returned by :func:`upgrade_database`."""

    database: str
    from_version: int
    to_version: int
    applied_versions: tuple[int, ...]
    latest_version: int

    @property
    def already_current(self) -> bool:
        return not self.applied_versions and self.to_version == self.latest_version


@dataclass(frozen=True, slots=True)
class MigrationStatus:
    """Read-only view of a database's migration state."""

    database: str
    exists: bool
    current_version: int
    latest_version: int
    applied: tuple[AppliedMigration, ...]
    pending_versions: tuple[int, ...]

    @property
    def is_current(self) -> bool:
        return (
            self.exists
            and not self.pending_versions
            and self.current_version == self.latest_version
        )


@dataclass(frozen=True, slots=True)
class BackupResult:
    """Verified SQLite backup metadata."""

    source: str
    destination: str
    size_bytes: int
    sha256: str
    schema_version: int
    created_at: str


@dataclass(frozen=True, slots=True)
class RestoreResult:
    """Verified restore metadata, including an automatic pre-restore snapshot."""

    backup: str
    destination: str
    schema_version: int
    sha256: str
    safety_backup: str | None
    restored_at: str


MigrationCallable = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True, slots=True)
class _Migration:
    version: int
    name: str
    checksum: str
    upgrade: MigrationCallable
    validate: MigrationCallable


_SCHEMA_MIGRATIONS_SQL: Final = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
)
"""

_V1_STATEMENTS: Final[tuple[str, ...]] = (
    """
    CREATE TABLE IF NOT EXISTS reviews (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        contract_id TEXT,
        fingerprint TEXT NOT NULL,
        document_name TEXT NOT NULL,
        media_type TEXT NOT NULL,
        status TEXT NOT NULL,
        report_json TEXT NOT NULL DEFAULT '{}',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        error TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_reviews_scope_id
        ON reviews (org_id, session_id, id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_reviews_scope_fingerprint
        ON reviews (org_id, session_id, fingerprint, updated_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS review_feedback (
        id TEXT PRIMARY KEY,
        review_id TEXT NOT NULL,
        org_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        rating INTEGER,
        accepted INTEGER,
        finding_id TEXT,
        comment TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_feedback_scope_review
        ON review_feedback (org_id, session_id, review_id, created_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        layer TEXT NOT NULL CHECK (
            layer IN ('global', 'short_term', 'profile', 'episodic')
        ),
        memory_key TEXT NOT NULL,
        content_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (org_id, session_id, layer, memory_key)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_memories_scope_layer
        ON memories (org_id, session_id, layer, updated_at DESC)
    """,
)

_V2_TABLE_STATEMENTS: Final[tuple[str, ...]] = (
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        email TEXT NOT NULL COLLATE NOCASE,
        display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'business_user',
        status TEXT NOT NULL DEFAULT 'active',
        password_changed_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE RESTRICT
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_global
        ON users (email COLLATE NOCASE)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_users_org_status
        ON users (org_id, status, created_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        access_token_hash TEXT NOT NULL UNIQUE,
        refresh_token_hash TEXT NOT NULL UNIQUE,
        access_expires_at TEXT NOT NULL,
        refresh_expires_at TEXT NOT NULL,
        revoked_at TEXT,
        created_at TEXT NOT NULL,
        last_seen_at TEXT,
        ip_hash TEXT,
        user_agent_hash TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_expiry
        ON auth_sessions (user_id, revoked_at, refresh_expires_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        actor_user_id TEXT,
        action TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        resource_id TEXT,
        outcome TEXT NOT NULL,
        request_id TEXT,
        ip_hash TEXT,
        details_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE RESTRICT,
        FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_audit_logs_org_created
        ON audit_logs (org_id, created_at DESC, id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_audit_logs_request
        ON audit_logs (request_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS finding_actions (
        id TEXT PRIMARY KEY,
        review_id TEXT NOT NULL,
        org_id TEXT NOT NULL,
        finding_id TEXT NOT NULL,
        actor_user_id TEXT,
        action TEXT NOT NULL,
        note TEXT,
        details_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
        FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE RESTRICT,
        FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_finding_actions_review_finding
        ON finding_actions (org_id, review_id, finding_id, created_at DESC)
    """,
)

_V2_REVIEW_COLUMNS: Final[tuple[tuple[str, str], ...]] = (
    (
        "created_by_user_id",
        "created_by_user_id TEXT REFERENCES users(id) ON DELETE SET NULL",
    ),
    ("deleted_at", "deleted_at TEXT"),
    (
        "decision_status",
        "decision_status TEXT NOT NULL DEFAULT 'draft'",
    ),
    (
        "state_version",
        "state_version INTEGER NOT NULL DEFAULT 1 CHECK (state_version >= 1)",
    ),
    (
        "analysis_version",
        "analysis_version TEXT NOT NULL DEFAULT 'contractguard-review-v1'",
    ),
    ("idempotency_key", "idempotency_key TEXT"),
)

_V2_REVIEW_INDEXES: Final[tuple[str, ...]] = (
    """
    CREATE INDEX IF NOT EXISTS idx_reviews_org_deleted_status_created
        ON reviews (org_id, deleted_at, status, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_reviews_org_decision_updated
        ON reviews (org_id, deleted_at, decision_status, updated_at DESC)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_reviews_org_session_idempotency
        ON reviews (org_id, session_id, idempotency_key)
        WHERE idempotency_key IS NOT NULL
    """,
)

_V1_REQUIRED_COLUMNS: Final[dict[str, frozenset[str]]] = {
    "reviews": frozenset(
        {
            "id",
            "org_id",
            "session_id",
            "contract_id",
            "fingerprint",
            "document_name",
            "media_type",
            "status",
            "report_json",
            "metadata_json",
            "error",
            "created_at",
            "updated_at",
        }
    ),
    "review_feedback": frozenset(
        {
            "id",
            "review_id",
            "org_id",
            "session_id",
            "rating",
            "accepted",
            "finding_id",
            "comment",
            "metadata_json",
            "created_at",
        }
    ),
    "memories": frozenset(
        {
            "id",
            "org_id",
            "session_id",
            "layer",
            "memory_key",
            "content_json",
            "metadata_json",
            "created_at",
            "updated_at",
        }
    ),
}

_V2_REQUIRED_COLUMNS: Final[dict[str, frozenset[str]]] = {
    "organizations": frozenset({"id", "name", "slug", "status", "created_at", "updated_at"}),
    "users": frozenset(
        {
            "id",
            "org_id",
            "email",
            "display_name",
            "password_hash",
            "role",
            "status",
            "password_changed_at",
            "created_at",
            "updated_at",
        }
    ),
    "auth_sessions": frozenset(
        {
            "id",
            "user_id",
            "access_token_hash",
            "refresh_token_hash",
            "access_expires_at",
            "refresh_expires_at",
            "revoked_at",
            "created_at",
            "last_seen_at",
            "ip_hash",
            "user_agent_hash",
        }
    ),
    "audit_logs": frozenset(
        {
            "id",
            "org_id",
            "actor_user_id",
            "action",
            "resource_type",
            "resource_id",
            "outcome",
            "request_id",
            "ip_hash",
            "details_json",
            "created_at",
        }
    ),
    "finding_actions": frozenset(
        {
            "id",
            "review_id",
            "org_id",
            "finding_id",
            "actor_user_id",
            "action",
            "note",
            "details_json",
            "created_at",
        }
    ),
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _checksum(label: str, parts: Iterable[str]) -> str:
    payload = "\n-- migration-part --\n".join((label, *parts))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _execute_all(connection: sqlite3.Connection, statements: Iterable[str]) -> None:
    for statement in statements:
        connection.execute(statement)


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(connection, table):
        return set()
    escaped = table.replace('"', '""')
    return {str(row[1]) for row in connection.execute(f'PRAGMA table_info("{escaped}")')}


def _require_columns(
    connection: sqlite3.Connection,
    requirements: dict[str, frozenset[str]],
) -> None:
    for table, required in requirements.items():
        existing = _table_columns(connection, table)
        missing = sorted(required.difference(existing))
        if missing:
            joined = ", ".join(missing)
            raise MigrationError(f"table {table!r} is incompatible; missing columns: {joined}")


def _validate_v1(connection: sqlite3.Connection) -> None:
    _require_columns(connection, _V1_REQUIRED_COLUMNS)


def _upgrade_v1(connection: sqlite3.Connection) -> None:
    # CREATE IF NOT EXISTS adopts the exact unversioned schema used by 0.1.0.
    # Existing tables and rows are never dropped, copied, or rewritten.
    _execute_all(connection, _V1_STATEMENTS)
    _validate_v1(connection)


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    declaration: str,
) -> None:
    if column in _table_columns(connection, table):
        return
    escaped_table = table.replace('"', '""')
    connection.execute(f'ALTER TABLE "{escaped_table}" ADD COLUMN {declaration}')


def _backfill_organizations(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT org_id FROM reviews
        UNION
        SELECT org_id FROM review_feedback
        UNION
        SELECT org_id FROM memories
        """
    ).fetchall()
    now = _utc_now()
    organization_ids = sorted({str(row[0]) for row in rows if row[0] is not None})
    for organization_id in organization_ids:
        connection.execute(
            """
            INSERT OR IGNORE INTO organizations (
                id, name, slug, status, created_at, updated_at
            ) VALUES (?, ?, ?, 'active', ?, ?)
            """,
            (organization_id, organization_id, organization_id, now, now),
        )

    if organization_ids:
        placeholders = ",".join("?" for _ in organization_ids)
        persisted = {
            str(row[0])
            for row in connection.execute(
                f"SELECT id FROM organizations WHERE id IN ({placeholders})",
                organization_ids,
            )
        }
        missing = sorted(set(organization_ids).difference(persisted))
        if missing:
            raise MigrationError(
                "could not backfill organizations for existing tenant ids: " + ", ".join(missing)
            )


def _validate_v2(connection: sqlite3.Connection) -> None:
    _validate_v1(connection)
    _require_columns(connection, _V2_REQUIRED_COLUMNS)
    review_columns = _table_columns(connection, "reviews")
    missing_review_columns = sorted(
        {name for name, _ in _V2_REVIEW_COLUMNS}.difference(review_columns)
    )
    if missing_review_columns:
        raise MigrationError(
            "V2 reviews schema is incomplete; missing columns: " + ", ".join(missing_review_columns)
        )

    indexes = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'users'"
        )
    }
    if "ux_users_email_global" not in indexes:
        raise MigrationError("V2 global unique users.email index is missing")


def _upgrade_v2(connection: sqlite3.Connection) -> None:
    _validate_v1(connection)
    _execute_all(connection, _V2_TABLE_STATEMENTS)
    _backfill_organizations(connection)
    for column, declaration in _V2_REVIEW_COLUMNS:
        _add_column_if_missing(connection, "reviews", column, declaration)
    _execute_all(connection, _V2_REVIEW_INDEXES)
    _validate_v2(connection)


_V3_TABLE_STATEMENTS: Final[tuple[str, ...]] = (
    """
    CREATE TABLE IF NOT EXISTS work_items (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        review_id TEXT NOT NULL,
        kind TEXT NOT NULL CHECK (kind IN ('finding', 'obligation')),
        source_id TEXT,
        source_ordinal INTEGER NOT NULL CHECK (source_ordinal >= 0),
        title TEXT NOT NULL,
        source_payload_json TEXT NOT NULL DEFAULT '{}',
        risk_level TEXT,
        status TEXT NOT NULL,
        assignee_user_id TEXT,
        due_at TEXT,
        note TEXT,
        state_version INTEGER NOT NULL DEFAULT 1 CHECK (state_version >= 1),
        created_by_user_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT,
        UNIQUE (review_id, kind, source_ordinal),
        FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE RESTRICT,
        FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
        FOREIGN KEY (assignee_user_id) REFERENCES users(id) ON DELETE SET NULL,
        FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_work_items_org_assignee_status_due
        ON work_items (org_id, assignee_user_id, status, due_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_work_items_review_kind_updated
        ON work_items (review_id, kind, updated_at DESC, id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_work_items_org_risk_status
        ON work_items (org_id, kind, risk_level, status)
    """,
    """
    CREATE TABLE IF NOT EXISTS work_item_events (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        review_id TEXT NOT NULL,
        work_item_id TEXT NOT NULL,
        actor_user_id TEXT,
        action TEXT NOT NULL,
        from_status TEXT,
        to_status TEXT,
        changes_json TEXT NOT NULL DEFAULT '{}',
        note TEXT,
        state_version INTEGER NOT NULL CHECK (state_version >= 1),
        created_at TEXT NOT NULL,
        FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE RESTRICT,
        FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
        FOREIGN KEY (work_item_id) REFERENCES work_items(id) ON DELETE CASCADE,
        FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_work_item_events_item_created
        ON work_item_events (org_id, work_item_id, created_at DESC, id DESC)
    """,
)

_V3_REQUIRED_COLUMNS: Final[dict[str, frozenset[str]]] = {
    "work_items": frozenset(
        {
            "id",
            "org_id",
            "review_id",
            "kind",
            "source_id",
            "source_ordinal",
            "title",
            "source_payload_json",
            "risk_level",
            "status",
            "assignee_user_id",
            "due_at",
            "note",
            "state_version",
            "created_by_user_id",
            "created_at",
            "updated_at",
            "completed_at",
        }
    ),
    "work_item_events": frozenset(
        {
            "id",
            "org_id",
            "review_id",
            "work_item_id",
            "actor_user_id",
            "action",
            "from_status",
            "to_status",
            "changes_json",
            "note",
            "state_version",
            "created_at",
        }
    ),
}


def _report_items(report: object, key: str) -> list[object]:
    if not isinstance(report, dict):
        return []
    value = report.get(key, [])
    if isinstance(value, dict):
        value = value.get("items", [])
    return value if isinstance(value, list) else []


def _backfill_work_items(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT id, org_id, report_json, created_by_user_id, created_at, updated_at
        FROM reviews WHERE status = 'completed'
        """
    ).fetchall()
    for row in rows:
        try:
            report = json.loads(str(row["report_json"]))
        except (json.JSONDecodeError, TypeError):
            continue
        for kind, key, default_status in (
            ("finding", "findings", "open"),
            ("obligation", "obligations", "pending"),
        ):
            for ordinal, raw_item in enumerate(_report_items(report, key)):
                item = raw_item if isinstance(raw_item, dict) else {"value": raw_item}
                source_key = "finding_id" if kind == "finding" else "obligation_id"
                raw_source_id = item.get(source_key)
                source_id = str(raw_source_id).strip() if raw_source_id is not None else None
                if not source_id:
                    source_id = None
                raw_title = item.get("title") if kind == "finding" else item.get("action")
                title = str(raw_title).strip() if raw_title is not None else ""
                if not title:
                    title = f"{'风险' if kind == 'finding' else '义务'} {ordinal + 1}"
                raw_risk = item.get("risk_level") if kind == "finding" else None
                risk_level = str(raw_risk).strip() if raw_risk is not None else None
                if not risk_level:
                    risk_level = None
                work_item_id = str(
                    uuid5(
                        NAMESPACE_URL,
                        f"contractguard:work-item:{row['id']}:{kind}:{ordinal}",
                    )
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO work_items (
                        id, org_id, review_id, kind, source_id, source_ordinal,
                        title, source_payload_json, risk_level, status,
                        assignee_user_id, due_at, note, state_version,
                        created_by_user_id, created_at, updated_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, 1, ?, ?, ?, NULL)
                    """,
                    (
                        work_item_id,
                        str(row["org_id"]),
                        str(row["id"]),
                        kind,
                        source_id,
                        ordinal,
                        title,
                        json.dumps(item, ensure_ascii=False, separators=(",", ":")),
                        risk_level,
                        default_status,
                        row["created_by_user_id"],
                        str(row["created_at"]),
                        str(row["updated_at"]),
                    ),
                )
                event_id = str(
                    uuid5(
                        NAMESPACE_URL,
                        f"contractguard:work-item-event:{work_item_id}:materialized",
                    )
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO work_item_events (
                        id, org_id, review_id, work_item_id, actor_user_id,
                        action, from_status, to_status, changes_json, note,
                        state_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, 'materialized', NULL, ?, '{}', NULL, 1, ?)
                    """,
                    (
                        event_id,
                        str(row["org_id"]),
                        str(row["id"]),
                        work_item_id,
                        row["created_by_user_id"],
                        default_status,
                        str(row["updated_at"]),
                    ),
                )


def _validate_v3(connection: sqlite3.Connection) -> None:
    _validate_v2(connection)
    _require_columns(connection, _V3_REQUIRED_COLUMNS)
    indexes = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'work_items'"
        )
    }
    if "idx_work_items_org_assignee_status_due" not in indexes:
        raise MigrationError("V3 work-item queue index is missing")


def _upgrade_v3(connection: sqlite3.Connection) -> None:
    _validate_v2(connection)
    _execute_all(connection, _V3_TABLE_STATEMENTS)
    _backfill_work_items(connection)
    _validate_v3(connection)


_V1_SIGNATURE = (*_V1_STATEMENTS, "adopt-existing-v1-without-rewrite")
_V2_SIGNATURE = (
    *_V2_TABLE_STATEMENTS,
    *(declaration for _, declaration in _V2_REVIEW_COLUMNS),
    *_V2_REVIEW_INDEXES,
    "backfill-organizations-from-v1-tenant-columns",
)
_V3_SIGNATURE = (*_V3_TABLE_STATEMENTS, "backfill-completed-review-work-items-by-ordinal")

_MIGRATIONS: Final[tuple[_Migration, ...]] = (
    _Migration(
        version=1,
        name="baseline_contractguard",
        checksum=_checksum("0001_baseline_contractguard", _V1_SIGNATURE),
        upgrade=_upgrade_v1,
        validate=_validate_v1,
    ),
    _Migration(
        version=2,
        name="identity_audit_review_lifecycle",
        checksum=_checksum("0002_identity_audit_review_lifecycle", _V2_SIGNATURE),
        upgrade=_upgrade_v2,
        validate=_validate_v2,
    ),
    _Migration(
        version=3,
        name="operational_work_items",
        checksum=_checksum("0003_operational_work_items", _V3_SIGNATURE),
        upgrade=_upgrade_v3,
        validate=_validate_v3,
    ),
)

LATEST_VERSION: Final = _MIGRATIONS[-1].version


def _database_path(value: str | Path) -> Path:
    text = str(value).strip()
    if not text or text == ":memory:":
        raise MigrationError("migration and backup tools require a filesystem SQLite path")
    return Path(text).expanduser().resolve()


def _configure_connection(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    _configure_connection(connection)
    return connection


def _connect_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(_SCHEMA_MIGRATIONS_SQL)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def _read_applied(connection: sqlite3.Connection) -> tuple[AppliedMigration, ...]:
    if not _table_exists(connection, "schema_migrations"):
        return ()
    rows = connection.execute(
        "SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version"
    ).fetchall()
    return tuple(
        AppliedMigration(
            version=int(row["version"]),
            name=str(row["name"]),
            checksum=str(row["checksum"]),
            applied_at=str(row["applied_at"]),
        )
        for row in rows
    )


def _validate_applied(applied: Sequence[AppliedMigration]) -> None:
    by_version = {migration.version: migration for migration in _MIGRATIONS}
    expected_prefix: list[int] = []
    for record in applied:
        migration = by_version.get(record.version)
        if migration is None:
            raise MigrationError(
                "database contains unknown migration version "
                f"{record.version}; refusing to continue"
            )
        if record.name != migration.name or record.checksum != migration.checksum:
            raise MigrationError(
                f"migration {record.version} metadata/checksum differs from this release"
            )
        expected_prefix.append(record.version)
    if expected_prefix != list(range(1, len(expected_prefix) + 1)):
        raise MigrationError("schema_migrations contains a non-contiguous version history")


def upgrade_database(path: str | Path) -> MigrationResult:
    """Upgrade ``path`` to the latest schema using one transaction per version.

    Existing unversioned V1 databases are adopted in place: V1 uses only
    ``CREATE ... IF NOT EXISTS`` followed by compatibility validation, then V2
    adds new tables and nullable/defaulted columns without deleting existing rows.
    """

    database = _database_path(path)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = _connect(database)
    applied_now: list[int] = []
    try:
        _ensure_migration_table(connection)
        before = _read_applied(connection)
        _validate_applied(before)
        for record in before:
            _MIGRATIONS[record.version - 1].validate(connection)
        from_version = max((item.version for item in before), default=0)

        for migration in _MIGRATIONS:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT name, checksum FROM schema_migrations WHERE version = ?",
                    (migration.version,),
                ).fetchone()
                if existing is not None:
                    if (
                        str(existing["name"]) != migration.name
                        or str(existing["checksum"]) != migration.checksum
                    ):
                        raise MigrationError(
                            f"migration {migration.version} metadata/checksum conflict"
                        )
                    migration.validate(connection)
                    connection.execute("COMMIT")
                    continue

                migration.upgrade(connection)
                connection.execute(
                    """
                    INSERT INTO schema_migrations (version, name, checksum, applied_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (migration.version, migration.name, migration.checksum, _utc_now()),
                )
                connection.execute("COMMIT")
                applied_now.append(migration.version)
            except Exception:
                connection.execute("ROLLBACK")
                raise

        after = _read_applied(connection)
        _validate_applied(after)
        for record in after:
            _MIGRATIONS[record.version - 1].validate(connection)
        to_version = max((item.version for item in after), default=0)
    except (sqlite3.Error, MigrationError) as exc:
        if isinstance(exc, MigrationError):
            raise
        raise MigrationError(f"could not upgrade SQLite database {database}: {exc}") from exc
    finally:
        connection.close()

    return MigrationResult(
        database=str(database),
        from_version=from_version,
        to_version=to_version,
        applied_versions=tuple(applied_now),
        latest_version=LATEST_VERSION,
    )


def migration_status(path: str | Path) -> MigrationStatus:
    """Inspect migration state without creating or changing the database."""

    database = _database_path(path)
    if not database.is_file():
        return MigrationStatus(
            database=str(database),
            exists=False,
            current_version=0,
            latest_version=LATEST_VERSION,
            applied=(),
            pending_versions=tuple(migration.version for migration in _MIGRATIONS),
        )

    try:
        connection = _connect_read_only(database)
        try:
            applied = _read_applied(connection)
            _validate_applied(applied)
        finally:
            connection.close()
    except (sqlite3.Error, MigrationError) as exc:
        if isinstance(exc, MigrationError):
            raise
        raise MigrationError(f"could not inspect SQLite database {database}: {exc}") from exc

    applied_versions = {record.version for record in applied}
    return MigrationStatus(
        database=str(database),
        exists=True,
        current_version=max(applied_versions, default=0),
        latest_version=LATEST_VERSION,
        applied=applied,
        pending_versions=tuple(
            migration.version
            for migration in _MIGRATIONS
            if migration.version not in applied_versions
        ),
    )


def _integrity_check(connection: sqlite3.Connection, *, label: str) -> None:
    rows = connection.execute("PRAGMA quick_check").fetchall()
    messages = [str(row[0]) for row in rows]
    if messages != ["ok"]:
        raise MigrationError(f"{label} failed SQLite integrity check: {'; '.join(messages)}")


def _schema_version(connection: sqlite3.Connection) -> int:
    if not _table_exists(connection, "schema_migrations"):
        return 0
    row = connection.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
    return int(row[0]) if row is not None else 0


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_database(source: Path, destination: Path) -> tuple[int, str]:
    if destination.exists():
        raise MigrationError(f"refusing to overwrite existing backup/staging file: {destination}")
    source_connection = _connect_read_only(source)
    destination_connection: sqlite3.Connection | None = None
    try:
        _integrity_check(source_connection, label=str(source))
        destination_connection = sqlite3.connect(destination, timeout=10)
        source_connection.backup(destination_connection)
        destination_connection.commit()
        _integrity_check(destination_connection, label=str(destination))
        schema_version = _schema_version(destination_connection)
    except Exception:
        if destination_connection is not None:
            destination_connection.close()
            destination_connection = None
        destination.unlink(missing_ok=True)
        raise
    finally:
        source_connection.close()
        if destination_connection is not None:
            destination_connection.close()
    os.chmod(destination, 0o600)
    return schema_version, _file_sha256(destination)


def backup_database(path: str | Path, destination: str | Path) -> BackupResult:
    """Create a consistent, integrity-checked SQLite backup without overwriting files."""

    source = _database_path(path)
    target = _database_path(destination)
    if not source.is_file():
        raise MigrationError(f"source database does not exist: {source}")
    if source == target:
        raise MigrationError("backup source and destination must be different files")
    if target.exists():
        raise MigrationError(f"refusing to overwrite existing backup: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f".{target.name}.tmp-{uuid4().hex}")
    try:
        schema_version, checksum = _copy_database(source, staging)
        # A hard link publishes the verified file atomically and fails if another
        # process created the requested destination after our initial check.
        os.link(staging, target)
        staging.unlink()
        os.chmod(target, 0o600)
    except FileExistsError as exc:
        staging.unlink(missing_ok=True)
        raise MigrationError(f"refusing to overwrite existing backup: {target}") from exc
    except (OSError, sqlite3.Error, MigrationError) as exc:
        staging.unlink(missing_ok=True)
        if isinstance(exc, MigrationError):
            raise
        raise MigrationError(f"could not back up {source} to {target}: {exc}") from exc

    return BackupResult(
        source=str(source),
        destination=str(target),
        size_bytes=target.stat().st_size,
        sha256=checksum,
        schema_version=schema_version,
        created_at=_utc_now(),
    )


def _prepare_existing_destination(destination: Path) -> None:
    """Fail if the destination cannot obtain an exclusive maintenance lock."""

    connection = sqlite3.connect(destination, timeout=1, isolation_level=None)
    try:
        checkpoint = connection.execute("PRAGMA wal_checkpoint(FULL)").fetchone()
        if checkpoint is not None and int(checkpoint[0]) != 0:
            raise MigrationError("database is busy; stop ContractGuard before restoring a backup")
        connection.execute("BEGIN EXCLUSIVE")
        connection.execute("ROLLBACK")
    except sqlite3.Error as exc:
        raise MigrationError(
            "database is busy; stop ContractGuard before restoring a backup"
        ) from exc
    finally:
        connection.close()


def restore_database(backup: str | Path, destination: str | Path) -> RestoreResult:
    """Restore a verified backup, preserving the current destination first.

    If ``destination`` exists, a timestamped ``pre-restore`` backup is created
    automatically in the same directory. The existing database is replaced only
    after both the requested backup and the staging copy pass SQLite integrity
    checks. This is the supported migration rollback mechanism.
    """

    source = _database_path(backup)
    target = _database_path(destination)
    if not source.is_file():
        raise MigrationError(f"restore backup does not exist: {source}")
    if source == target:
        raise MigrationError("restore backup and destination must be different files")
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        source_connection = _connect_read_only(source)
        try:
            _integrity_check(source_connection, label=str(source))
        finally:
            source_connection.close()
    except (sqlite3.Error, MigrationError) as exc:
        if isinstance(exc, MigrationError):
            raise
        raise MigrationError(f"could not validate restore backup {source}: {exc}") from exc

    safety_backup: Path | None = None
    if target.exists():
        _prepare_existing_destination(target)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        safety_backup = target.with_name(
            f"{target.name}.pre-restore-{timestamp}-{uuid4().hex[:8]}.bak"
        )
        backup_database(target, safety_backup)

    staging = target.with_name(f".{target.name}.restore-{uuid4().hex}")
    try:
        schema_version, checksum = _copy_database(source, staging)
        for suffix in ("-wal", "-shm"):
            Path(f"{target}{suffix}").unlink(missing_ok=True)
        os.replace(staging, target)
        os.chmod(target, 0o600)
    except (OSError, sqlite3.Error, MigrationError) as exc:
        staging.unlink(missing_ok=True)
        if isinstance(exc, MigrationError):
            raise
        raise MigrationError(f"could not restore {source} to {target}: {exc}") from exc

    return RestoreResult(
        backup=str(source),
        destination=str(target),
        schema_version=schema_version,
        sha256=checksum,
        safety_backup=str(safety_backup) if safety_backup is not None else None,
        restored_at=_utc_now(),
    )


__all__ = [
    "BackupResult",
    "LATEST_VERSION",
    "MigrationError",
    "MigrationResult",
    "MigrationStatus",
    "RestoreResult",
    "backup_database",
    "migration_status",
    "restore_database",
    "upgrade_database",
]
