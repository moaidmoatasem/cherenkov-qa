"""
cherenkov/core/certificate.py — E3.1: Verifiable trust certificate.

A VerificationCertificate is a JSON artifact produced after a proof run.
It carries a SHA-256 fingerprint of its own content (excluding the fingerprint
field) so any recipient can detect tampering offline.  An optional HMAC-SHA256
signature layer lets callers bind the cert to a signing key.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


# ── sub-models ─────────────────────────────────────────────────────────────────

class CertSubject(BaseModel):
    base_url: str
    spec_hash: str | None = None  # SHA-256 of the raw spec bytes, if available


class CertSummary(BaseModel):
    total: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    critical: int = 0


class VerificationCertificate(BaseModel):
    cert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"
    issued_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    subject: CertSubject
    run_id: str
    summary: CertSummary
    verdict: Literal["PASS", "WARN", "FAIL"]
    divergences_json: list[dict] = Field(default_factory=list)
    # fingerprint is computed AFTER all other fields are set
    fingerprint: str = ""
    signature: str = ""  # HMAC-SHA256(fingerprint, key) — empty when no key

    def _body_for_fingerprint(self) -> str:
        """Canonical JSON of the cert body, excluding fingerprint + signature."""
        d = self.model_dump()
        d.pop("fingerprint", None)
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, default=str)

    def compute_fingerprint(self) -> str:
        """Return the SHA-256 hex of the canonical cert body."""
        return hashlib.sha256(self._body_for_fingerprint().encode()).hexdigest()

    def seal(self, signing_key: bytes | None = None) -> "VerificationCertificate":
        """Finalise: compute fingerprint, optionally add HMAC signature."""
        self.fingerprint = self.compute_fingerprint()
        if signing_key:
            self.signature = hmac.new(
                signing_key, self.fingerprint.encode(), hashlib.sha256
            ).hexdigest()
        return self

    def verify(self, signing_key: bytes | None = None) -> bool:
        """Return True if the certificate has not been tampered with."""
        expected_fp = self.compute_fingerprint()
        if self.fingerprint != expected_fp:
            return False
        if signing_key:
            expected_sig = hmac.new(
                signing_key, self.fingerprint.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(self.signature, expected_sig):
                return False
        return True


# ── factory ────────────────────────────────────────────────────────────────────

def _severity_value(sev) -> str:
    return sev.value.upper() if hasattr(sev, "value") else str(sev).upper()


def issue_certificate(
    reports: list,
    base_url: str,
    spec: dict | None = None,
    run_id: str | None = None,
    signing_key: bytes | None = None,
) -> VerificationCertificate:
    """Create and seal a VerificationCertificate from a list of DivergenceReports."""
    summary = CertSummary(total=len(reports))
    for r in reports:
        sev = _severity_value(getattr(r, "severity", "MEDIUM"))
        if sev == "HIGH":
            summary.high += 1
        elif sev == "MEDIUM":
            summary.medium += 1
        elif sev == "LOW":
            summary.low += 1
        elif sev == "CRITICAL":
            summary.critical += 1

    if summary.high > 0 or summary.critical > 0:
        verdict: Literal["PASS", "WARN", "FAIL"] = "FAIL"
    elif summary.medium > 0:
        verdict = "WARN"
    else:
        verdict = "PASS"

    spec_hash: str | None = None
    if spec is not None:
        raw = json.dumps(spec, sort_keys=True, default=str).encode()
        spec_hash = hashlib.sha256(raw).hexdigest()[:16]

    div_list = []
    for r in reports:
        try:
            div_list.append(r.model_dump() if hasattr(r, "model_dump") else vars(r))
        except Exception:
            div_list.append({"raw": str(r)})

    cert = VerificationCertificate(
        subject=CertSubject(base_url=base_url, spec_hash=spec_hash),
        run_id=run_id or str(uuid.uuid4()),
        summary=summary,
        verdict=verdict,
        divergences_json=div_list,
    )
    return cert.seal(signing_key=signing_key)


def load_certificate(data: dict) -> VerificationCertificate:
    """Deserialise a cert from a dict (parsed JSON)."""
    return VerificationCertificate.model_validate(data)
