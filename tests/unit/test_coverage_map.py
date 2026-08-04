"""Unit tests for cherenkov/web/coverage_map.py and coverage_routes.py."""
from __future__ import annotations

import os

os.environ.setdefault("CHERENKOV_ENV", "development")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from cherenkov.persistence.run_store import RunRecord
from cherenkov.web import coverage_map
from cherenkov.web.api import app


class _FakeStore:
    """Minimal stand-in for RunStore returning a fixed record list."""

    def __init__(self, records):
        self._records = records

    def list(self, target_url=None, command=None, limit=50):
        return self._records[:limit]


def _run(coverage_pct, verdict="PASS", divergence_count=0, timestamp="2026-08-01T00:00:00Z"):
    return RunRecord(
        run_id=f"run-{coverage_pct}",
        command="verify",
        target_url="https://example.test",
        coverage_pct=coverage_pct,
        verdict=verdict,
        divergence_count=divergence_count,
        timestamp=timestamp,
    )


class TestBuildCoverageMap:
    def test_returns_corpus_shape(self):
        m = coverage_map.build_coverage_map()
        assert "totalEndpoints" in m
        assert "testedCount" in m
        assert "untestedCount" in m
        assert "coveragePct" in m
        assert "openIssueCount" in m
        assert isinstance(m["endpoints"], list)

    def test_endpoints_have_expected_fields(self):
        m = coverage_map.build_coverage_map()
        for ep in m["endpoints"]:
            assert set(ep) == {
                "method",
                "path",
                "tested",
                "divergenceCount",
                "activeSeverity",
            }

    def test_endpoint_methods_uppercased(self):
        m = coverage_map.build_coverage_map()
        assert all(ep["method"] == ep["method"].upper() for ep in m["endpoints"])

    def test_parse_endpoint_defaults_method(self):
        from cherenkov.web.coverage_map import _parse_endpoint
        assert _parse_endpoint("/user/login") == ("GET", "/user/login")

    def test_parse_endpoint_splits(self):
        from cherenkov.web.coverage_map import _parse_endpoint
        assert _parse_endpoint("post /pet") == ("POST", "/pet")

    def test_active_severity_ranks_lowest(self):
        m = coverage_map.build_coverage_map()
        for ep in m["endpoints"]:
            if ep["activeSeverity"] is not None:
                assert ep["activeSeverity"] in {
                    "critical",
                    "high",
                    "medium",
                    "low",
                    "info",
                }

    def test_open_issue_count(self):
        m = coverage_map.build_coverage_map()
        assert m["openIssueCount"] >= 0
        assert m["openIssueCount"] <= m["totalEndpoints"]


class TestCoverageTrend:
    def test_empty_store_returns_empty(self):
        out = coverage_map.coverage_trend(store=_FakeStore([]), limit=60)
        assert out == []

    def test_returns_sorted_points(self):
        store = _FakeStore(
            [
                _run(80.0, timestamp="2026-08-02T00:00:00Z"),
                _run(50.0, timestamp="2026-08-01T00:00:00Z"),
            ]
        )
        out = coverage_map.coverage_trend(store=store, limit=60)
        assert [p["timestamp"] for p in out] == [
            "2026-08-01T00:00:00Z",
            "2026-08-02T00:00:00Z",
        ]
        assert [p["coverage_pct"] for p in out] == [50.0, 80.0]

    def test_skips_runs_without_coverage(self):
        store = _FakeStore([_run(None, verdict="PASS")])
        assert coverage_map.coverage_trend(store=store, limit=60) == []

    def test_includes_verdict_and_divergences(self):
        store = _FakeStore([_run(66.0, verdict="WARN", divergence_count=3)])
        out = coverage_map.coverage_trend(store=store, limit=60)
        assert out[0]["verdict"] == "WARN"
        assert out[0]["divergence_count"] == 3


class TestCoverageRoutes:
    @pytest.fixture(autouse=True)
    def _isolate_store(self):
        from cherenkov.persistence import run_store as rs_module
        with patch.object(rs_module, "_store", None):
            with patch.object(rs_module, "get_run_store", return_value=_FakeStore([_run(75.0)])):
                yield

    def test_map_endpoint(self):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/coverage/map")
        assert r.status_code == 200
        body = r.json()
        assert "endpoints" in body
        assert body["testedCount"] >= 0

    def test_trend_endpoint(self):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/coverage/trend")
        assert r.status_code == 200
        body = r.json()
        assert "points" in body
        assert body["points"][0]["coverage_pct"] == 75.0

    def test_summary_endpoint(self):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/coverage/summary")
        assert r.status_code == 200
        body = r.json()
        for key in ("coveragePct", "openIssueCount", "testedCount", "totalEndpoints"):
            assert key in body
