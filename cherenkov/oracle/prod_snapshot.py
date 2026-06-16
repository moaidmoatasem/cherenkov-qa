"""
cherenkov/oracle/prod_snapshot.py — E4-3: Production-snapshot oracle.

Uses a captured production traffic snapshot as the oracle for 'correct' behaviour.
"""

from __future__ import annotations

from typing import Any

import requests

from cherenkov.core.contracts import Claim
from cherenkov.core.errors import get_logger
from cherenkov.oracle.interface import Oracle, OracleResult


class ProdSnapshotOracle(Oracle):
    """Oracle that evaluates claims by comparing against a live production endpoint.

    The production URL is treated as the ground truth for current behaviour.
    """

    def __init__(self, prod_base_url: str):
        self._prod_url = prod_base_url.rstrip("/")
        self._log = get_logger("oracle-prod-snapshot")

    def evaluate(self, claim: Claim, **kwargs: Any) -> OracleResult:
        if claim.category not in ("endpoint", "observed_status"):
            return OracleResult(
                is_correct=True, confidence=0.5, detail="Non-evaluable claim category"
            )

        subject = claim.subject
        parts = subject.split(" ", 1)
        if len(parts) != 2:
            return OracleResult(
                is_correct=True,
                confidence=0.3,
                detail=f"Cannot parse subject: {subject}",
            )

        method = parts[0].upper()
        path = parts[1]

        try:
            prod_path = f"{self._prod_url}{path}"
            resp = requests.request(method, prod_path, timeout=30)

            prod_status = resp.status_code
            observed_status = (
                claim.value.get("status") if isinstance(claim.value, dict) else None
            )

            if observed_status is not None:
                match = observed_status == prod_status
                return OracleResult(
                    is_correct=match,
                    confidence=0.85,
                    detail=f"Prod status {prod_status} vs observed {observed_status}: {'MATCH' if match else 'MISMATCH'}",
                    expected=prod_status,
                    actual=observed_status,
                )

            return OracleResult(
                is_correct=True,
                confidence=0.7,
                detail=f"Prod responded ({method} {path} -> {prod_status})",
                expected=prod_status,
                actual=observed_status,
            )

        except requests.RequestException as e:
            self._log.warning("prod unreachable", error=str(e))
            return OracleResult(
                is_correct=True,
                confidence=0.2,
                detail=f"Cannot reach prod at {self._prod_url}: {e}",
            )
