from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from cherenkov.core.certificate import load_certificate

router = APIRouter(tags=["certificates"])


class CertificateVerifyPayload(BaseModel):
    certificate: dict


@router.post("/api/v1/certificates/verify")
async def verify_certificate(payload: CertificateVerifyPayload):
    """Verify a Cherenkov VerificationCertificate's fingerprint (and signature, if present).

    Accepts the raw certificate JSON (as produced by `cherenkov certify`) and
    re-derives its SHA-256 fingerprint to detect tampering, matching the same
    `VerificationCertificate.verify()` logic the CLI uses.
    """
    try:
        cert = load_certificate(payload.certificate)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Malformed certificate: {exc}") from None

    return {
        "valid": cert.verify(),
        "cert_id": cert.cert_id,
        "version": cert.version,
        "run_id": cert.run_id,
        "issued_at": cert.issued_at,
        "verdict": cert.verdict,
        "subject": cert.subject.model_dump(),
        "summary": cert.summary.model_dump(),
        "fingerprint": cert.fingerprint,
        "signed": bool(cert.signature),
    }
