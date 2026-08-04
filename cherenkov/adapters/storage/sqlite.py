"""
SQLite Storage Adapter (ADR-014) - Unified implementation for all namespaces.

Implements StoragePort for SQLite with namespace isolation and FTS5 support.
Rows are stored as JSON documents (the ``data`` column) alongside a small set
of bookkeeping columns (id, created_at, updated_at, deleted_at, version).

Queries may filter/order by bookkeeping columns directly, or by any key inside
the JSON document via ``json_extract(data, '$.<key>')``.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from cherenkov.ports.storage import (
    QueryFilter,
    StorageConfig,
    StoragePort,
    StorageQuery,
)

_JSON_COLUMN = "data"
_BOOKKEEPING_COLUMNS = {"id", "rowid", "created_at", "updated_at", "deleted_at", "version"}


def _col_expr(column: str) -> str:
    """Map a column name to a SQL expression (real column or JSON path)."""
    if column in _BOOKKEEPING_COLUMNS:
        return column
    return f"json_extract({_JSON_COLUMN}, '$.{column}')"


class SQLiteStorageAdapter(StoragePort):
    """
    SQLite implementation of StoragePort with namespace isolation.

    Features:
    - Per-namespace table prefix (``{namespace}_{table}``)
    - JSON document rows with FTS5 index maintenance via triggers
    - Thread-local connection pooling, WAL mode, busy timeout
    - Schema initialization on first use
    """

    def __init__(self, config: StorageConfig) -> None:
        self.config = config
        self._local = threading.local()
        self._tx_depth = threading.local()
        self.config.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @property
    def namespace(self) -> str:
        """Return the namespace this adapter owns."""
        return self.config.namespace

    def _connect(self) -> sqlite3.Connection:
        """Get or create thread-local connection."""
        con = getattr(self._local, "con", None)
        if con is None:
            con = sqlite3.connect(
                str(self.config.db_path),
                timeout=self.config.busy_timeout_s,
                isolation_level=None,  # manual transactions
            )
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys = ON")
            if self.config.wal_mode:
                con.execute("PRAGMA journal_mode = WAL")
            self._local.con = con
        return con

    def _qualify_table(self, table: str) -> str:
        """Apply namespace prefix to table name."""
        return f"{self.namespace}_{table}"

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Reentrant SQLite transaction context manager."""
        conn = self._connect()
        depth = getattr(self._tx_depth, "depth", 0)
        if depth == 0:
            conn.execute("BEGIN")
        self._tx_depth.depth = depth + 1
        try:
            yield
        except Exception:
            self._tx_depth.depth = depth
            if depth == 0:
                conn.rollback()
            raise
        else:
            self._tx_depth.depth = depth
            if depth == 0:
                conn.commit()

    def close(self) -> None:
        """Close thread-local connection."""
        con = getattr(self._local, "con", None)
        if con is not None:
            con.close()
            self._local.con = None

    # ── StoragePort abstract methods ────────────────────────────────────────

    def init_schema(self) -> None:
        """Initialize tables and indexes for this namespace."""
        conn = self._connect()
        entries = self._qualify_table("entries")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {entries} (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                version INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{self.namespace}_created_at "
            f"ON {entries} (created_at DESC)"
        )
        if self.config.enable_fts and self.config.fts_columns:
            self._init_fts(conn)
        conn.commit()

    def insert(self, table: str, data: dict[str, Any]) -> str:
        """Insert row as JSON document, return row id."""
        row_id = str(data.get("id") or uuid.uuid4().hex)
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(data, default=str)
        qual = self._qualify_table(table)
        with self.transaction():
            self._connect().execute(
                f"INSERT INTO {qual} (id, data, created_at, updated_at, deleted_at, version) "
                "VALUES (?, ?, ?, ?, NULL, 1)",
                (row_id, payload, now, now),
            )
        return row_id

    def upsert(self, table: str, data: dict[str, Any], conflict_key: str) -> str:
        """Insert or update the row whose ``conflict_key`` matches ``data``."""
        qual = self._qualify_table(table)
        conflict_value = data.get(conflict_key)
        existing = None
        if conflict_value is not None:
            row = self._connect().execute(
                f"SELECT id, data FROM {qual} "
                f"WHERE {_col_expr(conflict_key)} = ? AND deleted_at IS NULL LIMIT 1",
                (conflict_value,),
            ).fetchone()
            existing = row

        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(data, default=str)
        with self.transaction():
            conn = self._connect()
            if existing is not None:
                conn.execute(
                    f"UPDATE {qual} SET data = ?, updated_at = ?, version = version + 1 "
                    "WHERE id = ?",
                    (payload, now, existing["id"]),
                )
                return existing["id"]
            row_id = str(data.get("id") or uuid.uuid4().hex)
            conn.execute(
                f"INSERT INTO {qual} (id, data, created_at, updated_at, deleted_at, version) "
                "VALUES (?, ?, ?, ?, NULL, 1)",
                (row_id, payload, now, now),
            )
            return row_id

    def query(
        self,
        table: str,
        query: StorageQuery,
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Query with filters, ordering, pagination (soft-deleted excluded)."""
        qual = self._qualify_table(table)
        select = ", ".join(columns) if columns else "*"
        where, params = self._build_where(query.filters)
        order = self._build_order_by(query.order_by, query.order_desc)
        sql = f"SELECT {select} FROM {qual}{where}{order} LIMIT ? OFFSET ?"
        conn = self._connect()
        rows = conn.execute(sql, params + [query.limit, query.offset]).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def query_one(
        self,
        table: str,
        query: StorageQuery,
        columns: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Query single row (soft-deleted excluded)."""
        results = self.query(table, query, columns)
        return results[0] if results else None

    def delete(self, table: str, query: StorageQuery) -> int:
        """Hard-delete rows matching query, return count."""
        qual = self._qualify_table(table)
        where, params = self._build_where(query.filters, not_deleted=False)
        with self.transaction():
            cur = self._connect().execute(f"DELETE FROM {qual}{where}", params)
            return cur.rowcount

    def execute(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute raw SELECT SQL, return rows as dicts."""
        conn = self._connect()
        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        """Execute raw write SQL, return affected row count."""
        with self.transaction():
            cur = self._connect().execute(sql, params)
            return cur.rowcount

    def insert_one(
        self, table: str, data: dict[str, Any], id_column: str = "id"
    ) -> str:
        """Insert single row, return id."""
        return self.insert(table, data)

    def query_by_id(
        self, table: str, row_id: str, columns: list[str] | None = None
    ) -> dict[str, Any] | None:
        """Query by primary key (soft-deleted excluded)."""
        q = StorageQuery(filters=[QueryFilter(column="id", operator="=", value=row_id)])
        return self.query_one(table, q, columns)

    def soft_delete(self, table: str, row_id: str, id_column: str = "id") -> int:
        """Soft-delete row (sets deleted_at timestamp), return count deleted."""
        qual = self._qualify_table(table)
        now = datetime.now(timezone.utc).isoformat()
        with self.transaction():
            cur = self._connect().execute(
                f"UPDATE {qual} SET deleted_at = ?, updated_at = ? "
                f"WHERE {id_column} = ? AND deleted_at IS NULL",
                (now, now, row_id),
            )
            return cur.rowcount

    def exists(self, table: str, query: StorageQuery) -> bool:
        """Check if a non-deleted row matches query."""
        return self.query_one(table, query) is not None

    def count(self, table: str, query: StorageQuery) -> int:
        """Count non-deleted rows matching query."""
        qual = self._qualify_table(table)
        where, params = self._build_where(query.filters)
        conn = self._connect()
        row = conn.execute(f"SELECT COUNT(*) FROM {qual}{where}", params).fetchone()
        return row[0] if row else 0

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _build_where(
        self, filters: list[QueryFilter], not_deleted: bool = True
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for f in filters:
            if f.operator == "MATCH":
                clauses.append(f"{_col_expr(f.column)} MATCH ?")
            else:
                clauses.append(f"{_col_expr(f.column)} {f.operator} ?")
            params.append(f.value)
        if not_deleted:
            clauses.append("deleted_at IS NULL")
        if not clauses:
            return "", []
        return " WHERE " + " AND ".join(clauses), params

    @staticmethod
    def _build_order_by(order_by: str, desc: bool) -> str:
        direction = "DESC" if desc else "ASC"
        return f" ORDER BY {_col_expr(order_by)} {direction}"

    def _init_fts(self, conn: sqlite3.Connection) -> None:
        """Initialize a contentless FTS5 index kept in sync via triggers."""
        table = self._qualify_table("fts_index")
        entries = self._qualify_table("entries")
        cols = ", ".join(self.config.fts_columns)
        col_list = ", ".join(["rowid", *self.config.fts_columns])
        new_extracts = ", ".join(
            [f"json_extract(NEW.{_JSON_COLUMN}, '$.{c}')" for c in self.config.fts_columns]
        )
        old_extracts = ", ".join(
            [f"json_extract(OLD.{_JSON_COLUMN}, '$.{c}')" for c in self.config.fts_columns]
        )
        changed = " OR ".join(
            [f"json_extract(NEW.{_JSON_COLUMN}, '$.{c}') IS NOT "
             f"json_extract(OLD.{_JSON_COLUMN}, '$.{c}')" for c in self.config.fts_columns]
        )

        conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {table} USING fts5({cols}, content='')")

        conn.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_{self.namespace}_fts_insert
            AFTER INSERT ON {entries}
            BEGIN
                INSERT INTO {table}({col_list}) VALUES (NEW.rowid, {new_extracts});
            END
            """
        )
        conn.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_{self.namespace}_fts_delete
            AFTER DELETE ON {entries}
            BEGIN
                INSERT INTO {table}({table}, {col_list})
                VALUES ('delete', OLD.rowid, {old_extracts});
            END
            """
        )
        conn.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_{self.namespace}_fts_update
            AFTER UPDATE ON {entries}
            WHEN {changed}
            BEGIN
                INSERT INTO {table}({table}, {col_list})
                VALUES ('delete', OLD.rowid, {old_extracts});
                INSERT INTO {table}({col_list}) VALUES (NEW.rowid, {new_extracts});
            END
            """
        )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        """Convert a SQLite row to a dict, unpacking the JSON document."""
        result: dict[str, Any] = {}
        for key in row.keys():
            value = row[key]
            if isinstance(value, (bytes, bytearray)):
                continue
            if key == _JSON_COLUMN and isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, dict):
                        result.update(parsed)
                        continue
                except json.JSONDecodeError:
                    pass
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[key] = value
        return result
