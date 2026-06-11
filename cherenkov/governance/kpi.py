from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cherenkov.core.errors import get_logger


@dataclass
class GovernanceKPI:
    escape_rate: float = 0.0
    false_positive_rate: float = 0.0
    coverage: float = 0.0
    maintenance_score: float = 1.0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    escaped_defects: int = 0
    false_positives: int = 0
    idiom_count: int = 0
    total_endpoints: int = 0
    covered_endpoints: int = 0
    last_run_ts: int = 0
    coverage_data_available: bool = True

    @property
    def health_score(self) -> float:
        weights = {"escape": 0.3, "fp": 0.2, "coverage": 0.3, "maintenance": 0.2}
        score = (
            weights["escape"] * (1.0 - self.escape_rate) +
            weights["fp"] * (1.0 - self.false_positive_rate) +
            weights["coverage"] * self.coverage +
            weights["maintenance"] * self.maintenance_score
        )
        return round(score, 4)


@dataclass
class GovernanceReport:
    kpi: GovernanceKPI = field(default_factory=GovernanceKPI)
    history: list[dict[str, Any]] = field(default_factory=list)

    def render(self) -> str:
        k = self.kpi
        lines = [
            "E12 Governance KPI Panel",
            "=" * 60,
            f"  Health Score:      {k.health_score:.2f}",
            f"  Escape Rate:       {k.escape_rate:.1%}  ({k.escaped_defects} escaped / {k.total_tests} tests)",
            f"  False Positive:    {k.false_positive_rate:.1%}  ({k.false_positives} FP / {k.total_tests} tests)",
            f"  Coverage:          {k.coverage:.1%}  ({k.covered_endpoints}/{k.total_endpoints} endpoints)",
            f"  Maintenance Score: {k.maintenance_score:.2f}",
            f"  Pass Rate:         {k.passed_tests}/{k.failed_tests + k.passed_tests} passed",
            f"  Active Idioms:     {k.idiom_count}",
        ]
        return "\n".join(lines)

    def render_json(self) -> dict[str, Any]:
        return {
            "health_score": self.kpi.health_score,
            "escape_rate": self.kpi.escape_rate,
            "false_positive_rate": self.kpi.false_positive_rate,
            "coverage": self.kpi.coverage,
            "maintenance_score": self.kpi.maintenance_score,
            "total_tests": self.kpi.total_tests,
            "passed_tests": self.kpi.passed_tests,
            "failed_tests": self.kpi.failed_tests,
            "escaped_defects": self.kpi.escaped_defects,
            "false_positives": self.kpi.false_positives,
            "idiom_count": self.kpi.idiom_count,
            "total_endpoints": self.kpi.total_endpoints,
            "covered_endpoints": self.kpi.covered_endpoints,
            "history_count": len(self.history),
        }


def _default_db_path() -> str:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    return os.path.join(repo_root, ".cherenkov", "governance.db")


class GovernanceCollector:
    """Collects KPIs from existing subsystems and persists history."""

    def __init__(self, db_path: str | None = None, run_id: str | None = None):
        self.db_path = db_path or _default_db_path()
        self.log = get_logger("GOVERNANCE", run_id)
        dirname = os.path.dirname(self.db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self._init_tables()

    def _init_tables(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS governance_kpi_history ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "timestamp INTEGER NOT NULL,"
            "health_score REAL NOT NULL,"
            "escape_rate REAL NOT NULL,"
            "false_positive_rate REAL NOT NULL,"
            "coverage REAL NOT NULL,"
            "maintenance_score REAL NOT NULL,"
            "total_tests INTEGER NOT NULL DEFAULT 0,"
            "passed_tests INTEGER NOT NULL DEFAULT 0,"
            "failed_tests INTEGER NOT NULL DEFAULT 0,"
            "escaped_defects INTEGER NOT NULL DEFAULT 0,"
            "false_positives INTEGER NOT NULL DEFAULT 0,"
            "idiom_count INTEGER NOT NULL DEFAULT 0,"
            "total_endpoints INTEGER NOT NULL DEFAULT 0,"
            "covered_endpoints INTEGER NOT NULL DEFAULT 0)"
        )
        conn.commit()
        conn.close()

    def collect(self) -> GovernanceReport:
        kpi = GovernanceKPI()
        kpi.last_run_ts = int(time.time())

        verdict_db = os.path.join(os.path.dirname(self.db_path), "verdicts.db")
        if os.path.exists(verdict_db):
            try:
                conn = sqlite3.connect(verdict_db, timeout=5.0)
                total = conn.execute("SELECT COUNT(*) FROM verdicts").fetchone()[0]
                escaped = conn.execute(
                    "SELECT COUNT(*) FROM verdicts WHERE outcome='escaped_defect'"
                ).fetchone()[0]
                accepted = conn.execute(
                    "SELECT COUNT(*) FROM verdicts WHERE outcome='accept'"
                ).fetchone()[0]
                rejected = conn.execute(
                    "SELECT COUNT(*) FROM verdicts WHERE outcome='reject'"
                ).fetchone()[0]
                idiom_count = conn.execute("SELECT COUNT(*) FROM idioms").fetchone()[0]
                conn.close()

                kpi.total_tests = total
                kpi.passed_tests = accepted
                kpi.failed_tests = rejected
                kpi.escaped_defects = escaped
                # false_positives here = verdicts rejected by human reviewers
                # This is a proxy for FP rate, not a statistically rigorous measure
                kpi.false_positives = rejected
                kpi.idiom_count = idiom_count

                if total > 0:
                    kpi.escape_rate = escaped / total
                if (accepted + rejected) > 0:
                    kpi.false_positive_rate = rejected / (accepted + rejected)
            except Exception as e:
                self.log.warning("could not read verdict db", error=str(e))

        coverage_db = os.path.join(os.path.dirname(self.db_path), "coverage.db")
        if os.path.exists(coverage_db):
            try:
                conn = sqlite3.connect(coverage_db, timeout=5.0)
                total_ep = conn.execute("SELECT COUNT(*) FROM coverage_items").fetchone()[0]
                covered_ep = conn.execute(
                    "SELECT COUNT(*) FROM coverage_items WHERE state='covered'"
                ).fetchone()[0]
                conn.close()
                if total_ep > 0:
                    kpi.coverage = covered_ep / total_ep
                    kpi.total_endpoints = total_ep
                    kpi.covered_endpoints = covered_ep
            except Exception as e:
                self.log.warning("could not read coverage db", error=str(e))

        if kpi.total_endpoints == 0:
            # No endpoint data available — coverage is unknown, not 100%
            kpi.coverage = 0.0
            # Add a flag so dashboards can show "no data" instead of 0%
            kpi.coverage_data_available = False

        kpi.maintenance_score = max(0.0, min(1.0, 1.0 - kpi.false_positive_rate * 0.5 - kpi.escape_rate * 0.3))

        report = GovernanceReport(kpi=kpi, history=self._get_history())
        self._persist(kpi)
        return report

    def _persist(self, kpi: GovernanceKPI) -> None:
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.execute(
                "INSERT INTO governance_kpi_history "
                "(timestamp, health_score, escape_rate, false_positive_rate, coverage, "
                " maintenance_score, total_tests, passed_tests, failed_tests, "
                " escaped_defects, false_positives, idiom_count, "
                " total_endpoints, covered_endpoints) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (kpi.last_run_ts, kpi.health_score, kpi.escape_rate, kpi.false_positive_rate,
                 kpi.coverage, kpi.maintenance_score, kpi.total_tests, kpi.passed_tests,
                 kpi.failed_tests, kpi.escaped_defects, kpi.false_positives, kpi.idiom_count,
                 kpi.total_endpoints, kpi.covered_endpoints),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.log.warning("could not persist governance KPI", error=str(e))

    def _get_history(self, limit: int = 30) -> list[dict[str, Any]]:
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            rows = conn.execute(
                "SELECT * FROM governance_kpi_history ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            conn.close()
            return [
                {
                    "id": r[0],
                    "timestamp": r[1],
                    "health_score": r[2],
                    "escape_rate": r[3],
                    "false_positive_rate": r[4],
                    "coverage": r[5],
                    "maintenance_score": r[6],
                    "total_tests": r[7],
                    "passed_tests": r[8],
                    "failed_tests": r[9],
                    "escaped_defects": r[10],
                    "false_positives": r[11],
                    "idiom_count": r[12],
                    "total_endpoints": r[13],
                    "covered_endpoints": r[14],
                }
                for r in rows
            ]
        except Exception:
            return []

    def get_trend(self, metric: str = "health_score", limit: int = 10) -> list[float]:
        history = self._get_history(limit=limit)
        return [h.get(metric, 0.0) for h in reversed(history)]
