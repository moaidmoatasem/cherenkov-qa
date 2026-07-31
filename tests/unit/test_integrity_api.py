"""
tests/unit/test_integrity_api.py
Unit tests for the Integrity-as-a-Service API (Pillar 5 — INNOVATION_ROADMAP_V2).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cherenkov.integrity.api import (
    IntegrityAuditRequest,
    VerdictLabel,
    audit_test_integrity,
    router,
)

# ── Test app ──────────────────────────────────────────────────────────────────

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ── Unit tests: core audit logic ──────────────────────────────────────────────

def test_clean_playwright_test_passes():
    """A well-written Playwright test with tight assertions should score PASS."""
    clean_test = """
import { expect } from '@playwright/test';

test('POST /users returns 201', async ({ request }) => {
    const response = await request.post('/users', {
        data: { name: 'Alice', email: 'alice@example.com' }
    });
    expect(response.status()).toBe(201);
    const body = await response.json();
    expect(body.id).toBeDefined();
    expect(body.name).toBe('Alice');
});
"""
    req = IntegrityAuditRequest(test_content=clean_test, test_format="playwright")
    result = audit_test_integrity(req)
    assert result.verdict == VerdictLabel.PASS
    assert result.integrity_score >= 0.90
    assert result.certificate is not None
    assert result.certificate.startswith("sha256:")


def test_weakened_playwright_assertion_detected():
    """Weakened assertion (toBeLessThan(500)) should be flagged."""
    weak_test = """
test('GET /users is okay', async ({ request }) => {
    const response = await request.get('/users');
    expect(response.status()).toBeLessThan(500);
});
"""
    req = IntegrityAuditRequest(test_content=weak_test, test_format="playwright")
    result = audit_test_integrity(req)
    assert result.verdict in (VerdictLabel.WEAK, VerdictLabel.FAIL)
    assert len(result.issues) > 0
    assert any(i.issue_type.value == "WEAKENED_ASSERTION" for i in result.issues)
    assert result.certificate is None


def test_empty_assertion_in_playwright():
    """Tautological expect(true).toBe(true) should be flagged as EMPTY_ASSERTION."""
    tautology_test = """
test('always passes', async () => {
    expect(true).toBe(true);
    expect(1).toBe(1);
});
"""
    req = IntegrityAuditRequest(test_content=tautology_test, test_format="playwright")
    result = audit_test_integrity(req)
    assert result.verdict == VerdictLabel.FAIL
    assert any(i.issue_type.value == "EMPTY_ASSERTION" for i in result.issues)
    assert result.integrity_score < 0.60


def test_clean_pytest_passes():
    """A well-written pytest with tight assertions should score PASS."""
    clean_pytest = """
def test_create_user(client):
    response = client.post('/users', json={'name': 'Bob'})
    assert response.status_code == 201
    data = response.json()
    assert 'id' in data
    assert data['name'] == 'Bob'
"""
    req = IntegrityAuditRequest(test_content=clean_pytest, test_format="pytest")
    result = audit_test_integrity(req)
    assert result.verdict == VerdictLabel.PASS
    assert result.integrity_score >= 0.90
    assert result.certificate is not None


def test_weakened_pytest_assertion():
    """Weakened pytest assertion should be flagged."""
    weak_pytest = """
def test_users(client):
    response = client.get('/users')
    assert response.status_code < 500
"""
    req = IntegrityAuditRequest(test_content=weak_pytest, test_format="pytest")
    result = audit_test_integrity(req)
    assert result.verdict in (VerdictLabel.WEAK, VerdictLabel.FAIL)
    assert any(i.issue_type.value == "WEAKENED_ASSERTION" for i in result.issues)
    assert result.certificate is None


def test_assert_true_pytest_noop():
    """assert True is flagged as EMPTY_ASSERTION."""
    noop_pytest = """
def test_noop():
    assert True
"""
    req = IntegrityAuditRequest(test_content=noop_pytest, test_format="pytest")
    result = audit_test_integrity(req)
    assert any(i.issue_type.value == "EMPTY_ASSERTION" for i in result.issues)


def test_agent_id_preserved():
    """agent_id is preserved in the audit response."""
    req = IntegrityAuditRequest(
        test_content="expect(response.status()).toBe(200);",
        test_format="playwright",
        agent_id="cursor-agent-v1",
    )
    result = audit_test_integrity(req)
    assert result.agent_id == "cursor-agent-v1"


def test_response_has_required_fields():
    """Response includes audit_id, timestamp, duration_ms."""
    req = IntegrityAuditRequest(
        test_content="expect(response.status()).toBe(200);",
        test_format="playwright",
    )
    result = audit_test_integrity(req)
    assert result.audit_id
    assert result.timestamp
    assert result.duration_ms >= 0
    assert result.summary


# ── HTTP integration tests ────────────────────────────────────────────────────

def test_http_audit_endpoint_clean_test():
    """HTTP POST /api/v1/integrity/audit with a clean test returns PASS."""
    payload = {
        "test_content": "expect(response.status()).toBe(201);",
        "test_format": "playwright",
    }
    resp = client.post("/api/v1/integrity/audit", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "PASS"
    assert data["integrity_score"] >= 0.90
    assert data["certificate"] is not None


def test_http_audit_endpoint_weak_test():
    """HTTP POST with weakened assertion returns WEAK or FAIL."""
    payload = {
        "test_content": "expect(response.status()).toBeLessThan(500);",
        "test_format": "playwright",
    }
    resp = client.post("/api/v1/integrity/audit", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] in ("WEAK", "FAIL")
    assert len(data["issues"]) > 0
    assert data["certificate"] is None


def test_http_health_endpoint():
    """GET /api/v1/integrity/health returns 200 with expected fields."""
    resp = client.get("/api/v1/integrity/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "playwright" in data["supported_formats"]
    assert data["certificate_threshold"] == 0.90


def test_http_invalid_format_rejected():
    """Invalid test_format is rejected by validation."""
    payload = {
        "test_content": "some test",
        "test_format": "invalid-format",
    }
    resp = client.post("/api/v1/integrity/audit", json=payload)
    assert resp.status_code == 422


def test_http_empty_content_rejected():
    """Empty test_content is rejected by validation."""
    payload = {"test_content": "", "test_format": "playwright"}
    resp = client.post("/api/v1/integrity/audit", json=payload)
    assert resp.status_code == 422
