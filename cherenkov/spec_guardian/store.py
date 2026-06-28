"""SQLite storage for spec drift events and reports."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cherenkov.spec_guardian.core import (
    DriftEvent,
    DriftReport,
    DriftSeverity,
    DriftType,
)


DRIFT_DB = Path(".cherenkov/drift.db")


class DriftStore:
    """Thread-safe SQLite store for drift events."""

    _lock = threading.Lock()

    def __init__(self, db_path: Path = DRIFT_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                con.execute("PRAGMA journal_mode=WAL")
                with con:
                    con.execute("""
                        CREATE TABLE IF NOT EXISTS drift_events (
                            id          INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp   TEXT NOT NULL,
                            drift_type  TEXT NOT NULL,
                            severity    TEXT NOT NULL,
                            endpoint    TEXT NOT NULL,
                            method      TEXT NOT NULL,
                            field_path  TEXT,
                            expected    TEXT NOT NULL,
                            actual      TEXT NOT NULL,
                            message     TEXT NOT NULL
                        )
                    """)
                    con.execute("""
                        CREATE TABLE IF NOT EXISTS drift_reports (
                            id              INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp       TEXT NOT NULL,
                            spec_path       TEXT NOT NULL,
                            start_time      TEXT NOT NULL,
                            end_time        TEXT NOT NULL,
                            total_checks    INTEGER NOT NULL,
                            compliant_checks INTEGER NOT NULL,
                            drift_rate      REAL NOT NULL,
                            critical_count  INTEGER NOT NULL,
                            warning_count   INTEGER NOT NULL,
                            events_json     TEXT NOT NULL
                        )
                    """)
            finally:
                con.close()

    def save_event(self, event: DriftEvent) -> int:
        """Save a single drift event. Returns event ID."""
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                con.execute("PRAGMA journal_mode=WAL")
                cur = con.execute(
                    """INSERT INTO drift_events 
                       (timestamp, drift_type, severity, endpoint, method, field_path, expected, actual, message)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.timestamp.isoformat(),
                        event.drift_type.value,
                        event.severity.value,
                        event.endpoint,
                        event.method,
                        event.field_path,
                        json.dumps(event.expected),
                        json.dumps(event.actual),
                        event.message,
                    ),
                )
                con.commit()
                return cur.lastrowid or 0
            finally:
                con.close()

    def save_report(self, report: DriftReport) -> int:
        """Save a drift report. Returns report ID."""
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                con.execute("PRAGMA journal_mode=WAL")
                cur = con.execute(
                    """INSERT INTO drift_reports
                       (timestamp, spec_path, start_time, end_time, total_checks, 
                        compliant_checks, drift_rate, critical_count, warning_count, events_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        datetime.now(timezone.utc).isoformat(),
                        report.spec_path,
                        report.start_time.isoformat(),
                        report.end_time.isoformat(),
                        report.total_checks,
                        report.compliant_checks,
                        report.drift_rate,
                        report.critical_count,
                        report.warning_count,
                        json.dumps(report.to_dict()),
                    ),
                )
                con.commit()
                return cur.lastrowid or 0
            finally:
                con.close()

    def latest_report(self) -> DriftReport | None:
        """Get the most recent drift report."""
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                con.execute("PRAGMA journal_mode=WAL")
                row = con.execute(
                    """SELECT spec_path, start_time, end_time, total_checks, 
                              compliant_checks, events_json
                       FROM drift_reports ORDER BY id DESC LIMIT 1"""
                ).fetchone()
                if row:
                    return DriftReport.from_dict(json.loads(row[5]))
                return None
            finally:
                con.close()

    def recent_events(self, limit: int = 100) -> list[DriftEvent]:
        """Get recent drift events."""
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                con.execute("PRAGMA journal_mode=WAL")
                rows = con.execute(
                    """SELECT timestamp, drift_type, severity, endpoint, method,
                              field_path, expected, actual, message
                       FROM drift_events ORDER BY id DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
                return [
                    DriftEvent(
                        timestamp=datetime.fromisoformat(r[0]),
                        drift_type=DriftType(r[1]),
                        severity=DriftSeverity(r[2]),
                        endpoint=r[3],
                        method=r[4],
                        field_path=r[5],
                        expected=json.loads(r[6]),
                        actual=json.loads(r[7]),
                        message=r[8],
                    )
                    for r in rows
                ]
            finally:
                con.close()

    def drift_trend(self, hours: int = 24) -> dict[str, Any]:
        """Get drift trend statistics for the last N hours."""
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                con.execute("PRAGMA journal_mode=WAL")
                cutoff = (datetime.now(timezone.utc) - __import__('datetime').timedelta(hours=hours)).isoformat()

                total = con.execute(
                    "SELECT COUNT(*) FROM drift_events WHERE timestamp >= ?",
                    (cutoff,),
                ).fetchone()[0]

                critical = con.execute(
                    "SELECT COUNT(*) FROM drift_events WHERE timestamp >= ? AND severity = 'critical'",
                    (cutoff,),
                ).fetchone()[0]

                warning = con.execute(
                    "SELECT COUNT(*) FROM drift_events WHERE timestamp >= ? AND severity = 'warning'",
                    (cutoff,),
                ).fetchone()[0]

                by_type = {}
                for row in con.execute(
                    "SELECT drift_type, COUNT(*) FROM drift_events WHERE timestamp >= ? GROUP BY drift_type",
                    (cutoff,),
                ).fetchall():
                    by_type[row[0]] = row[1]

                return {
                    "hours": hours,
                    "total_events": total,
                    "critical_events": critical,
                    "warning_events": warning,
                    "by_type": by_type,
                }
            finally:
                con.close()
