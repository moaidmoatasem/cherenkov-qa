"""Unit tests for cherenkov/web/routes/certificate_routes.py."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cherenkov.core.certificate import issue_certificate
from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceReport,
    Severity,
    StageMeta,
)
from cherenkov.web.routes.certificate_routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _make_report(sev: Severity = Severity.MEDIUM) -> DivergenceReport:
    ev = DivergenceEvidence(
        request_summary="GET /pet/1 -> 404",
        diff="status: expected=200 actual=404",
        response_actual="404",
        response_expected="200",
    )
    return DivergenceReport(
        id="test-001",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="spec says 200",
        claim_b="impl returns 404",
        severity=sev,
        endpoint="GET /pet/1",
        evidence=ev,
        repro_steps=["GET /pet/1"],
        metadata=StageMeta(stage="proof_run"),
    )


def test_verify_valid_unsigned_certificate():
    cert = issue_certificate(reports=[_make_report()], base_url="https://api.example.com", run_id="run-1")
    resp = client.post("/api/v1/certificates/verify", json={"certificate": cert.model_dump()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["run_id"] == "run-1"
    assert body["verdict"] == "WARN"
    assert body["summary"]["medium"] == 1
    assert body["signed"] is False


def test_verify_signed_certificate():
    key = b"secret-signing-key"
    cert = issue_certificate(reports=[], base_url="https://api.example.com", run_id="run-2", signing_key=key)
    resp = client.post("/api/v1/certificates/verify", json={"certificate": cert.model_dump()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["signed"] is True
    assert body["verdict"] == "PASS"


def test_verify_tampered_certificate_is_invalid():
    cert = issue_certificate(reports=[_make_report(Severity.HIGH)], base_url="https://api.example.com", run_id="run-3")
    tampered = cert.model_dump()
    tampered["verdict"] = "PASS"  # mutate a field after sealing without recomputing fingerprint
    resp = client.post("/api/v1/certificates/verify", json={"certificate": tampered})
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False


def test_verify_malformed_certificate_returns_400():
    resp = client.post("/api/v1/certificates/verify", json={"certificate": {"not": "a cert"}})
    assert resp.status_code == 400
