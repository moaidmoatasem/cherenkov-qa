"""HTTP-level tests for /api/enterprise/*.

These endpoints shipped calling methods that do not exist — `OrgManager.get_organization`
and `.create_organization` (the real names are `get_org`/`create_org`, and `create_org`
takes two arguments, not three) and `SOC2ReportGenerator.generate_report(org_name=...)`
against a parameter named `organization`. Every one raised on first request.

They survived because no test ever issued a request to this router: the existing
enterprise tests exercise the domain classes directly. That is the gap these tests close
— they go through the app, so a signature drift between route and domain fails here
instead of in production.
"""

from __future__ import annotations

import os

os.environ.setdefault("CHERENKOV_ENV", "development")

import pytest
from fastapi.testclient import TestClient

from cherenkov.web.api import app
from cherenkov.web.routes import enterprise_routes as er

# raise_server_exceptions=False so an unhandled error surfaces as a 500 response
# rather than propagating — otherwise these assert on an exception type instead of
# on what a real client would actually receive.
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _fresh_org_manager(monkeypatch):
    """Give each test its own OrgManager so ordering cannot leak state."""
    monkeypatch.setattr(er, "_org_manager", type(er._org_manager)())


def test_org_info_returns_200_and_real_fields():
    resp = client.get("/api/enterprise/org")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["name"] == er.DEFAULT_ORG_NAME
    assert body["tier"] == "enterprise"
    # Created with an owner member, so the org is never reported as empty.
    assert body["members"] == 1
    assert body["quota_max_users"] == 100
    assert body["id"].startswith("org_")


def test_org_info_is_idempotent_across_requests():
    """Two GETs must describe the same organization.

    The pre-fix code looked the org up by the fixed id "default-org", which
    `create_org` never assigns — it generates `org_<uuid>`. Had the method names been
    right, the lookup would still have missed every time and minted a brand new
    organization on each request. This pins the endpoint as a read, not a factory.
    """
    first = client.get("/api/enterprise/org")
    second = client.get("/api/enterprise/org")

    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert len(er._org_manager.list_orgs()) == 1


def test_org_info_uses_only_methods_org_manager_actually_has():
    """Regression guard on the exact drift that broke this route."""
    manager = er._org_manager
    assert hasattr(manager, "get_org")
    assert hasattr(manager, "create_org")
    assert not hasattr(manager, "get_organization")
    assert not hasattr(manager, "create_organization")


def test_soc2_report_returns_200_and_names_the_organization():
    resp = client.get("/api/enterprise/soc2/report")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    # The keyword was `org_name=` against a parameter named `organization`, so this
    # call raised TypeError before reaching the generator at all.
    assert body["organization"] == er.DEFAULT_ORG_NAME
    assert body["report_id"].startswith("soc2-")
    assert isinstance(body["controls"], list) and body["controls"]
    assert body["status"] in {"draft", "final"}


def test_soc2_summary_returns_200():
    resp = client.get("/api/enterprise/soc2/summary")
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), dict)


def test_gdpr_status_returns_200():
    resp = client.get("/api/enterprise/gdpr/status")
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), dict)


@pytest.mark.parametrize(
    "path",
    [
        "/api/enterprise/org",
        "/api/enterprise/soc2/report",
        "/api/enterprise/soc2/summary",
        "/api/enterprise/gdpr/status",
        "/api/enterprise/sla",
    ],
)
def test_no_enterprise_endpoint_returns_500(path):
    """Blanket guard: none of these may fail with a server error.

    Phase 13 was recorded as "verified and operational" while three of these raised on
    first call. A parametrised sweep is what makes that claim checkable.
    """
    resp = client.get(path)
    assert resp.status_code != 500, f"{path} -> 500: {resp.text}"


# ── No fabricated data ────────────────────────────────────────────────────────
#
# /sla used to return five hardcoded constants (uptime 99.99, p99 145ms, 125000
# checks, 12 failures, "operational") with nothing telling the caller they were
# invented, and /support/ticket answered "Enterprise support team has been
# notified." while notifying nobody. These pin both as honest.


_FABRICATED_SLA_CONSTANTS = {
    "uptime": 99.99,
    "api_response_p99": 145,
    "total_checks": 125000,
    "failed_checks": 12,
}


def test_sla_reports_no_data_rather_than_zeros_when_nothing_has_run(monkeypatch, tmp_path):
    """With an empty run store the response must say so, not report measurements."""
    from cherenkov.persistence import run_store as rs

    monkeypatch.setattr(rs, "get_run_store", lambda: rs.RunStore(db_path=tmp_path / "runs.db"))

    body = client.get("/api/enterprise/sla").json()
    assert body["measured"] is False
    assert body["status"] == "no_data"
    assert body["total_checks"] == 0
    # Nulls, not zeros — a zero here would render as a real measurement.
    assert body["pass_rate_pct"] is None
    assert body["api_response_p99"] is None
    assert body["trend"] == []


def test_sla_numbers_are_derived_from_recorded_runs(monkeypatch, tmp_path):
    """Feed the store real records; the endpoint must reflect exactly those."""
    from cherenkov.persistence import run_store as rs

    store = rs.RunStore(db_path=tmp_path / "runs.db")
    monkeypatch.setattr(rs, "get_run_store", lambda: store)

    for verdict, duration in [("PASS", 100), ("PASS", 200), ("FAIL", 300), ("WARN", 400)]:
        store.save(rs.RunRecord(command="verify", verdict=verdict, duration_ms=duration))

    body = client.get("/api/enterprise/sla").json()
    assert body["measured"] is True
    assert body["source"] == "run_store"
    assert body["total_checks"] == 4
    assert body["failed_checks"] == 1
    assert body["pass_rate_pct"] == 50.0          # 2 PASS of 4
    assert body["api_response_p99"] == 400        # real max of recorded durations
    assert len(body["trend"]) == 4


def test_sla_no_longer_returns_the_hardcoded_constants(monkeypatch, tmp_path):
    """Regression guard naming the exact invented values."""
    from cherenkov.persistence import run_store as rs

    monkeypatch.setattr(rs, "get_run_store", lambda: rs.RunStore(db_path=tmp_path / "runs.db"))

    body = client.get("/api/enterprise/sla").json()
    # `uptime` is gone entirely: CHERENKOV monitors no availability, so any value
    # for it could only be invented.
    assert "uptime" not in body
    for key, invented in _FABRICATED_SLA_CONSTANTS.items():
        assert body.get(key) != invented, f"{key} still returns the fabricated {invented}"


def test_support_ticket_refuses_rather_than_faking_a_ticket():
    """501, and no invented ticket id or false 'notified' claim."""
    resp = client.post("/api/enterprise/support/ticket", json={"message": "help"})
    assert resp.status_code == 501, resp.text

    body = resp.json()
    # web/errors.py wraps failures as {"error": {"code", "message"}}; fall back to
    # FastAPI's raw `detail` so this does not silently pass if that wrapper changes.
    message = (body.get("error") or {}).get("message") or body.get("detail") or ""
    assert "no ticket was created" in message.lower(), body
    assert "nobody was notified" in message.lower(), body

    # The old response shape must not come back: no invented id, no "created"
    # status, and nowhere a claim that anyone was told.
    assert body.get("ticket_id") is None
    assert body.get("status") != "created"
    assert "has been notified" not in resp.text
