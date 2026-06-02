"""
CHERENKOV divergence/witness.py — E3-2 Witness Agent.

Deterministic reproduction harness: fires a real HTTP request and diffs
the real response against the hypothesis claim. Re-execution is independent
of the Skeptic — the Witness only needs a DivergenceHypothesis and a base URL.
"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

from cherenkov.core.contracts import (
    DivergenceEvidence,
    DivergenceHypothesis,
    ReproductionResult,
)


class WitnessAgent:
    """
    Deterministically reproduces or rejects a DivergenceHypothesis.

    Each call to reproduce() is stateless — safe to parallelise.
    Does NOT use the Substrate Router; the Witness is near-zero intelligence
    (see architecture doc): just HTTP + diff, no LLM required.
    """

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def reproduce(self, hypothesis: DivergenceHypothesis) -> ReproductionResult:
        """
        Attempt to reproduce the divergence described in *hypothesis*.

        Returns ReproductionResult with reproduced=True when evidence of the
        divergence is captured, or reproduced=False with a rejection_reason.
        """
        if not hypothesis.repro_steps:
            return ReproductionResult(
                hypothesis_id=hypothesis.id,
                reproduced=False,
                rejection_reason="No repro_steps provided — cannot execute",
            )

        try:
            evidence = self._execute(hypothesis)
        except Exception as exc:
            return ReproductionResult(
                hypothesis_id=hypothesis.id,
                reproduced=False,
                rejection_reason=f"Execution error: {exc}",
            )

        reproduced = self._is_divergence(evidence)
        return ReproductionResult(
            hypothesis_id=hypothesis.id,
            reproduced=reproduced,
            evidence=evidence if reproduced else None,
            rejection_reason=(
                None
                if reproduced
                else "Response matches expected claim — no divergence observed"
            ),
        )

    def reproduce_batch(
        self, hypotheses: list[DivergenceHypothesis]
    ) -> list[ReproductionResult]:
        """Reproduce each hypothesis sequentially, collecting all results."""
        return [self.reproduce(h) for h in hypotheses]

    # ── private ───────────────────────────────────────────────────────────

    def _execute(self, hypothesis: DivergenceHypothesis) -> DivergenceEvidence:
        method, path, payload, expected = _parse_repro_steps(hypothesis.repro_steps)
        url = f"{self.base_url}{path}"

        t0 = time.time()
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            if method in ("POST", "PUT", "PATCH") and payload is not None:
                resp = getattr(client, method.lower())(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
            else:
                resp = getattr(client, method.lower())(url)
        latency_ms = int((time.time() - t0) * 1000)

        try:
            actual: str | dict = resp.json()
        except Exception:
            actual = resp.text

        # `expected` from repro_steps may be an int (expected status code).
        # DivergenceEvidence.response_expected is str|dict, so we use claim_b
        # as the narrative expectation and pass the raw expected to _diff.
        diff = _diff(actual, expected if expected is not None else hypothesis.claim_b, resp.status_code)
        response_expected: str | dict = (
            f"HTTP {expected} per spec" if isinstance(expected, int) else
            (expected if expected is not None else hypothesis.claim_b)
        )

        return DivergenceEvidence(
            request_summary=f"{method} {url} → {resp.status_code} ({latency_ms}ms)",
            response_actual=actual,
            response_expected=response_expected,
            diff=diff,
        )

    @staticmethod
    def _is_divergence(evidence: DivergenceEvidence) -> bool:
        """A non-empty, non-trivial diff means divergence is confirmed."""
        diff = evidence.diff.strip()
        return bool(diff) and diff != "no structural diff"


# ── helpers ───────────────────────────────────────────────────────────────

def _parse_repro_steps(
    steps: list[str],
) -> tuple[str, str, dict | None, Any]:
    """
    Extract (method, path, payload, expected) from natural-language repro steps.

    Supports lines like:
      "Send GET /pet/findByStatus?status=available"
      "POST /pet with body {\"name\": \"doggie\", \"photoUrls\": []}"
      "Expect 200 response"  or  "Assert status 404"
    """
    method = "GET"
    path = "/"
    payload: dict | None = None
    expected: Any = None

    for step in steps:
        upper = step.upper()
        # Extract HTTP method + path
        for m in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"):
            if m in upper:
                method = m
                # find the first token starting with "/"
                for token in step.split():
                    if token.startswith("/"):
                        path = token
                        break
                break

        # Extract JSON body
        brace = step.find("{")
        if brace != -1 and payload is None:
            try:
                payload = json.loads(step[brace:])
            except json.JSONDecodeError:
                pass

        # Extract expected status code
        step_lower = step.lower()
        if ("expect" in step_lower or "assert" in step_lower or "should" in step_lower):
            for code in (200, 201, 204, 400, 401, 403, 404, 409, 422, 500):
                if str(code) in step:
                    expected = code
                    break

    return method, path, payload, expected


def _diff(actual: Any, expected: Any, status_code: int) -> str:
    """Return a human-readable description of the delta between actual and expected."""
    if expected is None:
        body = json.dumps(actual, indent=2, default=str) if isinstance(actual, dict) else str(actual)
        return f"status={status_code}; body={body[:300]}"

    if isinstance(expected, int):
        # expected is a status code integer
        if status_code != expected:
            return f"status mismatch: expected={expected}, actual={status_code}"
        return "no structural diff"

    if isinstance(actual, dict) and isinstance(expected, dict):
        parts: list[str] = []
        missing = {k for k in expected if k not in actual}
        extra   = {k for k in actual   if k not in expected}
        if missing:
            parts.append(f"missing keys={sorted(missing)}")
        if extra:
            parts.append(f"extra keys={sorted(extra)}")
        for k in expected:
            if k in actual and actual[k] != expected[k]:
                parts.append(f"{k}: expected={expected[k]!r}, actual={actual[k]!r}")
        return "; ".join(parts) if parts else "no structural diff"

    if actual != expected:
        a_repr = json.dumps(actual, default=str)[:200]
        e_repr = json.dumps(expected, default=str)[:200]
        return f"actual={a_repr}, expected={e_repr}"

    return "no structural diff"
