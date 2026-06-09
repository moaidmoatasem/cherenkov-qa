"""
cherenkov/oracle/spec_prism.py — E4-3: Spec+Prism oracle.
Authority: v3.1 + delta.

Uses the OpenAPI spec (via Prism mock server) as the oracle for 'correct' behaviour.
"""

from __future__ import annotations

from typing import Any

import requests

from cherenkov.core.config import Config
from cherenkov.core.contracts import Claim
from cherenkov.core.errors import get_logger
from cherenkov.oracle.interface import Oracle, OracleResult


class SpecPrismOracle(Oracle):
    """Oracle that evaluates claims by replaying them against a Prism mock server.

    Prism is started with `prism mock <spec.yaml>` and provides spec-compliant
    responses.
    """

    def __init__(self, prism_url: str = "http://localhost:4010"):
        self._prism_url = prism_url.rstrip("/")
        self._log = get_logger("oracle-spec-prism")

    def evaluate(self, claim: Claim, **kwargs: Any) -> OracleResult:
        if claim.category not in ("endpoint", "observed_status", "observed_latency"):
            return OracleResult(is_correct=False, confidence=0.0, detail="Non-evaluable claim category")

        subject = claim.subject
        parts = subject.split(" ", 1)
        if len(parts) != 2:
            return OracleResult(is_correct=False, confidence=0.0, detail=f"Cannot parse subject: {subject}")

        method = parts[0].upper()
        path = parts[1]

        try:
            prism_path = f"{self._prism_url}{path}"
            resp = requests.request(method, prism_path, timeout=15)

            expected_status = resp.status_code
            observed_status = claim.value.get("status") if isinstance(claim.value, dict) else None

            if observed_status is not None and observed_status != expected_status:
                return OracleResult(
                    is_correct=False,
                    confidence=0.9,
                    detail=f"Status mismatch: got {observed_status}, Prism expects {expected_status}",
                    expected=expected_status,
                    actual=observed_status,
                )

            return OracleResult(
                is_correct=True,
                confidence=0.8,
                detail=f"Prism response matched ({method} {path} -> {expected_status})",
                expected=expected_status,
                actual=observed_status,
            )

        except requests.RequestException as e:
            self._log.warning("prism unreachable", error=str(e))
            return OracleResult(
                is_correct=False,
                confidence=0.0,
                detail=f"Cannot reach Prism at {self._prism_url}: {e}",
            )
