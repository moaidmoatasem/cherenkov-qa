"""
CHERENKOV governance/gen_metrics.py — LlamaRestTest-aligned generation quality metrics.

Tracks and persists per-run quality metrics aligned with the LlamaRestTest
evaluation methodology (FSE 2025, arXiv 2501.08598):

  gate_pass_rate      — fraction of generated tests that clear all 6 review
                        gates (the "assured generation" filter from TestGen-LLM).
  operation_coverage  — fraction of spec operations that have at least one
                        passing, gate-cleared test.
  faults_500          — server errors (5xx) detected during Prism/live runs,
                        the primary fault-detection signal in LlamaRestTest.

Threshold: the research's Stage 1 ship criterion is gate_pass_rate >= 75%.
When a run falls below this threshold the store emits a structured warning so
the operator knows the prompt/model/spec-context pipeline needs rework.

Storage: SQLite at .cherenkov/gen_metrics.db (created on first use).
Thread-safety: per-call connection — no long-lived handle.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cherenkov.core.errors import get_logger

# Research recommendation: warn when below 75% (Stage 1 ship criterion).
GATE_PASS_THRESHOLD = 0.75

_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS gen_metrics (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id             TEXT    NOT NULL,
    ts                 INTEGER NOT NULL,
    total_generated    INTEGER DEFAULT 0,
    gate_passed        INTEGER DEFAULT 0,
    gate_pass_rate     REAL    DEFAULT 0.0,
    operations_total   INTEGER DEFAULT 0,
    operations_covered INTEGER DEFAULT 0,
    operation_coverage REAL    DEFAULT 0.0,
    faults_500         INTEGER DEFAULT 0,
    below_threshold    INTEGER DEFAULT 0
);
"""


@dataclass
class RunGenMetrics:
    """Mutable accumulator for one pipeline run's generation quality metrics."""

    run_id: str
    total_generated: int = 0
    gate_passed: int = 0
    operations_total: int = 0
    operations_covered: int = 0
    faults_500: int = 0

    # ── derived properties ────────────────────────────────────────────────

    @property
    def gate_pass_rate(self) -> float:
        return self.gate_passed / self.total_generated if self.total_generated else 0.0

    @property
    def operation_coverage(self) -> float:
        return (
            self.operations_covered / self.operations_total
            if self.operations_total
            else 0.0
        )

    @property
    def below_threshold(self) -> bool:
        """True only after >= 3 generations so early runs don't false-alarm."""
        return self.total_generated >= 3 and self.gate_pass_rate < GATE_PASS_THRESHOLD

    # ── mutation helpers ──────────────────────────────────────────────────

    def record_generation(
        self, all_gates_passed: bool, had_500_fault: bool = False
    ) -> None:
        """Call once per generated test after ReviewStage completes."""
        self.total_generated += 1
        if all_gates_passed:
            self.gate_passed += 1
        if had_500_fault:
            self.faults_500 += 1

    def record_operation(self, covered: bool) -> None:
        """Call once per spec operation; covered=True when a passing test exists."""
        self.operations_total += 1
        if covered:
            self.operations_covered += 1

    # ── rendering ────────────────────────────────────────────────────────

    def render(self) -> str:
        threshold_flag = (
            " [BELOW THRESHOLD — check prompt/model/spec-context pipeline]"
            if self.below_threshold
            else ""
        )
        return (
            f"Generation Metrics  run={self.run_id}\n"
            f"  Gate Pass Rate:       {self.gate_pass_rate:.1%} "
            f"({self.gate_passed}/{self.total_generated}){threshold_flag}\n"
            f"  Operation Coverage:   {self.operation_coverage:.1%} "
            f"({self.operations_covered}/{self.operations_total})\n"
            f"  500-Fault Detections: {self.faults_500}"
        )


class GenMetricsStore:
    """
    Persists RunGenMetrics to a local SQLite database.

    Usage:
        store = GenMetricsStore()
        m = RunGenMetrics(run_id="abc123")
        m.record_generation(all_gates_passed=True)
        m.record_operation(covered=True)
        store.save(m)
        print(store.trend_summary())
    """

    def __init__(self, db_path: str | None = None) -> None:
        default = Path(".cherenkov") / "gen_metrics.db"
        self.db_path = str(Path(db_path) if db_path else default)
        self.log = get_logger("GEN_METRICS")
        self._ensure_schema()

    # ── public API ────────────────────────────────────────────────────────

    def save(self, metrics: RunGenMetrics) -> None:
        """Persist metrics for a completed run. Logs a warning if below threshold."""
        if metrics.below_threshold:
            self.log.warning(
                "gate pass rate below threshold",
                run_id=metrics.run_id,
                gate_pass_rate=f"{metrics.gate_pass_rate:.1%}",
                threshold=f"{GATE_PASS_THRESHOLD:.0%}",
                hint=(
                    "Inspect prompt (prompts/generator_system.txt), "
                    "model (get_settings().GEN_MODEL), and spec-context enrichment."
                ),
            )

        from contextlib import closing
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn:
                conn.execute(
                """
                INSERT INTO gen_metrics (
                    run_id, ts,
                    total_generated, gate_passed, gate_pass_rate,
                    operations_total, operations_covered, operation_coverage,
                    faults_500, below_threshold
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    metrics.run_id,
                    int(time.time()),
                    metrics.total_generated,
                    metrics.gate_passed,
                    metrics.gate_pass_rate,
                    metrics.operations_total,
                    metrics.operations_covered,
                    metrics.operation_coverage,
                    metrics.faults_500,
                    int(metrics.below_threshold),
                ),
            )

    def history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the N most recent run rows, newest first."""
        from contextlib import closing
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM gen_metrics ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def trend_summary(self) -> str:
        """Human-readable trend across the last 5 runs."""
        rows = self.history(limit=5)
        if not rows:
            return "No generation metrics recorded yet."
        lines = ["Recent generation metrics (newest first):"]
        for r in rows:
            flag = " [BELOW THRESHOLD]" if r["below_threshold"] else ""
            lines.append(
                f"  run={r['run_id']}  "
                f"pass={r['gate_pass_rate']:.0%}  "
                f"cov={r['operation_coverage']:.0%}  "
                f"faults500={r['faults_500']}{flag}"
            )
        return "\n".join(lines)

    # ── private ───────────────────────────────────────────────────────────

    def _ensure_schema(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        from contextlib import closing
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn:
                conn.execute(_DB_SCHEMA)
