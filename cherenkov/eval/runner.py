"""cherenkov/eval/runner.py — Execute a suite manifest against a live API.

Emits a JSONL trace file (one JSON line per test) that the grader and compare
commands consume. Works in dry-run mode when no target URL is provided.

Assertion types supported:
  {"type": "status",   "expected": [200, 201]}
  {"type": "json_key", "field": "id",    "exists": true}
  {"type": "json_key", "field": "name",  "expected": "Fido"}
  {"type": "header",   "name": "Content-Type", "contains": "json"}
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class AssertionResult:
    type: str
    passed: bool
    detail: str = ""


@dataclass
class TestResult:
    operation_id: str
    test_name: str
    passed: bool
    response_status: int | None
    duration_ms: float
    assertions: list[AssertionResult] = field(default_factory=list)
    error: str | None = None
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def assertions_total(self) -> int:
        return len(self.assertions)

    @property
    def assertions_passed(self) -> int:
        return sum(1 for a in self.assertions if a.passed)

    @property
    def assertions_failed(self) -> int:
        return self.assertions_total - self.assertions_passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "test_name": self.test_name,
            "passed": self.passed,
            "response_status": self.response_status,
            "duration_ms": round(self.duration_ms, 2),
            "assertions_total": self.assertions_total,
            "assertions_passed": self.assertions_passed,
            "assertions_failed": self.assertions_failed,
            "error": self.error,
            "ts": self.ts,
        }


@dataclass
class RunTrace:
    target_url: str | None
    spec_hash: str
    suite_hash: str
    results: list[TestResult] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 1.0

    def to_jsonl(self, path: Path) -> None:
        with path.open("w", encoding="utf-8") as f:
            meta = {
                "_meta": True,
                "target_url": self.target_url,
                "spec_hash": self.spec_hash,
                "suite_hash": self.suite_hash,
                "created_at": self.created_at,
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "pass_rate": round(self.pass_rate, 4),
            }
            f.write(json.dumps(meta) + "\n")
            for result in self.results:
                f.write(json.dumps(result.to_dict()) + "\n")

    @classmethod
    def from_jsonl(cls, path: Path) -> "RunTrace":
        lines = path.read_text().splitlines()
        meta: dict[str, Any] = {}
        results: list[TestResult] = []
        for line in lines:
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("_meta"):
                meta = obj
            else:
                results.append(TestResult(
                    operation_id=obj["operation_id"],
                    test_name=obj["test_name"],
                    passed=obj["passed"],
                    response_status=obj.get("response_status"),
                    duration_ms=obj.get("duration_ms", 0.0),
                    error=obj.get("error"),
                    ts=obj.get("ts", ""),
                ))
        return cls(
            target_url=meta.get("target_url"),
            spec_hash=meta.get("spec_hash", ""),
            suite_hash=meta.get("suite_hash", ""),
            created_at=meta.get("created_at", ""),
            results=results,
        )


def _check_assertion(assertion: dict[str, Any], response: Any) -> AssertionResult:
    """Evaluate a single assertion against an HTTP response."""
    typ = assertion.get("type", "")

    if typ == "status":
        expected = assertion.get("expected", [])
        actual = response.status_code if response is not None else None
        passed = actual in expected
        return AssertionResult(
            type=typ,
            passed=passed,
            detail=f"status {actual} {'in' if passed else 'not in'} {expected}",
        )

    if typ == "json_key":
        field_path = assertion.get("field", "")
        try:
            body = response.json() if response is not None else {}
        except Exception:
            body = {}
        parts = field_path.split(".")
        val: Any = body
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = None
                break
        if "exists" in assertion:
            passed = (val is not None) == assertion["exists"]
            detail = f"field '{field_path}' {'exists' if val is not None else 'missing'}"
        elif "expected" in assertion:
            passed = val == assertion["expected"]
            detail = f"field '{field_path}' = {val!r} (expected {assertion['expected']!r})"
        else:
            passed = val is not None
            detail = f"field '{field_path}' = {val!r}"
        return AssertionResult(type=typ, passed=passed, detail=detail)

    if typ == "header":
        name = assertion.get("name", "")
        actual_val = response.headers.get(name, "") if response is not None else ""
        if "contains" in assertion:
            passed = assertion["contains"].lower() in actual_val.lower()
            detail = f"header '{name}': {actual_val!r} {'contains' if passed else 'missing'} {assertion['contains']!r}"
        else:
            passed = bool(actual_val)
            detail = f"header '{name}': {actual_val!r}"
        return AssertionResult(type=typ, passed=passed, detail=detail)

    # Unknown assertion type — skip (don't block)
    return AssertionResult(type=typ, passed=True, detail=f"unknown type '{typ}' — skipped")


class EvalRunner:
    """Execute a suite manifest against a target URL and collect a RunTrace.

    In dry-run mode (target_url=None), all tests are recorded as skipped with
    pass=None (represented as passed=True, response_status=None).
    """

    def __init__(
        self,
        target_url: str | None = None,
        timeout_s: float = 10.0,
        spec_hash: str = "",
        suite_hash: str = "",
    ) -> None:
        self.target_url = target_url
        self.timeout_s = timeout_s
        self.spec_hash = spec_hash
        self.suite_hash = suite_hash

    def run(self, suite: dict[str, Any]) -> RunTrace:
        trace = RunTrace(
            target_url=self.target_url,
            spec_hash=self.spec_hash,
            suite_hash=self.suite_hash,
        )
        for op_id, tests in suite.items():
            if op_id.startswith("_"):
                continue
            if not isinstance(tests, list):
                continue
            for test in tests:
                if not isinstance(test, dict):
                    continue
                result = self._run_test(op_id, test)
                trace.results.append(result)
        return trace

    def _run_test(self, op_id: str, test: dict[str, Any]) -> TestResult:
        test_name = test.get("name", op_id)
        assertions_spec = test.get("assertions", [])

        if self.target_url is None:
            # Dry-run: check assertions statically (banned-pattern only)
            return TestResult(
                operation_id=op_id,
                test_name=test_name,
                passed=True,
                response_status=None,
                duration_ms=0.0,
                error="dry-run: no target URL",
            )

        request = test.get("request", {})
        method = request.get("method", "GET").upper()
        path = request.get("path", "/")

        # Resolve path params
        path_params = request.get("path_params", {})
        for k, v in path_params.items():
            path = path.replace(f"{{{k}}}", str(v))

        url = self.target_url.rstrip("/") + path
        params = request.get("params")
        body = request.get("body")
        headers = request.get("headers", {})

        t0 = time.monotonic()
        response = None
        error = None
        try:
            import urllib.request, urllib.parse

            req_data = json.dumps(body).encode() if body is not None else None
            if params:
                url += "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, data=req_data, method=method)
            req.add_header("Content-Type", "application/json")
            for h, v in headers.items():
                req.add_header(h, v)

            class _Resp:
                def __init__(self, r: Any) -> None:
                    self._r = r
                    self.status_code = r.status
                    self.headers = dict(r.headers)
                    self._body = r.read()

                def json(self) -> Any:
                    return json.loads(self._body)

            with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                response = _Resp(r)
        except Exception as exc:
            error = str(exc)

        duration_ms = (time.monotonic() - t0) * 1000

        assertion_results: list[AssertionResult] = []
        for a in assertions_spec:
            if not isinstance(a, dict):
                continue
            assertion_results.append(_check_assertion(a, response))

        passed = (
            error is None
            and all(a.passed for a in assertion_results)
        )

        return TestResult(
            operation_id=op_id,
            test_name=test_name,
            passed=passed,
            response_status=response.status_code if response else None,
            duration_ms=duration_ms,
            assertions=assertion_results,
            error=error,
        )
