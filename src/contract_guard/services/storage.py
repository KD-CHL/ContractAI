"""SQLite persistence with organization and session isolation.

The repository deliberately stores the domain report as JSON.  This keeps the
platform layer independent from the review model's implementation while still
supporting typed dataclasses and Pydantic models at the boundary.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, date, datetime, timedelta
from enum import Enum, StrEnum
from pathlib import Path
from threading import RLock
from typing import Any, Protocol
from uuid import UUID, uuid4

from contract_guard.domain.operations import (
    UNSET,
    ApprovalBlocked,
    AssignmentError,
    InvalidTransition,
    ReviewDecisionStatus,
    ReviewNotFound,
    StateConflict,
    UnsetType,
    WorkItemKind,
    WorkItemNotFound,
    initial_work_status,
    require_aware_due_at,
    terminal_work_statuses,
    validate_review_transition,
    validate_work_transition,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict") and callable(value.dict):
        return value.dict()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    raise TypeError(f"value of type {type(value).__name__} is not JSON serializable")


def to_jsonable(value: Any) -> Any:
    """Convert common domain objects into detached JSON-compatible data."""

    return json.loads(json.dumps(value, default=_json_default, ensure_ascii=False))


def _encode_json(value: Any) -> str:
    return json.dumps(value, default=_json_default, ensure_ascii=False, separators=(",", ":"))


def _decode_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else {"value": decoded}


def _validate_scope(org_id: str, session_id: str) -> None:
    if not org_id.strip():
        raise ValueError("org_id cannot be empty")
    if not session_id.strip():
        raise ValueError("session_id cannot be empty")


@dataclass(frozen=True, slots=True)
class StoredReview:
    id: str
    org_id: str
    session_id: str
    status: str
    fingerprint: str
    document_name: str
    media_type: str
    contract_id: str | None
    report: dict[str, Any]
    metadata: dict[str, Any]
    error: str | None
    created_at: datetime
    updated_at: datetime
    created_by_user_id: str | None = None
    deleted_at: datetime | None = None
    decision_status: str = "draft"
    state_version: int = 1
    analysis_version: str = "contractguard-review-v1"


class ReviewStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class StoredFeedback:
    id: str
    review_id: str
    org_id: str
    session_id: str
    rating: int | None
    accepted: bool | None
    finding_id: str | None
    comment: str | None
    metadata: dict[str, Any]
    created_at: datetime


class MemoryLayer(StrEnum):
    """Supported memory horizons for review context and learning signals."""

    GLOBAL = "global"
    SHORT_TERM = "short_term"
    PROFILE = "profile"
    EPISODIC = "episodic"


@dataclass(frozen=True, slots=True)
class StoredMemory:
    id: str
    org_id: str
    session_id: str | None
    layer: MemoryLayer
    key: str
    content: Any
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StoredWorkItem:
    id: str
    org_id: str
    review_id: str
    kind: WorkItemKind
    source_id: str | None
    source_ordinal: int
    title: str
    source_payload: dict[str, Any]
    risk_level: str | None
    status: str
    assignee_user_id: str | None
    due_at: datetime | None
    note: str | None
    state_version: int
    created_by_user_id: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class StoredWorkItemEvent:
    id: str
    org_id: str
    review_id: str
    work_item_id: str
    actor_user_id: str | None
    action: str
    from_status: str | None
    to_status: str | None
    changes: dict[str, Any]
    note: str | None
    state_version: int
    created_at: datetime


class ReviewRepository(Protocol):
    def create_review(
        self,
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        document_name: str,
        media_type: str,
        contract_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        review_id: str | None = None,
        status: str = "processing",
        created_by_user_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> StoredReview: ...

    def get_review(
        self, review_id: str, *, org_id: str, session_id: str
    ) -> StoredReview | None: ...

    def upsert_memory(
        self,
        *,
        org_id: str,
        session_id: str | None,
        layer: MemoryLayer | str,
        key: str,
        content: Any,
        metadata: Mapping[str, Any] | None = None,
    ) -> StoredMemory: ...

    def list_memories(
        self,
        *,
        org_id: str,
        session_id: str | None,
        layer: MemoryLayer | str | None = None,
        limit: int = 100,
    ) -> Sequence[StoredMemory]: ...

    def update_review(
        self,
        review_id: str,
        *,
        org_id: str,
        session_id: str,
        status: str,
        report: Any | None = None,
        error: str | None = None,
    ) -> StoredReview | None: ...

    def list_work_items(
        self,
        *,
        org_id: str,
        page: int = 1,
        page_size: int = 20,
        kind: WorkItemKind | str | None = None,
        status: str | None = None,
        assignee_user_id: str | None | UnsetType = UNSET,
        overdue: bool = False,
        risk_level: str | None = None,
        review_id: str | None = None,
    ) -> tuple[Sequence[StoredWorkItem], int]: ...

    def list_review_work_items(
        self, review_id: str, *, org_id: str
    ) -> Sequence[StoredWorkItem]: ...

    def get_work_item(self, work_item_id: str, *, org_id: str) -> StoredWorkItem | None: ...

    def list_work_item_events(
        self, work_item_id: str, *, org_id: str
    ) -> Sequence[StoredWorkItemEvent]: ...

    def operations_summary(self, *, org_id: str, user_id: str | None) -> dict[str, int]: ...


class SQLiteReviewRepository:
    """Small, thread-safe repository backed by a single SQLite database."""

    def __init__(self, path: str | Path = "data/contractguard.db") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            self.path = str(Path(self.path).expanduser().resolve())
        self._lock = RLock()
        self._connection = sqlite3.connect(
            self.path,
            check_same_thread=False,
            isolation_level=None,
            timeout=10,
        )
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA busy_timeout = 10000")
            if self.path != ":memory:":
                self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.executescript(
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
                );

                CREATE INDEX IF NOT EXISTS idx_reviews_scope_id
                    ON reviews (org_id, session_id, id);
                CREATE INDEX IF NOT EXISTS idx_reviews_scope_fingerprint
                    ON reviews (org_id, session_id, fingerprint, updated_at DESC);

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
                );

                CREATE INDEX IF NOT EXISTS idx_feedback_scope_review
                    ON review_feedback (org_id, session_id, review_id, created_at);

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
                );

                CREATE INDEX IF NOT EXISTS idx_memories_scope_layer
                    ON memories (org_id, session_id, layer, updated_at DESC);

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
                    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_work_items_org_assignee_status_due
                    ON work_items (org_id, assignee_user_id, status, due_at);
                CREATE INDEX IF NOT EXISTS idx_work_items_review_kind_updated
                    ON work_items (review_id, kind, updated_at DESC, id);
                CREATE INDEX IF NOT EXISTS idx_work_items_org_risk_status
                    ON work_items (org_id, kind, risk_level, status);

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
                    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
                    FOREIGN KEY (work_item_id) REFERENCES work_items(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_work_item_events_item_created
                    ON work_item_events (org_id, work_item_id, created_at DESC, id DESC);
                """
            )
            # In-memory repositories cannot be upgraded through a second
            # connection. Keep their review table aligned with the additive V2
            # columns used by the catalog APIs.
            existing_columns = {
                str(row["name"])
                for row in self._connection.execute("PRAGMA table_info(reviews)").fetchall()
            }
            additions = (
                ("created_by_user_id", "TEXT"),
                ("deleted_at", "TEXT"),
                ("decision_status", "TEXT NOT NULL DEFAULT 'draft'"),
                ("state_version", "INTEGER NOT NULL DEFAULT 1"),
                (
                    "analysis_version",
                    "TEXT NOT NULL DEFAULT 'contractguard-review-v1'",
                ),
                ("idempotency_key", "TEXT"),
            )
            for column, definition in additions:
                if column not in existing_columns:
                    self._connection.execute(
                        f"ALTER TABLE reviews ADD COLUMN {column} {definition}"
                    )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> SQLiteReviewRepository:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def healthcheck(self) -> bool:
        try:
            with self._lock:
                value = self._connection.execute("SELECT 1").fetchone()
            return bool(value and value[0] == 1)
        except sqlite3.Error:
            return False

    def create_review(
        self,
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        document_name: str,
        media_type: str,
        contract_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        review_id: str | None = None,
        status: str = "processing",
        created_by_user_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> StoredReview:
        _validate_scope(org_id, session_id)
        if not fingerprint:
            raise ValueError("fingerprint cannot be empty")
        _validate_review_status(status)
        identifier = review_id or str(uuid4())
        now = _utc_now().isoformat()
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute(
                    """
                    INSERT INTO reviews (
                        id, org_id, session_id, contract_id, fingerprint,
                        document_name, media_type, status, report_json,
                        metadata_json, error, created_at, updated_at,
                        created_by_user_id, idempotency_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, NULL, ?, ?, ?, ?)
                    """,
                    (
                        identifier,
                        org_id,
                        session_id,
                        contract_id,
                        fingerprint,
                        document_name,
                        media_type,
                        status,
                        _encode_json(dict(metadata or {})),
                        now,
                        now,
                        created_by_user_id,
                        idempotency_key,
                    ),
                )
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise
        created = self.get_review(identifier, org_id=org_id, session_id=session_id)
        if created is None:  # pragma: no cover - protects repository invariant
            raise RuntimeError("created review could not be read back")
        return created

    def get_review(self, review_id: str, *, org_id: str, session_id: str) -> StoredReview | None:
        _validate_scope(org_id, session_id)
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM reviews
                WHERE id = ? AND org_id = ? AND session_id = ?
                """,
                (review_id, org_id, session_id),
            ).fetchone()
        return self._row_to_review(row) if row is not None else None

    def find_completed_by_fingerprint(
        self, fingerprint: str, *, org_id: str, session_id: str
    ) -> StoredReview | None:
        _validate_scope(org_id, session_id)
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM reviews
                WHERE fingerprint = ? AND org_id = ? AND session_id = ?
                  AND status = 'completed'
                ORDER BY updated_at DESC LIMIT 1
                """,
                (fingerprint, org_id, session_id),
            ).fetchone()
        return self._row_to_review(row) if row is not None else None

    def update_review(
        self,
        review_id: str,
        *,
        org_id: str,
        session_id: str,
        status: str,
        report: Any | None = None,
        error: str | None = None,
    ) -> StoredReview | None:
        _validate_scope(org_id, session_id)
        _validate_review_status(status)
        now = _utc_now().isoformat()
        report_data = to_jsonable(report) if report is not None else None
        report_json = _encode_json(report_data) if report is not None else None
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                if report_json is None:
                    cursor = self._connection.execute(
                        """
                        UPDATE reviews
                        SET status = ?, error = ?, updated_at = ?
                        WHERE id = ? AND org_id = ? AND session_id = ?
                        """,
                        (status, error, now, review_id, org_id, session_id),
                    )
                else:
                    cursor = self._connection.execute(
                        """
                        UPDATE reviews
                        SET status = ?, report_json = ?, error = ?, updated_at = ?
                        WHERE id = ? AND org_id = ? AND session_id = ?
                        """,
                        (
                            status,
                            report_json,
                            error,
                            now,
                            review_id,
                            org_id,
                            session_id,
                        ),
                    )
                if cursor.rowcount > 0 and status == ReviewStatus.COMPLETED.value:
                    row = self._connection.execute(
                        """
                        SELECT report_json, created_by_user_id, created_at
                        FROM reviews WHERE id = ? AND org_id = ? AND session_id = ?
                        """,
                        (review_id, org_id, session_id),
                    ).fetchone()
                    if row is not None:
                        try:
                            persisted_report: Any = json.loads(str(row["report_json"]))
                        except (json.JSONDecodeError, TypeError):
                            persisted_report = {}
                        self._materialize_work_items_locked(
                            review_id=review_id,
                            org_id=org_id,
                            report=persisted_report,
                            created_by_user_id=row["created_by_user_id"],
                            created_at=str(row["created_at"]),
                            updated_at=now,
                        )
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise
        if cursor.rowcount == 0:
            return None
        return self.get_review(review_id, org_id=org_id, session_id=session_id)

    def _materialize_work_items_locked(
        self,
        *,
        review_id: str,
        org_id: str,
        report: Any,
        created_by_user_id: str | None,
        created_at: str,
        updated_at: str,
    ) -> None:
        if not isinstance(report, Mapping):
            return
        # Auth-disabled legacy mode can create a new header-scoped organization
        # after V2 has already backfilled organizations. V3 work items use a
        # real organization foreign key, so adopt that scope before inserting
        # the derived queue rows. Authenticated organizations already exist and
        # are left untouched. The in-memory test schema has no organizations
        # table and therefore needs no adoption.
        organizations_exists = self._connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'organizations'"
        ).fetchone()
        if organizations_exists is not None:
            organization_exists = self._connection.execute(
                "SELECT 1 FROM organizations WHERE id = ?",
                (org_id,),
            ).fetchone()
            if organization_exists is None:
                self._connection.execute(
                    """
                    INSERT INTO organizations (
                        id, name, slug, status, created_at, updated_at
                    ) VALUES (?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        org_id,
                        org_id,
                        f"legacy-{uuid4().hex}",
                        created_at,
                        updated_at,
                    ),
                )
        for kind, key in (
            (WorkItemKind.FINDING, "findings"),
            (WorkItemKind.OBLIGATION, "obligations"),
        ):
            raw_items: Any = report.get(key, [])
            if isinstance(raw_items, Mapping):
                raw_items = raw_items.get("items", [])
            if not isinstance(raw_items, list):
                continue
            for ordinal, raw_item in enumerate(raw_items):
                item = dict(raw_item) if isinstance(raw_item, Mapping) else {"value": raw_item}
                source_key = "finding_id" if kind is WorkItemKind.FINDING else "obligation_id"
                raw_source_id = item.get(source_key)
                source_id = str(raw_source_id).strip() if raw_source_id is not None else None
                if not source_id:
                    source_id = None
                raw_title = (
                    item.get("title") if kind is WorkItemKind.FINDING else item.get("action")
                )
                title = str(raw_title).strip() if raw_title is not None else ""
                if not title:
                    label = "风险" if kind is WorkItemKind.FINDING else "义务"
                    title = f"{label} {ordinal + 1}"
                raw_risk = item.get("risk_level") if kind is WorkItemKind.FINDING else None
                risk_level = str(raw_risk).strip() if raw_risk is not None else None
                if not risk_level:
                    risk_level = None
                status = initial_work_status(kind)
                work_item_id = str(uuid4())
                cursor = self._connection.execute(
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
                        org_id,
                        review_id,
                        kind.value,
                        source_id,
                        ordinal,
                        title,
                        _encode_json(item),
                        risk_level,
                        status,
                        created_by_user_id,
                        created_at,
                        updated_at,
                    ),
                )
                if cursor.rowcount == 0:
                    continue
                self._connection.execute(
                    """
                    INSERT INTO work_item_events (
                        id, org_id, review_id, work_item_id, actor_user_id,
                        action, from_status, to_status, changes_json, note,
                        state_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, 'materialized', NULL, ?, '{}', NULL, 1, ?)
                    """,
                    (
                        str(uuid4()),
                        org_id,
                        review_id,
                        work_item_id,
                        created_by_user_id,
                        status,
                        updated_at,
                    ),
                )

    def get_review_for_actor(
        self,
        review_id: str,
        *,
        org_id: str,
        user_id: str | None,
        can_manage_all: bool,
        include_deleted: bool = False,
    ) -> StoredReview | None:
        _validate_org(org_id)
        clauses = ["id = ?", "org_id = ?"]
        parameters: list[Any] = [review_id, org_id]
        if not include_deleted:
            clauses.append("deleted_at IS NULL")
        if not can_manage_all:
            clauses.append("created_by_user_id = ?")
            parameters.append(user_id or "")
        with self._lock:
            row = self._connection.execute(
                f"SELECT * FROM reviews WHERE {' AND '.join(clauses)}",  # noqa: S608
                parameters,
            ).fetchone()
        return self._row_to_review(row) if row is not None else None

    def list_reviews(
        self,
        *,
        org_id: str,
        user_id: str | None,
        can_manage_all: bool,
        page: int = 1,
        page_size: int = 20,
        query: str | None = None,
        status: str | None = None,
        include_deleted: bool = False,
        sort: str = "updated_desc",
    ) -> tuple[Sequence[StoredReview], int]:
        _validate_org(org_id)
        if page < 1:
            raise ValueError("page must be at least 1")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")
        clauses = ["org_id = ?"]
        parameters: list[Any] = [org_id]
        if not can_manage_all:
            clauses.append("created_by_user_id = ?")
            parameters.append(user_id or "")
        if not include_deleted:
            clauses.append("deleted_at IS NULL")
        if status:
            _validate_review_status(status)
            clauses.append("status = ?")
            parameters.append(status)
        if query and query.strip():
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("(document_name LIKE ? ESCAPE '\\' OR contract_id LIKE ? ESCAPE '\\')")
            search = f"%{escaped}%"
            parameters.extend((search, search))
        order_by = {
            "updated_desc": "updated_at DESC, id DESC",
            "updated_asc": "updated_at ASC, id ASC",
            "created_desc": "created_at DESC, id DESC",
            "created_asc": "created_at ASC, id ASC",
        }.get(sort)
        if order_by is None:
            raise ValueError("unsupported review sort")
        where = " AND ".join(clauses)
        with self._lock:
            total = int(
                self._connection.execute(
                    f"SELECT COUNT(*) FROM reviews WHERE {where}",  # noqa: S608
                    parameters,
                ).fetchone()[0]
            )
            rows = self._connection.execute(
                f"""
                SELECT * FROM reviews WHERE {where}
                ORDER BY {order_by} LIMIT ? OFFSET ?
                """,  # noqa: S608
                (*parameters, page_size, (page - 1) * page_size),
            ).fetchall()
        return tuple(self._row_to_review(row) for row in rows), total

    def soft_delete_review(
        self,
        review_id: str,
        *,
        org_id: str,
        user_id: str | None,
        can_manage_all: bool,
    ) -> bool:
        clauses = ["id = ?", "org_id = ?", "deleted_at IS NULL"]
        parameters: list[Any] = [review_id, org_id]
        if not can_manage_all:
            clauses.append("created_by_user_id = ?")
            parameters.append(user_id or "")
        now = _utc_now().isoformat()
        with self._lock:
            cursor = self._connection.execute(
                f"""
                UPDATE reviews SET deleted_at = ?, updated_at = ?, state_version = state_version + 1
                WHERE {" AND ".join(clauses)}
                """,  # noqa: S608
                (now, now, *parameters),
            )
        return cursor.rowcount > 0

    def review_statistics(
        self,
        *,
        org_id: str,
        user_id: str | None,
        can_manage_all: bool,
    ) -> dict[str, Any]:
        clauses = ["org_id = ?", "deleted_at IS NULL"]
        parameters: list[Any] = [org_id]
        if not can_manage_all:
            clauses.append("created_by_user_id = ?")
            parameters.append(user_id or "")
        where = " AND ".join(clauses)
        with self._lock:
            rows = self._connection.execute(
                f"""
                SELECT status, COUNT(*) AS item_count
                FROM reviews WHERE {where} GROUP BY status
                """,  # noqa: S608
                parameters,
            ).fetchall()
            high_risk = int(
                self._connection.execute(
                    f"""
                    SELECT COUNT(*) FROM reviews WHERE {where}
                    AND json_extract(report_json, '$.summary.highest_risk_level')
                        IN ('high', 'critical')
                    """,  # noqa: S608
                    parameters,
                ).fetchone()[0]
            )
        status_counts = {str(row["status"]): int(row["item_count"]) for row in rows}
        return {
            "total": sum(status_counts.values()),
            "completed": status_counts.get(ReviewStatus.COMPLETED.value, 0),
            "failed": status_counts.get(ReviewStatus.FAILED.value, 0),
            "high_risk": high_risk,
            "status_counts": status_counts,
        }

    def restore_review(
        self,
        review_id: str,
        *,
        org_id: str,
        user_id: str | None,
        can_manage_all: bool,
    ) -> bool:
        clauses = ["id = ?", "org_id = ?", "deleted_at IS NOT NULL"]
        parameters: list[Any] = [review_id, org_id]
        if not can_manage_all:
            clauses.append("created_by_user_id = ?")
            parameters.append(user_id or "")
        now = _utc_now().isoformat()
        with self._lock:
            cursor = self._connection.execute(
                f"""
                UPDATE reviews SET deleted_at = NULL, updated_at = ?,
                    state_version = state_version + 1
                WHERE {" AND ".join(clauses)}
                """,  # noqa: S608
                (now, *parameters),
            )
        return cursor.rowcount > 0

    def delete_review(self, review_id: str, *, org_id: str, session_id: str) -> bool:
        _validate_scope(org_id, session_id)
        with self._lock:
            cursor = self._connection.execute(
                "DELETE FROM reviews WHERE id = ? AND org_id = ? AND session_id = ?",
                (review_id, org_id, session_id),
            )
        return cursor.rowcount > 0

    def add_feedback(
        self,
        review_id: str,
        *,
        org_id: str,
        session_id: str,
        rating: int | None = None,
        accepted: bool | None = None,
        finding_id: str | None = None,
        comment: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        feedback_id: str | None = None,
    ) -> StoredFeedback | None:
        _validate_scope(org_id, session_id)
        if rating is not None and not 1 <= rating <= 5:
            raise ValueError("rating must be between 1 and 5")
        identifier = feedback_id or str(uuid4())
        created_at = _utc_now().isoformat()

        # The scoped INSERT ... SELECT prevents feedback from being attached to
        # another tenant's review even if its opaque id becomes known.
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT INTO review_feedback (
                    id, review_id, org_id, session_id, rating, accepted,
                    finding_id, comment, metadata_json, created_at
                )
                SELECT ?, id, org_id, session_id, ?, ?, ?, ?, ?, ?
                FROM reviews
                WHERE id = ? AND org_id = ? AND session_id = ?
                """,
                (
                    identifier,
                    rating,
                    None if accepted is None else int(accepted),
                    finding_id,
                    comment,
                    _encode_json(dict(metadata or {})),
                    created_at,
                    review_id,
                    org_id,
                    session_id,
                ),
            )
        if cursor.rowcount == 0:
            return None
        return StoredFeedback(
            id=identifier,
            review_id=review_id,
            org_id=org_id,
            session_id=session_id,
            rating=rating,
            accepted=accepted,
            finding_id=finding_id,
            comment=comment,
            metadata=dict(metadata or {}),
            created_at=datetime.fromisoformat(created_at),
        )

    def list_feedback(
        self, review_id: str, *, org_id: str, session_id: str
    ) -> Sequence[StoredFeedback]:
        _validate_scope(org_id, session_id)
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM review_feedback
                WHERE review_id = ? AND org_id = ? AND session_id = ?
                ORDER BY created_at ASC
                """,
                (review_id, org_id, session_id),
            ).fetchall()
        return tuple(self._row_to_feedback(row) for row in rows)

    def list_obligations(
        self, review_id: str, *, org_id: str, session_id: str
    ) -> list[dict[str, Any]] | None:
        review = self.get_review(review_id, org_id=org_id, session_id=session_id)
        if review is None:
            return None
        value: Any = review.report.get("obligations", [])
        if isinstance(value, Mapping):
            value = value.get("items", [])
        if not isinstance(value, list):
            return []
        return [dict(item) if isinstance(item, Mapping) else {"value": item} for item in value]

    def get_work_item(self, work_item_id: str, *, org_id: str) -> StoredWorkItem | None:
        _validate_org(org_id)
        with self._lock:
            row = self._connection.execute(
                """
                SELECT work_items.* FROM work_items
                JOIN reviews ON reviews.id = work_items.review_id
                WHERE work_items.id = ? AND work_items.org_id = ?
                  AND reviews.org_id = ? AND reviews.deleted_at IS NULL
                """,
                (work_item_id, org_id, org_id),
            ).fetchone()
        return self._row_to_work_item(row) if row is not None else None

    def list_review_work_items(self, review_id: str, *, org_id: str) -> Sequence[StoredWorkItem]:
        _validate_org(org_id)
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT work_items.* FROM work_items
                JOIN reviews ON reviews.id = work_items.review_id
                WHERE work_items.review_id = ? AND work_items.org_id = ?
                  AND reviews.org_id = ? AND reviews.deleted_at IS NULL
                ORDER BY work_items.kind, work_items.source_ordinal, work_items.id
                """,
                (review_id, org_id, org_id),
            ).fetchall()
        return tuple(self._row_to_work_item(row) for row in rows)

    def list_work_items(
        self,
        *,
        org_id: str,
        page: int = 1,
        page_size: int = 20,
        kind: WorkItemKind | str | None = None,
        status: str | None = None,
        assignee_user_id: str | None | UnsetType = UNSET,
        overdue: bool = False,
        risk_level: str | None = None,
        review_id: str | None = None,
    ) -> tuple[Sequence[StoredWorkItem], int]:
        _validate_org(org_id)
        if page < 1:
            raise ValueError("page must be at least 1")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")
        resolved_kind: WorkItemKind | None = None
        if kind is not None:
            try:
                resolved_kind = WorkItemKind(kind)
            except ValueError as exc:
                raise ValueError("kind must be finding or obligation") from exc
        if status is not None:
            _validate_work_item_filter_status(status, kind=resolved_kind)
        clauses = [
            "work_items.org_id = ?",
            "reviews.org_id = ?",
            "reviews.deleted_at IS NULL",
        ]
        parameters: list[Any] = [org_id, org_id]
        if resolved_kind is not None:
            clauses.append("work_items.kind = ?")
            parameters.append(resolved_kind.value)
        if status is not None:
            clauses.append("work_items.status = ?")
            parameters.append(status)
        if assignee_user_id is not UNSET:
            if assignee_user_id is None:
                clauses.append("work_items.assignee_user_id IS NULL")
            else:
                clauses.append("work_items.assignee_user_id = ?")
                parameters.append(assignee_user_id)
        if overdue:
            clauses.extend(
                (
                    "work_items.due_at IS NOT NULL",
                    "work_items.due_at < ?",
                    "work_items.completed_at IS NULL",
                )
            )
            parameters.append(_utc_now().isoformat())
        if risk_level is not None:
            clauses.append("work_items.risk_level = ?")
            parameters.append(risk_level)
        if review_id is not None:
            clauses.append("work_items.review_id = ?")
            parameters.append(review_id)
        where = " AND ".join(clauses)
        with self._lock:
            total = int(
                self._connection.execute(
                    f"""
                    SELECT COUNT(*) FROM work_items
                    JOIN reviews ON reviews.id = work_items.review_id
                    WHERE {where}
                    """,  # noqa: S608
                    parameters,
                ).fetchone()[0]
            )
            rows = self._connection.execute(
                f"""
                SELECT work_items.* FROM work_items
                JOIN reviews ON reviews.id = work_items.review_id
                WHERE {where}
                ORDER BY
                    CASE WHEN work_items.due_at IS NULL THEN 1 ELSE 0 END,
                    work_items.due_at ASC,
                    work_items.updated_at DESC,
                    work_items.id
                LIMIT ? OFFSET ?
                """,  # noqa: S608
                (*parameters, page_size, (page - 1) * page_size),
            ).fetchall()
        return tuple(self._row_to_work_item(row) for row in rows), total

    def list_work_item_events(
        self, work_item_id: str, *, org_id: str
    ) -> Sequence[StoredWorkItemEvent]:
        _validate_org(org_id)
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT work_item_events.* FROM work_item_events
                JOIN work_items ON work_items.id = work_item_events.work_item_id
                JOIN reviews ON reviews.id = work_items.review_id
                WHERE work_item_events.work_item_id = ?
                  AND work_item_events.org_id = ?
                  AND work_items.org_id = ?
                  AND reviews.org_id = ?
                  AND reviews.deleted_at IS NULL
                ORDER BY work_item_events.created_at ASC, work_item_events.id ASC
                """,
                (work_item_id, org_id, org_id, org_id),
            ).fetchall()
        return tuple(self._row_to_work_item_event(row) for row in rows)

    def operations_summary(self, *, org_id: str, user_id: str | None) -> dict[str, int]:
        _validate_org(org_id)
        now = _utc_now()
        week_ago = now - timedelta(days=7)
        with self._lock:
            row = self._connection.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN work_items.assignee_user_id = ?
                        AND work_items.completed_at IS NULL THEN 1 ELSE 0 END), 0)
                        AS assigned_to_me,
                    COALESCE(SUM(CASE WHEN work_items.due_at IS NOT NULL
                        AND work_items.due_at < ? AND work_items.completed_at IS NULL
                        THEN 1 ELSE 0 END), 0) AS overdue,
                    COALESCE(SUM(CASE WHEN work_items.kind = 'finding'
                        AND work_items.completed_at IS NULL THEN 1 ELSE 0 END), 0)
                        AS open_findings,
                    COALESCE(SUM(CASE WHEN work_items.kind = 'obligation'
                        AND work_items.completed_at IS NULL THEN 1 ELSE 0 END), 0)
                        AS pending_obligations,
                    COALESCE(SUM(CASE WHEN work_items.kind = 'finding'
                        AND work_items.risk_level IN ('high', 'critical')
                        AND work_items.completed_at IS NULL THEN 1 ELSE 0 END), 0)
                        AS open_high_risk,
                    COALESCE(SUM(CASE WHEN work_items.completed_at >= ?
                        THEN 1 ELSE 0 END), 0) AS completed_this_week
                FROM work_items
                JOIN reviews ON reviews.id = work_items.review_id
                WHERE work_items.org_id = ? AND reviews.org_id = ?
                  AND reviews.deleted_at IS NULL
                """,
                (
                    user_id or "",
                    now.isoformat(),
                    week_ago.isoformat(),
                    org_id,
                    org_id,
                ),
            ).fetchone()
            pending_approvals = int(
                self._connection.execute(
                    """
                    SELECT COUNT(*) FROM reviews
                    WHERE org_id = ? AND deleted_at IS NULL
                      AND status = 'completed' AND decision_status = 'in_review'
                    """,
                    (org_id,),
                ).fetchone()[0]
            )
        return {
            "assigned_to_me": int(row["assigned_to_me"]),
            "overdue": int(row["overdue"]),
            "open_findings": int(row["open_findings"]),
            "pending_obligations": int(row["pending_obligations"]),
            "open_high_risk": int(row["open_high_risk"]),
            "pending_approvals": pending_approvals,
            "completed_this_week": int(row["completed_this_week"]),
        }

    def update_work_item(
        self,
        work_item_id: str,
        *,
        org_id: str,
        expected_version: int,
        status: str | UnsetType = UNSET,
        assignee_user_id: str | None | UnsetType = UNSET,
        due_at: datetime | None | UnsetType = UNSET,
        note: str | None | UnsetType = UNSET,
        actor_user_id: str | None = None,
    ) -> StoredWorkItem:
        _validate_org(org_id)
        if expected_version < 1:
            raise ValueError("expected_version must be at least 1")
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._connection.execute(
                    """
                    SELECT work_items.* FROM work_items
                    JOIN reviews ON reviews.id = work_items.review_id
                    WHERE work_items.id = ? AND work_items.org_id = ?
                      AND reviews.org_id = ? AND reviews.deleted_at IS NULL
                    """,
                    (work_item_id, org_id, org_id),
                ).fetchone()
                if row is None:
                    raise WorkItemNotFound("work item not found")
                current = self._row_to_work_item(row)
                if current.state_version != expected_version:
                    raise StateConflict(expected=expected_version, current=current.state_version)

                next_status = current.status if isinstance(status, UnsetType) else status
                action_note = None if isinstance(note, UnsetType) else note
                if next_status != current.status:
                    validate_work_transition(
                        current.kind,
                        current=current.status,
                        target=next_status,
                        note=action_note,
                    )

                next_assignee = (
                    current.assignee_user_id
                    if isinstance(assignee_user_id, UnsetType)
                    else assignee_user_id
                )
                if next_assignee is not None and not isinstance(assignee_user_id, UnsetType):
                    self._validate_assignee_locked(org_id=org_id, user_id=next_assignee)

                next_due = current.due_at if isinstance(due_at, UnsetType) else due_at
                if not isinstance(due_at, UnsetType):
                    require_aware_due_at(next_due)
                    if next_due is not None:
                        next_due = next_due.astimezone(UTC)
                next_note = current.note if isinstance(note, UnsetType) else note

                changes: dict[str, Any] = {}
                for field, before, after in (
                    ("status", current.status, next_status),
                    ("assignee_user_id", current.assignee_user_id, next_assignee),
                    ("due_at", current.due_at, next_due),
                    ("note", current.note, next_note),
                ):
                    if before != after:
                        changes[field] = {
                            "before": to_jsonable(before),
                            "after": to_jsonable(after),
                        }
                if not changes:
                    raise ValueError("work item update must change at least one field")

                now = _utc_now()
                completed_at = current.completed_at
                if next_status != current.status:
                    completed_at = (
                        now if next_status in terminal_work_statuses(current.kind) else None
                    )
                next_version = current.state_version + 1
                cursor = self._connection.execute(
                    """
                    UPDATE work_items SET
                        status = ?, assignee_user_id = ?, due_at = ?, note = ?,
                        state_version = ?, updated_at = ?, completed_at = ?
                    WHERE id = ? AND org_id = ? AND state_version = ?
                    """,
                    (
                        next_status,
                        next_assignee,
                        next_due.isoformat() if next_due is not None else None,
                        next_note,
                        next_version,
                        now.isoformat(),
                        completed_at.isoformat() if completed_at is not None else None,
                        work_item_id,
                        org_id,
                        expected_version,
                    ),
                )
                if cursor.rowcount == 0:
                    latest = self._connection.execute(
                        "SELECT state_version FROM work_items WHERE id = ? AND org_id = ?",
                        (work_item_id, org_id),
                    ).fetchone()
                    if latest is None:
                        raise WorkItemNotFound("work item not found")
                    raise StateConflict(expected=expected_version, current=int(latest[0]))

                if next_status != current.status:
                    action = "status_changed"
                elif next_assignee != current.assignee_user_id:
                    action = "assigned" if next_assignee is not None else "unassigned"
                elif next_due != current.due_at:
                    action = "due_date_changed"
                else:
                    action = "updated"
                self._connection.execute(
                    """
                    INSERT INTO work_item_events (
                        id, org_id, review_id, work_item_id, actor_user_id,
                        action, from_status, to_status, changes_json, note,
                        state_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        org_id,
                        current.review_id,
                        work_item_id,
                        actor_user_id,
                        action,
                        current.status,
                        next_status,
                        _encode_json(changes),
                        action_note,
                        next_version,
                        now.isoformat(),
                    ),
                )
                self._connection.execute(
                    "UPDATE reviews SET updated_at = ? WHERE id = ? AND org_id = ?",
                    (now.isoformat(), current.review_id, org_id),
                )
                updated_row = self._connection.execute(
                    "SELECT * FROM work_items WHERE id = ? AND org_id = ?",
                    (work_item_id, org_id),
                ).fetchone()
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise
        if updated_row is None:  # pragma: no cover - transaction invariant
            raise RuntimeError("updated work item could not be read back")
        return self._row_to_work_item(updated_row)

    def transition_review_decision(
        self,
        review_id: str,
        *,
        org_id: str,
        expected_version: int,
        target_status: ReviewDecisionStatus | str,
        note: str | None = None,
        actor_user_id: str | None = None,
    ) -> StoredReview:
        _validate_org(org_id)
        if expected_version < 1:
            raise ValueError("expected_version must be at least 1")
        target = ReviewDecisionStatus(target_status).value
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._connection.execute(
                    """
                    SELECT * FROM reviews
                    WHERE id = ? AND org_id = ? AND deleted_at IS NULL
                    """,
                    (review_id, org_id),
                ).fetchone()
                if row is None:
                    raise ReviewNotFound("review not found")
                current = self._row_to_review(row)
                if current.state_version != expected_version:
                    raise StateConflict(expected=expected_version, current=current.state_version)
                if current.status != ReviewStatus.COMPLETED.value:
                    raise InvalidTransition(
                        entity="review analysis",
                        current=current.status,
                        target=target,
                    )
                validate_review_transition(
                    current=current.decision_status,
                    target=target,
                    note=note,
                )
                if target == ReviewDecisionStatus.APPROVED.value:
                    blockers = self._connection.execute(
                        """
                        SELECT id FROM work_items
                        WHERE org_id = ? AND review_id = ? AND kind = 'finding'
                          AND risk_level IN ('high', 'critical')
                          AND status NOT IN ('resolved', 'accepted')
                        ORDER BY source_ordinal, id
                        """,
                        (org_id, review_id),
                    ).fetchall()
                    if blockers:
                        raise ApprovalBlocked(tuple(str(item["id"]) for item in blockers))
                now = _utc_now().isoformat()
                cursor = self._connection.execute(
                    """
                    UPDATE reviews SET decision_status = ?, state_version = state_version + 1,
                        updated_at = ?
                    WHERE id = ? AND org_id = ? AND state_version = ?
                    """,
                    (target, now, review_id, org_id, expected_version),
                )
                if cursor.rowcount == 0:
                    latest = self._connection.execute(
                        "SELECT state_version FROM reviews WHERE id = ? AND org_id = ?",
                        (review_id, org_id),
                    ).fetchone()
                    if latest is None:
                        raise ReviewNotFound("review not found")
                    raise StateConflict(expected=expected_version, current=int(latest[0]))
                updated_row = self._connection.execute(
                    "SELECT * FROM reviews WHERE id = ? AND org_id = ?",
                    (review_id, org_id),
                ).fetchone()
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise
        if updated_row is None:  # pragma: no cover - transaction invariant
            raise RuntimeError("updated review could not be read back")
        return self._row_to_review(updated_row)

    def _validate_assignee_locked(self, *, org_id: str, user_id: str) -> None:
        users_table = self._connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        if users_table is None:
            return
        row = self._connection.execute(
            """
            SELECT 1 FROM users
            WHERE id = ? AND org_id = ? AND status = 'active'
            """,
            (user_id, org_id),
        ).fetchone()
        if row is None:
            raise AssignmentError("assignee must be an active member of the organization")

    def upsert_memory(
        self,
        *,
        org_id: str,
        session_id: str | None,
        layer: MemoryLayer | str,
        key: str,
        content: Any,
        metadata: Mapping[str, Any] | None = None,
    ) -> StoredMemory:
        resolved_layer, scoped_session = _memory_scope(
            org_id=org_id, session_id=session_id, layer=layer
        )
        if not key.strip():
            raise ValueError("memory key cannot be empty")
        identifier = str(uuid4())
        now = _utc_now().isoformat()
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO memories (
                    id, org_id, session_id, layer, memory_key, content_json,
                    metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(org_id, session_id, layer, memory_key) DO UPDATE SET
                    content_json = excluded.content_json,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    identifier,
                    org_id,
                    scoped_session,
                    resolved_layer.value,
                    key,
                    _encode_json(content),
                    _encode_json(dict(metadata or {})),
                    now,
                    now,
                ),
            )
        memory = self.retrieve_memory(
            key,
            org_id=org_id,
            session_id=session_id,
            layer=resolved_layer,
        )
        if memory is None:  # pragma: no cover - protects repository invariant
            raise RuntimeError("upserted memory could not be read back")
        return memory

    def retrieve_memory(
        self,
        key: str,
        *,
        org_id: str,
        session_id: str | None,
        layer: MemoryLayer | str,
    ) -> StoredMemory | None:
        resolved_layer, scoped_session = _memory_scope(
            org_id=org_id, session_id=session_id, layer=layer
        )
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM memories
                WHERE org_id = ? AND session_id = ? AND layer = ? AND memory_key = ?
                """,
                (org_id, scoped_session, resolved_layer.value, key),
            ).fetchone()
        return self._row_to_memory(row) if row is not None else None

    get_memory = retrieve_memory

    def list_memories(
        self,
        *,
        org_id: str,
        session_id: str | None,
        layer: MemoryLayer | str | None = None,
        limit: int = 100,
    ) -> Sequence[StoredMemory]:
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if layer is not None:
            resolved_layer, scoped_session = _memory_scope(
                org_id=org_id, session_id=session_id, layer=layer
            )
            query = """
                SELECT * FROM memories
                WHERE org_id = ? AND session_id = ? AND layer = ?
                ORDER BY updated_at DESC, id ASC LIMIT ?
            """
            parameters: tuple[Any, ...] = (
                org_id,
                scoped_session,
                resolved_layer.value,
                limit,
            )
        else:
            _validate_org(org_id)
            if session_id is None or not session_id.strip():
                query = """
                    SELECT * FROM memories
                    WHERE org_id = ? AND layer = 'global' AND session_id = ''
                    ORDER BY updated_at DESC, id ASC LIMIT ?
                """
                parameters = (org_id, limit)
            else:
                query = """
                    SELECT * FROM memories
                    WHERE org_id = ? AND (
                        (layer = 'global' AND session_id = '') OR
                        (layer != 'global' AND session_id = ?)
                    )
                    ORDER BY updated_at DESC, id ASC LIMIT ?
                """
                parameters = (org_id, session_id, limit)
        with self._lock:
            rows = self._connection.execute(query, parameters).fetchall()
        return tuple(self._row_to_memory(row) for row in rows)

    def delete_memory(
        self,
        key: str,
        *,
        org_id: str,
        session_id: str | None,
        layer: MemoryLayer | str,
    ) -> bool:
        resolved_layer, scoped_session = _memory_scope(
            org_id=org_id, session_id=session_id, layer=layer
        )
        with self._lock:
            cursor = self._connection.execute(
                """
                DELETE FROM memories
                WHERE org_id = ? AND session_id = ? AND layer = ? AND memory_key = ?
                """,
                (org_id, scoped_session, resolved_layer.value, key),
            )
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_review(row: sqlite3.Row) -> StoredReview:
        return StoredReview(
            id=row["id"],
            org_id=row["org_id"],
            session_id=row["session_id"],
            status=row["status"],
            fingerprint=row["fingerprint"],
            document_name=row["document_name"],
            media_type=row["media_type"],
            contract_id=row["contract_id"],
            report=_decode_object(row["report_json"]),
            metadata=_decode_object(row["metadata_json"]),
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            created_by_user_id=row["created_by_user_id"],
            deleted_at=(datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None),
            decision_status=row["decision_status"],
            state_version=int(row["state_version"]),
            analysis_version=row["analysis_version"],
        )

    @staticmethod
    def _row_to_feedback(row: sqlite3.Row) -> StoredFeedback:
        accepted = row["accepted"]
        return StoredFeedback(
            id=row["id"],
            review_id=row["review_id"],
            org_id=row["org_id"],
            session_id=row["session_id"],
            rating=row["rating"],
            accepted=None if accepted is None else bool(accepted),
            finding_id=row["finding_id"],
            comment=row["comment"],
            metadata=_decode_object(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> StoredMemory:
        content = json.loads(row["content_json"])
        session_id = row["session_id"]
        return StoredMemory(
            id=row["id"],
            org_id=row["org_id"],
            session_id=session_id or None,
            layer=MemoryLayer(row["layer"]),
            key=row["memory_key"],
            content=content,
            metadata=_decode_object(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_work_item(row: sqlite3.Row) -> StoredWorkItem:
        due_at = row["due_at"]
        completed_at = row["completed_at"]
        return StoredWorkItem(
            id=str(row["id"]),
            org_id=str(row["org_id"]),
            review_id=str(row["review_id"]),
            kind=WorkItemKind(str(row["kind"])),
            source_id=(str(row["source_id"]) if row["source_id"] is not None else None),
            source_ordinal=int(row["source_ordinal"]),
            title=str(row["title"]),
            source_payload=_decode_object(row["source_payload_json"]),
            risk_level=(str(row["risk_level"]) if row["risk_level"] is not None else None),
            status=str(row["status"]),
            assignee_user_id=(
                str(row["assignee_user_id"]) if row["assignee_user_id"] is not None else None
            ),
            due_at=datetime.fromisoformat(str(due_at)) if due_at else None,
            note=str(row["note"]) if row["note"] is not None else None,
            state_version=int(row["state_version"]),
            created_by_user_id=(
                str(row["created_by_user_id"]) if row["created_by_user_id"] is not None else None
            ),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            completed_at=(datetime.fromisoformat(str(completed_at)) if completed_at else None),
        )

    @staticmethod
    def _row_to_work_item_event(row: sqlite3.Row) -> StoredWorkItemEvent:
        return StoredWorkItemEvent(
            id=str(row["id"]),
            org_id=str(row["org_id"]),
            review_id=str(row["review_id"]),
            work_item_id=str(row["work_item_id"]),
            actor_user_id=(str(row["actor_user_id"]) if row["actor_user_id"] is not None else None),
            action=str(row["action"]),
            from_status=(str(row["from_status"]) if row["from_status"] is not None else None),
            to_status=str(row["to_status"]) if row["to_status"] is not None else None,
            changes=_decode_object(row["changes_json"]),
            note=str(row["note"]) if row["note"] is not None else None,
            state_version=int(row["state_version"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )


def _validate_org(org_id: str) -> None:
    if not org_id.strip():
        raise ValueError("org_id cannot be empty")


def _validate_review_status(value: str) -> None:
    try:
        ReviewStatus(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ReviewStatus)
        raise ValueError(f"review status must be one of: {allowed}") from exc


def _validate_work_item_filter_status(value: str, *, kind: WorkItemKind | None) -> None:
    finding_statuses = {"open", "in_progress", "resolved", "accepted"}
    obligation_statuses = {"pending", "in_progress", "completed", "waived"}
    allowed = (
        finding_statuses
        if kind is WorkItemKind.FINDING
        else obligation_statuses
        if kind is WorkItemKind.OBLIGATION
        else finding_statuses | obligation_statuses
    )
    if value not in allowed:
        raise ValueError("unsupported work item status")


def _memory_scope(
    *, org_id: str, session_id: str | None, layer: MemoryLayer | str
) -> tuple[MemoryLayer, str]:
    _validate_org(org_id)
    try:
        resolved_layer = MemoryLayer(layer)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in MemoryLayer)
        raise ValueError(f"memory layer must be one of: {allowed}") from exc
    if resolved_layer is MemoryLayer.GLOBAL:
        return resolved_layer, ""
    if session_id is None or not session_id.strip():
        raise ValueError(f"session_id is required for {resolved_layer.value} memory")
    return resolved_layer, session_id


# Common implementation aliases retained for straightforward dependency wiring.
SQLiteStorage = SQLiteReviewRepository
ReviewStore = SQLiteReviewRepository
