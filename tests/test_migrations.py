from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from contract_guard.infrastructure.db import (
    MigrationError,
    backup_database,
    migration_status,
    restore_database,
    upgrade_database,
)
from contract_guard.services.storage import MemoryLayer, SQLiteReviewRepository


def _table_names(database: Path) -> set[str]:
    with sqlite3.connect(database) as connection:
        return {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }


def _columns(database: Path, table: str) -> set[str]:
    with sqlite3.connect(database) as connection:
        return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def test_empty_database_upgrades_to_v3_with_operational_work_items(tmp_path: Path) -> None:
    database = tmp_path / "empty.db"

    before = migration_status(database)
    result = upgrade_database(database)
    after = migration_status(database)

    assert before.exists is False
    assert before.pending_versions == (1, 2, 3, 4)
    assert result.from_version == 0
    assert result.to_version == 4
    assert result.applied_versions == (1, 2, 3, 4)
    assert after.is_current
    assert {item.version for item in after.applied} == {1, 2, 3, 4}
    assert {
        "schema_migrations",
        "reviews",
        "review_feedback",
        "memories",
        "organizations",
        "users",
        "auth_sessions",
        "audit_logs",
        "finding_actions",
        "work_items",
        "work_item_events",
        "contract_templates",
        "clause_library",
    }.issubset(_table_names(database))
    assert {
        "created_by_user_id",
        "deleted_at",
        "decision_status",
        "state_version",
        "analysis_version",
        "idempotency_key",
    }.issubset(_columns(database, "reviews"))

    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO organizations (id, name, slug, status, created_at, updated_at)
            VALUES ('org-a', 'Org A', 'org-a', 'active', '2026-01-01', '2026-01-01')
            """
        )
        connection.execute(
            """
            INSERT INTO users (
                id, org_id, email, display_name, password_hash, role, status,
                created_at, updated_at
            ) VALUES (
                'user-a', 'org-a', 'Legal@Example.com', 'Legal', 'hash',
                'legal_reviewer', 'active', '2026-01-01', '2026-01-01'
            )
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO users (
                    id, org_id, email, display_name, password_hash, role, status,
                    created_at, updated_at
                ) VALUES (
                    'user-b', 'org-a', 'legal@example.com', 'Duplicate', 'hash',
                    'business_user', 'active', '2026-01-01', '2026-01-01'
                )
                """
            )


def test_unversioned_v1_is_adopted_without_losing_rows(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    repository = SQLiteReviewRepository(database)
    review = repository.create_review(
        org_id="legacy-org",
        session_id="legacy-session",
        fingerprint="legacy-fingerprint",
        document_name="legacy-contract.txt",
        media_type="text/plain",
        contract_id="legacy-contract",
        metadata={"source": "legacy"},
    )
    repository.update_review(
        review.id,
        org_id="legacy-org",
        session_id="legacy-session",
        status="completed",
        report={"contract_id": "legacy-contract", "findings": []},
    )
    feedback = repository.add_feedback(
        review.id,
        org_id="legacy-org",
        session_id="legacy-session",
        rating=5,
        accepted=True,
        comment="keep me",
    )
    memory = repository.upsert_memory(
        org_id="legacy-org",
        session_id="legacy-session",
        layer=MemoryLayer.PROFILE,
        key="legacy-preference",
        content={"language": "zh-CN"},
    )
    repository.close()

    result = upgrade_database(database)

    assert result.applied_versions == (1, 2, 3, 4)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        stored_review = connection.execute(
            "SELECT * FROM reviews WHERE id = ?", (review.id,)
        ).fetchone()
        stored_feedback = connection.execute(
            "SELECT * FROM review_feedback WHERE id = ?", (feedback.id,)
        ).fetchone()
        stored_memory = connection.execute(
            "SELECT * FROM memories WHERE id = ?", (memory.id,)
        ).fetchone()
        organization = connection.execute(
            "SELECT * FROM organizations WHERE id = 'legacy-org'"
        ).fetchone()

    assert stored_review is not None
    assert stored_review["status"] == "completed"
    assert json.loads(stored_review["report_json"])["contract_id"] == "legacy-contract"
    assert stored_review["decision_status"] == "draft"
    assert stored_review["state_version"] == 1
    assert stored_review["analysis_version"] == "contractguard-review-v1"
    assert stored_feedback is not None and stored_feedback["comment"] == "keep me"
    assert stored_memory is not None
    assert json.loads(stored_memory["content_json"]) == {"language": "zh-CN"}
    assert organization is not None and organization["slug"] == "legacy-org"


def test_v3_backfills_completed_report_items_by_ordinal(tmp_path: Path) -> None:
    database = tmp_path / "backfill.db"
    repository = SQLiteReviewRepository(database)
    review = repository.create_review(
        org_id="legacy-org",
        session_id="legacy-session",
        fingerprint="backfill-fingerprint",
        document_name="backfill-contract.txt",
        media_type="text/plain",
    )
    repository.update_review(
        review.id,
        org_id="legacy-org",
        session_id="legacy-session",
        status="completed",
        report={
            "findings": [
                {"finding_id": "duplicate", "title": "风险一", "risk_level": "high"},
                {"finding_id": "duplicate", "title": "风险二", "risk_level": "low"},
            ],
            "obligations": [{"action": "在十日内付款"}],
        },
    )
    repository.close()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE work_item_events")
        connection.execute("DROP TABLE work_items")

    result = upgrade_database(database)

    assert result.applied_versions == (1, 2, 3, 4)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT kind, source_id, source_ordinal, title, status
            FROM work_items ORDER BY kind, source_ordinal
            """
        ).fetchall()
        event_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM work_item_events WHERE action = 'materialized'"
            ).fetchone()[0]
        )

    assert [tuple(row) for row in rows] == [
        ("finding", "duplicate", 0, "风险一", "open"),
        ("finding", "duplicate", 1, "风险二", "open"),
        ("obligation", None, 0, "在十日内付款", "pending"),
    ]
    assert event_count == 3


def test_repeated_upgrade_is_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "repeat.db"

    first = upgrade_database(database)
    second = upgrade_database(database)

    assert first.applied_versions == (1, 2, 3, 4)
    assert second.from_version == 4
    assert second.to_version == 4
    assert second.applied_versions == ()
    assert second.already_current
    with sqlite3.connect(database) as connection:
        count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    assert count == 4


def test_backup_and_restore_preserve_current_database_as_safety_snapshot(tmp_path: Path) -> None:
    database = tmp_path / "restore.db"
    backup = tmp_path / "known-good.db"
    upgrade_database(database)

    repository = SQLiteReviewRepository(database)
    review = repository.create_review(
        org_id="org-a",
        session_id="session-a",
        fingerprint="original",
        document_name="original.txt",
        media_type="text/plain",
    )
    repository.close()
    backup_result = backup_database(database, backup)

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE reviews SET status = 'failed', error = 'later mutation' WHERE id = ?",
            (review.id,),
        )

    restore_result = restore_database(backup, database)

    assert backup_result.schema_version == 4
    assert restore_result.schema_version == 4
    assert restore_result.safety_backup is not None
    assert Path(restore_result.safety_backup).is_file()
    with sqlite3.connect(database) as connection:
        restored = connection.execute(
            "SELECT status, error FROM reviews WHERE id = ?", (review.id,)
        ).fetchone()
    assert restored == ("processing", None)

    with sqlite3.connect(restore_result.safety_backup) as connection:
        preserved_mutation = connection.execute(
            "SELECT status, error FROM reviews WHERE id = ?", (review.id,)
        ).fetchone()
    assert preserved_mutation == ("failed", "later mutation")


def test_backup_never_silently_overwrites_an_existing_file(tmp_path: Path) -> None:
    database = tmp_path / "source.db"
    destination = tmp_path / "existing.db"
    upgrade_database(database)
    destination.write_bytes(b"do not overwrite")

    with pytest.raises(MigrationError, match="refusing to overwrite"):
        backup_database(database, destination)

    assert destination.read_bytes() == b"do not overwrite"
