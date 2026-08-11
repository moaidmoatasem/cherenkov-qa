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
        """Placeholder docstring.

:param target_url: <description>
:param command: <description>
:param limit: <description>
:return: <description>"""
        return self._records[:limit]


def _run(coverage_pct, verdict="PASS", divergence_count=0, timestamp="2026-08-01T00:00:00Z", target_url="https://example.test"):
    return RunRecord(
        run_id=f"run-{coverage_pct}-{timestamp}",
        command="verify",
        target_url=target_url,
        coverage_pct=coverage_pct,
        verdict=verdict,
        divergence_count=divergence_count,
        timestamp=timestamp,
    )
    """Placeholder docstring.

<description>"""
class TestBuildCoverageMap:
    def test_returns_corpus_shape(self):
        """Placeholder docstring.

:return: <description>"""
        m = coverage_map.build_coverage_map()
        assert "totalEndpoints" in m
        assert "testedCount" in m
        assert "untestedCount" in m
        assert "coveragePct" in m
        assert "openIssueCount" in m
        assert isinstance(m["endpoints"], list)

    def test_endpoints_have_expected_fields(self):
        """Placeholder docstring.

:return: <description>"""
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
        """Placeholder docstring.

:return: <description>"""
        m = coverage_map.build_coverage_map()
        assert all(ep["method"] == ep["method"].upper() for ep in m["endpoints"])

    def test_parse_endpoint_defaults_method(self):
        """Placeholder docstring.

:return: <description>"""
        from cherenkov.web.coverage_map import _parse_endpoint
        assert _parse_endpoint("/user/login") == ("GET", "/user/login")

    def test_parse_endpoint_splits(self):
        """Placeholder docstring.

:return: <description>"""
        from cherenkov.web.coverage_map import _parse_endpoint
        assert _parse_endpoint("post /pet") == ("POST", "/pet")

    def test_active_severity_ranks_lowest(self):
        """Placeholder docstring.

:return: <description>"""
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
    """Placeholder docstring.

<description>"""
    def test_open_issue_count(self):
        """Placeholder docstring.

:return: <description>"""
        m = coverage_map.build_coverage_map()
        assert m["openIssueCount"] >= 0
        assert m["openIssueCount"] <= m["totalEndpoints"]


class TestCoverageTrend:
    def test_empty_store_returns_empty(self):
        """Placeholder docstring.

:return: <description>"""
        out = coverage_map.coverage_trend(store=_FakeStore([]), limit=60)
        assert out == []

    def test_returns_sorted_points(self):
        """Placeholder docstring.

:return: <description>"""
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
        """Placeholder docstring.

:return: <description>"""
    """Placeholder docstring.

<description>"""
        store = _FakeStore([_run(None, verdict="PASS")])
        assert coverage_map.coverage_trend(store=store, limit=60) == []

    def test_includes_verdict_and_divergences(self):
        """Placeholder docstring.

:return: <description>"""
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
        """Placeholder docstring.

:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/coverage/map")
        assert r.status_code == 200
        body = r.json()
        assert "endpoints" in body
        assert body["testedCount"] >= 0

    def test_trend_endpoint(self):
        """Placeholder docstring.

:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/coverage/trend")
        assert r.status_code == 200
    """Placeholder docstring.

<description>"""
        body = r.json()
        assert "points" in body
        assert body["points"][0]["coverage_pct"] == 75.0

    def test_summary_endpoint(self):
        """Placeholder docstring.

:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/coverage/summary")
        assert r.status_code == 200
        body = r.json()
        for key in ("coveragePct", "openIssueCount", "testedCount", "totalEndpoints"):
            assert key in body


class TestConformanceRoutes:
    @pytest.fixture
    def _conv_store(self):
        return _FakeStore(
            [
                _run(60.0, verdict="PASS", divergence_count=0, timestamp="2026-08-01T00:00:00Z"),
                _run(50.0, verdict="WARN", divergence_count=2, timestamp="2026-08-02T00:00:00Z"),
                _run(40.0, verdict="FAIL", divergence_count=5, timestamp="2026-08-03T00:00:00Z"),
            ]
        )

    @pytest.fixture
    def _patched_store(self, _conv_store):
        from cherenkov.persistence import run_store as rs_module
        with patch.object(rs_module, "_store", None):
            with patch.object(rs_module, "get_run_store", return_value=_conv_store):
                yield

    def test_conformance_trend_endpoint(self, _patched_store):
        """Placeholder docstring.

:param _patched_store: <description>
:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/coverage/conformance-trend")
        assert r.status_code == 200
        body = r.json()
        assert "points" in body
        assert len(body["points"]) == 3
        assert body["points"][0]["verdict"] == "PASS"
        assert body["points"][2]["verdict"] == "FAIL"

    def test_conformance_summary_endpoint(self, _patched_store):
        """Placeholder docstring.

:param _patched_store: <description>
:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
    """Placeholder docstring.

<description>"""
        r = client.get("/api/v1/coverage/conformance-summary")
        assert r.status_code == 200
        body = r.json()
        assert body["passCount"] == 1
        assert body["warnCount"] == 1
        assert body["failCount"] == 1
        assert body["totalRuns"] == 3
        assert body["latestVerdict"] == "FAIL"
        assert body["latestDivergenceCount"] == 5
        assert len(body["trend"]) == 3

    def test_conformance_trend_includes_target_url(self, _patched_store):
        """Placeholder docstring.

:param _patched_store: <description>
:return: <description>"""
        out = coverage_map.conformance_trend()
        assert all("target_url" in p for p in out)


class TestDetectRegressions:
    def test_empty_store_no_regressions(self):
        """Placeholder docstring.

:return: <description>"""
        store = _FakeStore([])
        assert coverage_map.detect_regressions(store=store, limit=50) == []

    def test_single_run_no_regressions(self):
        """Placeholder docstring.

:return: <description>"""
        store = _FakeStore(
            [_run(80.0, verdict="PASS", divergence_count=0, timestamp="2026-08-03T00:00:00Z")]
        )
        assert coverage_map.detect_regressions(store=store, limit=50) == []

    def test_verdict_downgrade_detected(self):
        """Placeholder docstring.

:return: <description>"""
        store = _FakeStore(
            [
                _run(80.0, verdict="PASS", divergence_count=0, timestamp="2026-08-01T00:00:00Z"),
                _run(80.0, verdict="FAIL", divergence_count=0, timestamp="2026-08-02T00:00:00Z"),
            ]
        )
        regs = coverage_map.detect_regressions(store=store, limit=50)
        kinds = [r["kind"] for r in regs]
        assert "verdict_downgrade" in kinds
        vd = next(r for r in regs if r["kind"] == "verdict_downgrade")
        assert "PASS -> FAIL" in vd["detail"]

    def test_coverage_regression_detected(self):
        """Placeholder docstring.

:return: <description>"""
        store = _FakeStore(
            [
                _run(100.0, verdict="PASS", divergence_count=0, timestamp="2026-08-01T00:00:00Z"),
                _run(40.0, verdict="PASS", divergence_count=0, timestamp="2026-08-02T00:00:00Z"),
            ]
        )
        regs = coverage_map.detect_regressions(store=store, limit=50)
        kinds = [r["kind"] for r in regs]
        assert "coverage_regression" in kinds
        cr = next(r for r in regs if r["kind"] == "coverage_regression")
        assert "100.0%" in cr["detail"]

    def test_divergence_spike_detected(self):
        """Placeholder docstring.

:return: <description>"""
        store = _FakeStore(
            [
                _run(80.0, verdict="PASS", divergence_count=0, timestamp="2026-08-01T00:00:00Z"),
                _run(80.0, verdict="WARN", divergence_count=3, timestamp="2026-08-02T00:00:00Z"),
            ]
        )
        regs = coverage_map.detect_regressions(store=store, limit=50)
        kinds = [r["kind"] for r in regs]
        assert "divergence_spike" in kinds

    def test_no_regression_when_improving(self):
        """Placeholder docstring.

:return: <description>"""
        store = _FakeStore(
            [
                _run(40.0, verdict="DIVERGENT", divergence_count=5, timestamp="2026-08-01T00:00:00Z"),
                _run(90.0, verdict="PASS", divergence_count=0, timestamp="2026-08-02T00:00:00Z"),
            ]
        )
        assert coverage_map.detect_regressions(store=store, limit=50) == []
    """Placeholder docstring.

<description>"""
    def test_multiple_regressions_recorded(self):
        """Placeholder docstring.

:return: <description>"""
        store = _FakeStore(
            [
                _run(90.0, verdict="PASS", divergence_count=0, timestamp="2026-08-01T00:00:00Z"),
                _run(40.0, verdict="FAIL", divergence_count=4, timestamp="2026-08-02T00:00:00Z"),
            ]
        )
        regs = coverage_map.detect_regressions(store=store, limit=50)
        kinds = {r["kind"] for r in regs}
        assert kinds == {"verdict_downgrade", "coverage_regression", "divergence_spike"}

    def test_grouped_by_target_url(self):
        """Regressions compared only within the same target_url."""
        store = _FakeStore(
            [
                _run(90.0, verdict="PASS", divergence_count=0, timestamp="2026-08-01T00:00:00Z", target_url="http://a.test"),
                _run(40.0, verdict="FAIL", divergence_count=4, timestamp="2026-08-02T00:00:00Z", target_url="http://b.test"),
            ]
        )
        # different targets → no comparison → no regressions
        assert coverage_map.detect_regressions(store=store, limit=50) == []


class TestRegressionsRoute:
    @pytest.fixture
    def _reg_store(self):
        return _FakeStore(
            [
                _run(80.0, verdict="PASS", divergence_count=0, timestamp="2026-08-01T00:00:00Z"),
                _run(40.0, verdict="FAIL", divergence_count=3, timestamp="2026-08-02T00:00:00Z"),
            ]
        )

    @pytest.fixture
    def _patched(self, _reg_store):
        from cherenkov.persistence import run_store as rs_module
        with patch.object(rs_module, "_store", None):
            with patch.object(rs_module, "get_run_store", return_value=_reg_store):
                yield

    def test_regressions_endpoint(self, _patched):
        """Placeholder docstring.

:param _patched: <description>
:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/coverage/regressions")
        assert r.status_code == 200
        body = r.json()
        assert "regressions" in body
        kinds = {reg["kind"] for reg in body["regressions"]}
        assert "verdict_downgrade" in kinds
        assert "coverage_regression" in kinds
        assert "divergence_spike" in kinds
