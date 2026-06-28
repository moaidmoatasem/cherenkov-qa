from __future__ import annotations

import os
import sqlite3
import time
import hashlib
from typing import Any

from cherenkov.core.errors import get_logger

_BUSY_TIMEOUT_S = 30.0


def _default_db_path() -> str:
    data_dir = os.environ.get(
        "CHERENKOV_DATA_DIR",
        os.path.join(os.path.expanduser("~"), ".cherenkov"),
    )
    return os.path.join(data_dir, "healing_feedback.db")


class HealingFeedbackStore:
    """Append-only feedback log with CQRS read-model thresholds.

    Write model: healing_feedback_log (append-only rows).
    Read model: recomputed healing_thresholds per endpoint+mutation_id.
    Laplace-smoothed confidence: (votes_for_dominant + 1) / (total + 3).

    Suggestion surfaces only at confidence >= 0.70 AND count >= 3.
    """

    def __init__(self, db_path: str | None = None, run_id: str | None = None) -> None:
        self.db_path = db_path or _default_db_path()
        self.log = get_logger("HEALING_FEEDBACK", run_id)
        if self.db_path != ":memory:":
            dirname = os.path.dirname(self.db_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        """Return a new connection (not cached, to avoid file-lock issues on Windows)."""
        con = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        con.row_factory = sqlite3.Row
        return con

    def _init_tables(self) -> None:
        try:
            con = self._connect()
            try:
                con.execute(
                    "CREATE TABLE IF NOT EXISTS healing_feedback_log ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "item_id TEXT NOT NULL, "
                    "endpoint TEXT NOT NULL, "
                    "mutation_id TEXT NOT NULL, "
                    "classification TEXT NOT NULL CHECK(classification IN ('regression','intended','ignore')), "
                    "actor TEXT NOT NULL DEFAULT 'unknown', "
                    "detail TEXT DEFAULT '', "
                    "timestamp INTEGER NOT NULL)"
                )
                con.execute(
                    "CREATE INDEX IF NOT EXISTS idx_feedback_endpoint_mutation "
                    "ON healing_feedback_log(endpoint, mutation_id)"
                )
                con.commit()
            finally:
                con.close()
        except sqlite3.OperationalError as exc:
            self.log.warning(
                "db init failed (non-fatal on some filesystems)", error=str(exc)
            )

    def record_feedback(
        self,
        item_id: str,
        endpoint: str,
        mutation_id: str,
        classification: str,
        actor: str = "unknown",
        detail: str = "",
    ) -> None:
        assert classification in (
            "regression",
            "intended",
            "ignore",
        ), f"Invalid classification: {classification}"
        con = self._connect()
        try:
            con.execute(
                "INSERT INTO healing_feedback_log "
                "(item_id, endpoint, mutation_id, classification, actor, detail, timestamp) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    item_id,
                    endpoint,
                    mutation_id,
                    classification,
                    actor,
                    detail,
                    int(time.time()),
                ),
            )
            con.commit()
        finally:
            con.close()
        self.log.info(
            "recorded healing feedback",
            item_id=item_id,
            classification=classification,
            endpoint=endpoint,
        )

    def compute_thresholds(self, endpoint: str, mutation_id: str) -> dict[str, Any]:
        """Compute Laplace-smoothed thresholds for an endpoint+mutation pair.

        Returns:
            count, dominant_classification, confidence, votes per classification.
        """
        def h(v):
            return hashlib.sha256(v.encode()).hexdigest()[:12] if v else ""
        hashed_ep = h(endpoint)
        hashed_mut = h(mutation_id)

        con = self._connect()
        try:
            rows = con.execute(
                "SELECT classification, COUNT(*) as cnt FROM healing_feedback_log "
                "WHERE (endpoint=? OR endpoint=?) AND (mutation_id=? OR mutation_id=?) "
                "GROUP BY classification",
                (endpoint, hashed_ep, mutation_id, hashed_mut),
            ).fetchall()
        finally:
            con.close()

        total = sum(r["cnt"] for r in rows)
        if total == 0:
            return {
                "endpoint": endpoint,
                "mutation_id": mutation_id,
                "count": 0,
                "dominant_classification": None,
                "confidence": 0.0,
                "votes": {"regression": 0, "intended": 0, "ignore": 0},
            }

        votes = {"regression": 0, "intended": 0, "ignore": 0}
        for r in rows:
            votes[r["classification"]] = r["cnt"]

        dominant = max(votes, key=votes.get)
        dominant_votes = votes[dominant]
        # Laplace smoothing: (dominant + 1) / (total + 3)
        confidence = (dominant_votes + 1.0) / (total + 3.0)

        return {
            "endpoint": endpoint,
            "mutation_id": mutation_id,
            "count": total,
            "dominant_classification": dominant,
            "confidence": round(confidence, 4),
            "votes": votes,
        }
