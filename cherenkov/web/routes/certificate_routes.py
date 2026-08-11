"""API route handler for verifying CHERENKOV cryptographic certificates."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from cherenkov.core.certificate import load_certificate

router = APIRouter(tags=["certificates"])


class CertificateVerifyPayload(BaseModel):
    """Payload model for verifying a CHERENKOV certificate."""
    certificate: dict
    signing_key: str | None = None


@router.post("/api/v1/certificates/verify")
async def verify_certificate(payload: CertificateVerifyPayload):
    """Verify cryptographic signature and integrity of a CHERENKOV certificate.

    Args:
        payload: CertificateVerifyPayload object containing certificate dictionary and optional key.

    Returns:
        Dictionary payload listing validity status, cert fingerprint, and summary details.

    Raises:
        HTTPException: 400 if signing_key is invalid hex, or 422 if certificate schema is invalid.
    """
    try:
        cert = load_certificate(payload.certificate)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail=f"Not a valid CHERENKOV certificate: {exc}"
        ) from None

    key_bytes: bytes | None = None
    if payload.signing_key:
        try:
            key_bytes = bytes.fromhex(payload.signing_key)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="signing_key must be a hex string"
            ) from None

    valid = cert.verify(signing_key=key_bytes)

    return {
        "valid": valid,
        "cert_id": cert.cert_id,
        "issued_at": cert.issued_at,
        "verdict": cert.verdict,
        "subject": cert.subject.model_dump(),
        "summary": cert.summary.model_dump(),
        "fingerprint": cert.fingerprint,
        "signature_present": bool(cert.signature),
    }
