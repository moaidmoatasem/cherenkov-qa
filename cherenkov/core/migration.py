from __future__ import annotations

import os
import sqlite3
import logging
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA_TABLE = "_schema_version"


class SchemaMigration:
    db_path: str
    current_version: int
    target_version: int

    def __init__(self, db_path: str, current_version: int = 1, target_version: int = 1):
        self.db_path = db_path
        self.current_version = current_version
        self.target_version = target_version

    def _ensure_schema_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {_SCHEMA_TABLE} ("
            "version INTEGER NOT NULL,"
            "applied_at INTEGER NOT NULL)"
        )

    def _applied_version(self, conn: sqlite3.Connection) -> int:
        """Return the highest applied version using an existing connection."""
        try:
            self._ensure_schema_table(conn)
            row = conn.execute(
                f"SELECT MAX(version) FROM {_SCHEMA_TABLE}"
            ).fetchone()
            return row[0] if row and row[0] else 0
        except sqlite3.OperationalError:
            return 0

    def get_applied_version(self) -> int:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            return self._applied_version(conn)
        finally:
            conn.close()

    def needs_migration(self) -> bool:
        return self.get_applied_version() < self.target_version

    def apply(self, migrations: list[tuple[int, str]]) -> bool:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            applied = self._applied_version(conn)
            for version, sql in migrations:
                if version > applied and version <= self.target_version:
                    logger.info("applying migration v%s", version)
                    conn.executescript(sql)
                    conn.execute(
                        f"INSERT INTO {_SCHEMA_TABLE} (version, applied_at) VALUES (?, ?)",
                        (version, int(__import__("time").time())),
                    )
            conn.commit()
            return True
        except Exception as e:
            logger.error("migration failed", exc_info=e)
            conn.rollback()
            return False
        finally:
            conn.close()

    def rollback(self, migrations: list[tuple[int, str]]) -> bool:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            applied = self._applied_version(conn)
            for version, sql in reversed(migrations):
                if version <= applied and version > self.current_version:
                    logger.info("rolling back migration v%s", version)
                    conn.executescript(sql)
            conn.commit()
            return True
        except Exception as e:
            logger.error("rollback failed", exc_info=e)
            conn.rollback()
            return False
        finally:
            conn.close()
