"""The enterprise run-statistics endpoint must report measurements, not constants.

`/api/enterprise/sla` used to return hardcoded values — `uptime: 99.99`,
`api_response_p99: 145`, `total_checks: 125000`, `failed_checks: 12` — beneath a
"Target: 99.9%" label, and the panel drew its 30-day chart from `Math.random()`,
so the bars changed on every re-render while their tooltips asserted
"Day N: X% uptime".

HANDOVER.md records this as an integrity defect rather than a missing feature:
it is the exact failure mode the product exists to detect, shipped in the
product's own dashboard.

These tests pin the two properties that make the endpoint honest: every number
it returns is counted from the run store, and it reports nothing it cannot
measure.
"""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cherenkov.persistence.run_store import RunRecord, RunStore
from cherenkov.web.routes import enterprise_routes


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client whose SLA endpoint reads an isolated, empty run store."""
    store = RunStore(db_path=tmp_path / "runs.db")
    monkeypatch.setattr(
        "cherenkov.persistence.run_store.get_run_store", lambda: store
    )
    app = FastAPI()
    app.include_router(enterprise_routes.router)
    return TestClient(app), store


def _record(verdict: str, days_ago: int = 0) -> RunRecord:
    stamp = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - days_ago * 86_400)
    )
    return RunRecord(command="verify", verdict=verdict, timestamp=stamp)


# ── It reports what it measures ──────────────────────────────────────────────


def test_counts_come_from_the_run_store(client):
    api, store = client
    for _ in range(3):
        store.save(_record("PASS"))
    store.save(_record("FAIL"))

    body = api.get("/api/enterprise/sla").json()
    assert body["total_runs"] == 4
    assert body["failed_runs"] == 1
    assert body["pass_rate"] == 75.0
    assert body["measured"] is True


def test_empty_store_reports_zero_not_a_plausible_number(client):
    api, _ = client
    body = api.get("/api/enterprise/sla").json()
    assert body["total_runs"] == 0
    assert body["failed_runs"] == 0
    assert body["pass_rate"] is None
    assert body["measured"] is False


def test_counts_change_with_the_data(client):
    """The old endpoint returned the same constants no matter what happened."""
    api, store = client
    first = api.get("/api/enterprise/sla").json()["total_runs"]
    store.save(_record("PASS"))
    second = api.get("/api/enterprise/sla").json()["total_runs"]
    assert (first, second) == (0, 1)


def test_runs_outside_the_window_are_excluded(client):
    api, store = client
    store.save(_record("PASS", days_ago=1))
    store.save(_record("PASS", days_ago=400))
    body = api.get("/api/enterprise/sla").json()
    assert body["total_runs"] == 1


def test_trend_is_a_real_per_day_series(client):
    api, store = client
    store.save(_record("FAIL", days_ago=1))
    store.save(_record("PASS", days_ago=1))

    body = api.get("/api/enterprise/sla").json()
    trend = body["trend"]
    assert len(trend) == body["window_days"]
    # Oldest first, one entry per day, and the day with data carries it.
    assert trend[0]["date"] < trend[-1]["date"]
    populated = [p for p in trend if p["runs"] > 0]
    assert len(populated) == 1
    assert populated[0]["runs"] == 2
    assert populated[0]["failed"] == 1


def test_trend_is_stable_across_calls(client):
    """The old chart was redrawn from Math.random() on every render."""
    api, store = client
    store.save(_record("PASS"))
    first = api.get("/api/enterprise/sla").json()["trend"]
    second = api.get("/api/enterprise/sla").json()["trend"]
    assert first == second


def test_window_is_configurable(client):
    api, store = client
    store.save(_record("PASS", days_ago=10))
    assert api.get("/api/enterprise/sla?days=7").json()["total_runs"] == 0
    assert api.get("/api/enterprise/sla?days=30").json()["total_runs"] == 1


# ── It no longer reports what it cannot measure ──────────────────────────────


@pytest.mark.parametrize("field", ["uptime", "api_response_p99", "total_checks"])
def test_unmeasurable_fields_are_gone(client, field):
    """CHERENKOV never observes the target between runs, so it cannot know
    uptime; run duration is not the target's response latency."""
    api, _ = client
    assert field not in api.get("/api/enterprise/sla").json()


def test_support_ticket_endpoint_is_removed(client):
    """It returned a UUID and "Enterprise support team has been notified" while
    persisting nothing and sending nothing. Per the no-paid-tier decision on
    #754 there is no team to route to, so no implementation makes it true."""
    api, _ = client
    assert api.post("/api/enterprise/support/ticket", json={"msg": "x"}).status_code == 404


# ── The panel that rendered the fabrication ──────────────────────────────────

_UI = (
    "cherenkov/web/ui/src/components/workspaces/EnterpriseWorkspace"
)


def test_sla_panel_does_not_fabricate_chart_data():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    panel = (repo / _UI / "SlaDashboard.tsx").read_text(encoding="utf-8")
    # Bar heights came from Math.random(), so the chart changed on every
    # re-render while its tooltips asserted a specific uptime per day.
    assert "Math.random" not in panel
    # The panel no longer claims an uptime figure at all — nothing measures it.
    assert "uptime" not in panel.lower()


def test_support_portal_component_is_removed():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    assert not (repo / _UI / "SupportPortal.tsx").exists()
    workspace = (repo / _UI / "EnterpriseWorkspace.tsx").read_text(encoding="utf-8")
    assert "SupportPortal" not in workspace
