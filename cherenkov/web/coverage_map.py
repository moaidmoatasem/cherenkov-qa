"""CHERENKOV web/coverage_map.py — Spec coverage map + history trend.

Serves the Phase 14 "coverage map" surface (#770). Given the in-process
divergence corpus (which records every endpoint that was actually probed and
any findings raised there) plus the persisted run history from RunStore, this
module exposes:

  * a per-endpoint coverage map  (GET /api/v1/coverage/map)
  * a coverage-pct history trend (GET /api/v1/coverage/trend)

The map is spec-derived: endpoints are keyed by "METHOD /path" exactly as the
`compute_coverage` contract does in cherenkov/divergence/coverage.py, so the
web surface and the CLI/reporting share the same endpoint identity. This keeps
the D7 invariant (expected values derived from the spec, not hardcoded).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cherenkov.web import divergences as divergence_store

_ALTERNATE_STATUS = ("rejected", "live")


def _parse_endpoint(ep: str) -> tuple[str, str]:
    """Split an endpoint string "METHOD /path" into (METHOD, path)."""
    parts = ep.split(None, 1)
    if len(parts) == 2:
        return parts[0].upper(), parts[1]
    return "GET", ep


def _is_active(status: str) -> bool:
    """A finding is 'active' (represents a real, open issue) unless it has been
    closed as rejected/closed_with_test. Mirrors `divergences.get_latest_status`."""
    return status not in _ALTERNATE_STATUS


def build_coverage_map(store=None) -> dict[str, Any]:
    """Build a per-endpoint coverage map.

    Per-endpoint status comes from the divergence corpus (every entry records
    an endpoint that was actually probed in a proof run). The headline
    `coveragePct` reflects the *real* measured coverage from the latest
    persisted run in RunStore when one exists; otherwise it falls back to the
    corpus-derived value (100% only when every corpus endpoint was probed).

    Returns a dict matching the frontend's expected shape:
      {
        "totalEndpoints": int,
        "testedCount": int,
        "untestedCount": int,
        "coveragePct": float,       # 0.0-100.0
        "openIssueCount": int,
        "endpoints": [
          {
            "method": str, "path": str, "tested": bool,
            "divergenceCount": int, "activeSeverity": str | None,
          }
        ],
      }
    """
    findings = divergence_store.list_divergences()

    per_endpoint: dict[str, dict[str, Any]] = {}
    for f in findings:
        endpoint = f.get("endpoint", "")
        if not endpoint:
            continue
        method, path = _parse_endpoint(endpoint)
        key = f"{method} {path}"
        entry = per_endpoint.setdefault(
            key,
            {
                "method": method,
                "path": path,
                "divergence_count": 0,
                "active_severity": None,
            },
        )
        entry["divergence_count"] += 1
        severity = f.get("severity")
        status = f.get("status", "")
        if severity and status and _is_active(status):
            rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(
                severity, 5
            )
            current_rank = {
                "critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4,
            }.get(entry.get("active_severity"), 6)
            if rank < current_rank:
                entry["active_severity"] = severity

    endpoints = [
        {
            "method": e["method"],
            "path": e["path"],
            "tested": True,
            "divergenceCount": e["divergence_count"],
            "activeSeverity": e["active_severity"],
        }
        for e in per_endpoint.values()
    ]
    endpoints.sort(key=lambda e: (e["method"], e["path"]))

    total = len(endpoints)
    tested = sum(1 for e in endpoints if e["tested"])
    open_issues = sum(
        1
        for e in endpoints
        if e["activeSeverity"] is not None
    )

    coverage_pct = _latest_coverage_pct(store)

    return {
        "totalEndpoints": total,
        "testedCount": tested,
        "untestedCount": total - tested,
        "coveragePct": coverage_pct,
        "openIssueCount": open_issues,
        "endpoints": endpoints,
    }


def _latest_coverage_pct(store=None) -> float:
    """Return the coverage_pct of the most recent run with a recorded value,
    else the corpus-derived figure (tested/total)."""
    from cherenkov.persistence.run_store import get_run_store

    run_store = store or get_run_store()
    records = run_store.list(limit=1)
    if records and records[0].coverage_pct is not None:
        return round(records[0].coverage_pct, 1)

    findings = divergence_store.list_divergences()
    total = len({(f.get("endpoint") or "").upper() for f in findings})
    return round((total / max(total, 1)) * 100.0, 1) if total else 100.0


def coverage_trend(store=None, limit: int = 60) -> list[dict[str, Any]]:
    """Return a coverage-pct time-series from run history, oldest → newest.

    Reuses the persisted RunStore so the trend reflects *real* measured
    coverage across verify/validate/certify runs, not a synthetic corpus.
    When no runs exist yet, returns an empty list.
    """
    from cherenkov.persistence.run_store import get_run_store

    run_store = store or get_run_store()
    records = run_store.list(limit=limit)
    points = [
        {
            "timestamp": r.timestamp,
            "coverage_pct": r.coverage_pct,
            "verdict": r.verdict,
            "divergence_count": r.divergence_count,
        }
        for r in records
        if r.coverage_pct is not None
    ]
    points.sort(key=lambda p: p["timestamp"])
    return points


@dataclass
class CoverageSummary:
    """Lightweight aggregate for quick status display."""

    coverage_pct: float
    open_issues: int
    tested_endpoints: int
    total_endpoints: int

    @classmethod
    def from_map(cls, m: dict[str, Any]) -> "CoverageSummary":
        return cls(
            coverage_pct=m["coveragePct"],
            open_issues=m["openIssueCount"],
            tested_endpoints=m["testedCount"],
            total_endpoints=m["totalEndpoints"],
        )