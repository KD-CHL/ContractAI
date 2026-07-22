#!/usr/bin/env python3
"""Operate ContractGuard SQLite migrations and verified backups."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

# Allow direct execution from a source checkout without requiring an editable install.
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from contract_guard.infrastructure.db import (  # noqa: E402
    MigrationError,
    backup_database,
    migration_status,
    restore_database,
    upgrade_database,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Manage versioned ContractGuard SQLite schemas and safe backup-based rollback."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="show applied and pending migrations")
    status_parser.add_argument("--database", required=True, type=Path)

    upgrade_parser = subparsers.add_parser("upgrade", help="upgrade to the latest schema")
    upgrade_parser.add_argument("--database", required=True, type=Path)

    backup_parser = subparsers.add_parser("backup", help="create a verified SQLite backup")
    backup_parser.add_argument("--database", required=True, type=Path)
    backup_parser.add_argument("--destination", required=True, type=Path)

    restore_parser = subparsers.add_parser(
        "restore",
        help="restore a backup; an existing destination is preserved first",
    )
    restore_parser.add_argument("--backup", required=True, type=Path)
    restore_parser.add_argument("--destination", required=True, type=Path)
    return parser


def _render(value: Any) -> str:
    return json.dumps(asdict(value), ensure_ascii=False, indent=2, default=str)


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "status":
            result = migration_status(arguments.database)
        elif arguments.command == "upgrade":
            result = upgrade_database(arguments.database)
        elif arguments.command == "backup":
            result = backup_database(arguments.database, arguments.destination)
        else:
            result = restore_database(arguments.backup, arguments.destination)
    except MigrationError as exc:
        print(f"database operation failed: {exc}", file=sys.stderr)
        return 1

    print(_render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
