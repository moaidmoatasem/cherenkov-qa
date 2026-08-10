"""
cherenkov/core/migration.py — Database schema migration runner.
"""

from __future__ import annotations

import logging
import sqlite3
import time

logger = logging.getLogger(__name__)

_SCHEMA_TABLE = "_schema_version"


class SchemaMigration:
    """Manages SQLite schema version tracking and step-wise SQL migrations."""

    db_path: str
    current_version: int
    target_version: int

    def __init__(self, db_path: str, current_version: int = 1, target_version: int = 1):
        """Initialize SchemaMigration.

        Args:
            db_path (str): SQLite database file path.
            current_version (int, optional): Initial expected schema version. Defaults to 1.
            target_version (int, optional): Desired schema version. Defaults to 1.
        """
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
            row = conn.execute(f"SELECT MAX(version) FROM {_SCHEMA_TABLE}").fetchone()
            return row[0] if row and row[0] else 0
        except sqlite3.OperationalError:
            return 0

    def get_applied_version(self) -> int:
        """Fetch the current highest applied schema version from database.

        Returns:
            int: Applied version number.
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            return self._applied_version(conn)
        finally:
            conn.close()

    def needs_migration(self) -> bool:
        """Check whether the applied version is less than the target version.

        Returns:
            bool: True if migration is required, False otherwise.
        """
        return self.get_applied_version() < self.target_version

    def apply(self, migrations: list[tuple[int, str]]) -> bool:
        """Apply pending migrations up to target_version.

        Args:
            migrations (list[tuple[int, str]]): List of (version, sql_script) tuples.

        Returns:
            bool: True if migration succeeded, False on error.
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            applied = self._applied_version(conn)
            for version, sql in migrations:
                if version > applied and version <= self.target_version:
                    logger.info("applying migration v%s", version)
                    conn.executescript(sql)
                    conn.execute(
                        f"INSERT INTO {_SCHEMA_TABLE} (version, applied_at) VALUES (?, ?)",
                        (version, int(time.time())),
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
        """Rollback applied migrations down to current_version.

        Args:
            migrations (list[tuple[int, str]]): List of (version, sql_script) tuples.

        Returns:
            bool: True if rollback succeeded, False on error.
        """
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

