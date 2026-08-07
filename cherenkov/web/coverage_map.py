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
    from cherenkov.persistence.run_store import get_run_store, spec_hash
    from cherenkov.core.config_loader import load_effective_config
    from cherenkov.cli.loaders import load_spec
    from cherenkov.divergence.coverage import _extract_endpoints
    import json

    findings = divergence_store.list_divergences()

    run_store = store or get_run_store()
    
    target_hash = ""
    records = run_store.list(limit=1)
    if records:
        target_hash = records[0].spec_hash

    spec_dict = None
    if target_hash:
        cfg = load_effective_config()
        for path in cfg.get("sources.openapi", []):
            candidate = load_spec(path)
            if candidate:
                h = spec_hash(json.dumps(candidate, sort_keys=True).encode())
                if h == target_hash:
                    spec_dict = candidate
                    break

    endpoints_from_spec = []
    if spec_dict:
        endpoints_from_spec = _extract_endpoints(spec_dict)

    per_endpoint: dict[str, dict[str, Any]] = {}
    
    # Pre-populate all endpoints from the spec as untested
    for method, path, _ in endpoints_from_spec:
        key = f"{method.upper()} {path}"
        per_endpoint[key] = {
            "method": method.upper(),
            "path": path,
            "tested": False,
            "divergence_count": 0,
            "active_severity": None,
        }

    for f in findings:
        endpoint = f.get("endpoint", "")
        if not endpoint:
            continue
        method, path = _parse_endpoint(endpoint)
        key = f"{method.upper()} {path}"
        entry = per_endpoint.setdefault(
            key,
            {
                "method": method.upper(),
                "path": path,
                "tested": False,
                "divergence_count": 0,
                "active_severity": None,
            },
        )
        entry["tested"] = True
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
            "tested": e["tested"],
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


@dataclass
class ConformancePoint:
    """One run's conformance snapshot for the continuous trend (#767)."""

    timestamp: str
    verdict: str
    divergence_count: int
    coverage_pct: float | None


def conformance_trend(store=None, limit: int = 60) -> list[dict[str, Any]]:
    """Return a continuous conformance trend over persisted run history (#767).

    Unlike `coverage_trend` (which focuses on the coverage-pct headline),
    this surfaces each run's verdict + divergence count so the dashboard can
    visualise whether the service is drifting toward or away from the spec,
    not just how much surface was probed.

    Verdict strings are normalised to the RunStore contract (PASS/WARN/FAIL)
    and points are ordered oldest → newest. No runs recorded yet → empty list.
    """
    from cherenkov.persistence.run_store import get_run_store

    run_store = store or get_run_store()
    records = run_store.list(limit=limit)
    points = [
        {
            "timestamp": r.timestamp,
            "verdict": (r.verdict or "").upper(),
            "divergence_count": r.divergence_count,
            "coverage_pct": r.coverage_pct,
            "target_url": r.target_url,
        }
        for r in records
    ]
    points.sort(key=lambda p: p["timestamp"])
    return points


def conformance_summary(store=None) -> dict[str, Any]:
    """Aggregate the trend into headline numbers for status display.

    Returns pass/warn/fail run counts across the recorded history, plus the
    most recent run's verdict and divergence count (or None if no runs exist).
    """
    trend = conformance_trend(store=store, limit=500)
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for p in trend:
        verdict = p["verdict"]
        if verdict in counts:
            counts[verdict] += 1
    latest = trend[-1] if trend else None
    return {
        "totalRuns": len(trend),
        "passCount": counts["PASS"],
        "warnCount": counts["WARN"],
        "failCount": counts["FAIL"],
        "latestVerdict": latest["verdict"] if latest else None,
        "latestDivergenceCount": latest["divergence_count"] if latest else None,
        "latestCoveragePct": latest["coverage_pct"] if latest else None,
        "trend": trend[-20:],
    }


# ── Phase 14 #771: Regression detection ──────────────────────────────────────

# Ordered best → worst for comparing consecutive runs. Mirrors the
# OverallVerdict semantics (models.py): CERTIFIED/PASS best, DIVERGENT worst.
_VERDICT_RANK: dict[str, int] = {
    "PASS": 0,
    "CERTIFIED": 0,
    "SUSPECT": 1,
    "WARN": 2,
    "DIVERGENT": 2,
    "FAIL": 3,
    "INCONCLUSIVE": 3,
}


def _verdict_rank(verdict: str) -> int:
    return _VERDICT_RANK.get((verdict or "").upper(), 1)


def detect_regressions(store=None, limit: int = 200) -> list[dict[str, Any]]:
    """Detect conformance regressions across consecutive runs (#771).

    Walks the run history (oldest → newest) and flags three regression kinds:
      * `verdict_downgrade` — a run whose verdict is strictly worse than the
        previous run's for the same target.
      * `coverage_regression` — coverage_pct dropped versus the prior run.
      * `divergence_spike` — divergence_count rose versus the prior run.

    Each returned entry is spec-derived (verdict + divergence counts come from
    persisted RunStore records, not hardcoded). The list is ordered by timestamp
    (most recent first).
    """
    trend = conformance_trend(store=store, limit=limit)

    # Group consecutive runs by target so a verdict downgrade is only compared
    # against the *same* service under test.
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in trend:
        target = p.get("target_url", "unknown")
        groups.setdefault(target, []).append(p)

    regressions: list[dict[str, Any]] = []
    for target, points in groups.items():
        points.sort(key=lambda p: p["timestamp"])
        for prev, cur in zip(points, points[1:]):
            base = {
                "target_url": target,
                "prev_timestamp": prev["timestamp"],
                "cur_timestamp": cur["timestamp"],
            }
            prev_verdict = (prev["verdict"] or "").upper()
            cur_verdict = (cur["verdict"] or "").upper()

            if _verdict_rank(cur_verdict) > _verdict_rank(prev_verdict):
                regressions.append(
                    {
                        **base,
                        "kind": "verdict_downgrade",
                        "detail": f"{prev_verdict} -> {cur_verdict}",
                    }
                )

            if (
                cur.get("coverage_pct") is not None
                and prev.get("coverage_pct") is not None
                and cur["coverage_pct"] < prev["coverage_pct"]
            ):
                regressions.append(
                    {
                        **base,
                        "kind": "coverage_regression",
                        "detail": (
                            f"{prev['coverage_pct']:.1f}% -> "
                            f"{cur['coverage_pct']:.1f}%"
                        ),
                    }
                )

            if cur["divergence_count"] > prev["divergence_count"]:
                regressions.append(
                    {
                        **base,
                        "kind": "divergence_spike",
                        "detail": (
                            f"{prev['divergence_count']} -> "
                            f"{cur['divergence_count']}"
                        ),
                    }
                )

    regressions.reverse()
    return regressions