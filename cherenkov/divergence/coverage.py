"""
cherenkov/divergence/coverage.py — Spec coverage-gap report.

Given an OpenAPI spec dict and the list of DivergenceReports from a proof run,
computes which endpoints were tested and which were not.

The certificate spec (docs/specs/CHERENKOV_CERTIFICATE.md §1) says:
  "The NOT_checked scope is implicit: anything not in the proof run was not checked."
This module makes that scope explicit and machine-readable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_HTTP_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
)


@dataclass
class EndpointCoverage:
    method: str          # uppercase, e.g. "GET"
    path: str            # e.g. "/pet/{petId}"
    operation_id: str | None
    tested: bool
    divergence_count: int = 0


@dataclass
class CoverageReport:
    total_endpoints: int
    tested_count: int
    untested_count: int
    coverage_pct: float  # 0.0–100.0
    endpoints: list[EndpointCoverage] = field(default_factory=list)

    @property
    def gap_endpoints(self) -> list[EndpointCoverage]:
        return [e for e in self.endpoints if not e.tested]

    @property
    def tested_endpoints(self) -> list[EndpointCoverage]:
        return [e for e in self.endpoints if e.tested]


def _extract_endpoints(spec: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    """Return (METHOD, path, operation_id) tuples for all operations in the spec."""
    result: list[tuple[str, str, str | None]] = []
    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            op_id: str | None = operation.get("operationId")
            result.append((method.upper(), path, op_id))
    return result


def _endpoint_key(method: str, path: str) -> str:
    """Canonical key for matching report endpoints to spec endpoints."""
    return f"{method.upper()} {path}"


def compute_coverage(
    spec: dict[str, Any],
    reports: list,
) -> CoverageReport:
    """Compute which spec endpoints were probed in this proof run.

    `reports` is a list of DivergenceReport (or any object with `.endpoint` str
    attribute in the form "METHOD /path").  Endpoints appearing in any report
    are counted as tested; the rest are the coverage gap.
    """
    spec_endpoints = _extract_endpoints(spec)

    # Build a set of (METHOD, path) keys that appear in the reports
    tested_keys: set[str] = set()
    divergence_by_key: dict[str, int] = {}
    for r in reports:
        raw: str = getattr(r, "endpoint", "") or ""
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split(None, 1)
        if len(parts) == 2:
            key = _endpoint_key(parts[0], parts[1])
        else:
            key = raw.upper()
        tested_keys.add(key)
        divergence_by_key[key] = divergence_by_key.get(key, 0) + 1

    endpoint_list: list[EndpointCoverage] = []
    for method, path, op_id in spec_endpoints:
        key = _endpoint_key(method, path)
        tested = key in tested_keys
        endpoint_list.append(
            EndpointCoverage(
                method=method,
                path=path,
                operation_id=op_id,
                tested=tested,
                divergence_count=divergence_by_key.get(key, 0),
            )
        )

    total = len(endpoint_list)
    tested_count = sum(1 for e in endpoint_list if e.tested)
    untested_count = total - tested_count
    coverage_pct = (tested_count / total * 100.0) if total > 0 else 100.0

    return CoverageReport(
        total_endpoints=total,
        tested_count=tested_count,
        untested_count=untested_count,
        coverage_pct=coverage_pct,
        endpoints=endpoint_list,
    )
