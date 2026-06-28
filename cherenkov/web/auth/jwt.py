"""Minimal HS256 JWT — stdlib only (base64 + hmac + hashlib). No python-jose."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import warnings

_SECRET_KEY: str | None = None


def _secret() -> str:
    global _SECRET_KEY
    if _SECRET_KEY:
        return _SECRET_KEY
    from cherenkov.core.settings import get_settings
    key = get_settings().JWT_SECRET
    if not key:
        key = secrets.token_hex(32)
        warnings.warn(
            "CHERENKOV_JWT_SECRET is not set — using a random key. "
            "Tokens will be invalidated on every restart. Set CHERENKOV_JWT_SECRET in your environment.",
            RuntimeWarning,
            stacklevel=2,
        )
    _SECRET_KEY = key
    return key


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def encode(payload: dict, expire_hours: int = 8) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = {**payload, "iat": int(time.time()), "exp": int(time.time()) + expire_hours * 3600}
    body = _b64url(json.dumps(payload).encode())
    signing_input = f"{header}.{body}"
    sig = _b64url(hmac.new(_secret().encode(), signing_input.encode(), hashlib.sha256).digest())
    return f"{signing_input}.{sig}"


def decode(token: str) -> dict:
    """Decode and verify. Raises ValueError on any failure."""
    try:
        header, body, sig = token.split(".")
    except ValueError:
        raise ValueError("Malformed token")
    signing_input = f"{header}.{body}"
    expected_sig = _b64url(hmac.new(_secret().encode(), signing_input.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("Invalid signature")
    payload = json.loads(_b64url_decode(body))
    if payload.get("exp", 0) < int(time.time()):
        raise ValueError("Token expired")
    return payload
