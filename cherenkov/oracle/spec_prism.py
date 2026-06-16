"""
cherenkov/oracle/spec_prism.py — E4-3: Spec+Prism oracle.

Uses the OpenAPI spec (via Prism mock server) as the oracle for 'correct' behaviour.
"""

from __future__ import annotations

from typing import Any

import requests

from cherenkov.core.settings import get_settings
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

    def _validate_response_body(
        self, response_body: dict | None, spec_schema: dict | None
    ) -> tuple[bool, float, str]:
        """Validate response body against OpenAPI response schema. Returns (is_correct, confidence, detail)."""
        if spec_schema is None:
            return True, 0.5, "No response schema in spec — cannot validate body"
        if response_body is None:
            return False, 0.9, "Response body is empty but spec defines a schema"

        try:
            import jsonschema

            jsonschema.validate(instance=response_body, schema=spec_schema)
            return True, 1.0, "Response body matches spec schema"
        except ImportError:
            return True, 0.4, "jsonschema not installed — body validation skipped"
        except jsonschema.ValidationError as e:
            return False, 0.95, f"Body schema violation: {e.message}"
        except Exception as e:
            return True, 0.3, f"Body validation error: {e}"

    def _validate_response_headers(
        self, actual_headers: dict, expected_content_type: str | None, status_code: int
    ) -> tuple[bool, float, str]:
        """Validate response headers against spec expectations."""
        issues = []

        if expected_content_type:
            actual_ct = actual_headers.get("content-type", "").split(";")[0].strip()
            expected_ct = expected_content_type.split(";")[0].strip()
            if actual_ct != expected_ct:
                issues.append(
                    f"Content-Type: expected {expected_ct!r}, got {actual_ct!r}"
                )

        # 201 Created should have Location header
        if status_code == 201 and "location" not in {k.lower() for k in actual_headers}:
            issues.append("201 response missing Location header")

        if issues:
            return False, 0.85, "; ".join(issues)
        return True, 1.0, "Headers valid"

    def _evaluate_latency(
        self, observed_ms: float, endpoint: str, method: str
    ) -> OracleResult:
        """Evaluate observed latency against configured SLA threshold."""
        max_ms = getattr(get_settings(), "MAX_LATENCY_MS", 2000)
        if observed_ms > max_ms:
            return OracleResult(
                is_correct=False,
                confidence=0.95,
                detail=f"Latency {observed_ms:.0f}ms exceeds SLA {max_ms}ms for {method} {endpoint}",
            )
        return OracleResult(
            is_correct=True,
            confidence=1.0,
            detail=f"Latency {observed_ms:.0f}ms within SLA {max_ms}ms",
        )

    def evaluate(self, claim: Claim, **kwargs: Any) -> OracleResult:
        if claim.category not in ("endpoint", "observed_status", "observed_latency"):
            return OracleResult(
                is_correct=False, confidence=0.0, detail="Non-evaluable claim category"
            )

        subject = claim.subject
        parts = subject.split(" ", 1)
        if len(parts) != 2:
            return OracleResult(
                is_correct=False,
                confidence=0.0,
                detail=f"Cannot parse subject: {subject}",
            )

        method = parts[0].upper()
        path = parts[1]

        # Handle latency claims directly without calling Prism
        if claim.category == "observed_latency":
            observed_ms = (
                claim.value.get("latency_ms") if isinstance(claim.value, dict) else None
            )
            if observed_ms is None:
                return OracleResult(
                    is_correct=False,
                    confidence=0.0,
                    detail="observed_latency claim missing latency_ms value",
                )
            return self._evaluate_latency(float(observed_ms), path, method)

        try:
            prism_path = f"{self._prism_url}{path}"
            resp = requests.request(method, prism_path, timeout=15)

            expected_status = resp.status_code
            observed_status = (
                claim.value.get("status") if isinstance(claim.value, dict) else None
            )

            if observed_status is not None and observed_status != expected_status:
                return OracleResult(
                    is_correct=False,
                    confidence=0.9,
                    detail=f"Status mismatch: got {observed_status}, Prism expects {expected_status}",
                    expected=expected_status,
                    actual=observed_status,
                )

            # Status check passed — optionally validate body
            min_confidence = 0.8
            details = [f"Prism response matched ({method} {path} -> {expected_status})"]

            response_body = kwargs.get("response_body")
            spec_schema = kwargs.get("spec_schema")
            if response_body is not None or spec_schema is not None:
                body_ok, body_conf, body_detail = self._validate_response_body(
                    response_body, spec_schema
                )
                details.append(body_detail)
                min_confidence = min(min_confidence, body_conf)
                if not body_ok:
                    return OracleResult(
                        is_correct=False,
                        confidence=min_confidence,
                        detail="; ".join(details),
                        expected=expected_status,
                        actual=observed_status,
                    )

            return OracleResult(
                is_correct=True,
                confidence=min_confidence,
                detail="; ".join(details),
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
