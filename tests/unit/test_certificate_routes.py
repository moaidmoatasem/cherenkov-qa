from __future__ import annotations

import os

os.environ.setdefault("CHERENKOV_ENV", "development")

from fastapi.testclient import TestClient

from cherenkov.core.certificate import issue_certificate
from cherenkov.web.api import app

client = TestClient(app, raise_server_exceptions=False)


def _issue(signing_key: bytes | None = None):
    cert = issue_certificate(reports=[], base_url="https://example.test", signing_key=signing_key)
    return cert.model_dump()


def test_verify_valid_unsigned_certificate():
    r = client.post("/api/v1/certificates/verify", json={"certificate": _issue()})
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["verdict"] == "PASS"
    assert body["subject"]["base_url"] == "https://example.test"
    assert body["signature_present"] is False


def test_verify_tampered_certificate_is_invalid():
    data = _issue()
    data["subject"]["base_url"] = "https://attacker.test"
    r = client.post("/api/v1/certificates/verify", json={"certificate": data})
    assert r.status_code == 200
    assert r.json()["valid"] is False


def test_verify_signed_certificate_with_correct_key():
    key = b"\x01" * 32
    data = _issue(signing_key=key)
    r = client.post(
        "/api/v1/certificates/verify",
        json={"certificate": data, "signing_key": key.hex()},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["signature_present"] is True


def test_verify_signed_certificate_with_wrong_key():
    data = _issue(signing_key=b"\x01" * 32)
    r = client.post(
        "/api/v1/certificates/verify",
        json={"certificate": data, "signing_key": (b"\x02" * 32).hex()},
    )
    assert r.status_code == 200
    assert r.json()["valid"] is False


def test_verify_malformed_certificate_returns_422():
    r = client.post("/api/v1/certificates/verify", json={"certificate": {"not": "a cert"}})
    assert r.status_code == 422


def test_verify_bad_signing_key_hex_returns_400():
    r = client.post(
        "/api/v1/certificates/verify",
        json={"certificate": _issue(), "signing_key": "not-hex"},
    )
    assert r.status_code == 400
