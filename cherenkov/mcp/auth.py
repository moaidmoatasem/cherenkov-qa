"""MCP Authentication and Authorization (CC-3)."""
from __future__ import annotations

import os
import time
from typing import Any

import jwt

_DEFAULT_JWT_SECRET = "cherenkov-mcp-jwt-secret-change-me"
JWT_SECRET = os.environ.get("CHERENKOV_JWT_SECRET", _DEFAULT_JWT_SECRET)
JWT_ALGORITHM = "HS256"


def generate_mcp_token(client_id: str, expiration_seconds: int = 3600) -> str:
    """Generate a JWT token for an MCP client."""
    now = int(time.time())
    payload = {
        "sub": client_id,
        "iat": now,
        "exp": now + expiration_seconds,
        "iss": "cherenkov-mcp",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_mcp_token(token: str) -> dict[str, Any] | None:
    """Verify a JWT token. Returns the payload if valid, None otherwise."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


class MCPAuthMiddleware:
    """Middleware to validate API keys or JWT tokens on MCP requests."""

    def __init__(self, require_auth: bool = False, valid_api_keys: set[str] | None = None):
        self.require_auth = require_auth
        self.valid_api_keys = valid_api_keys or set()
        if require_auth and JWT_SECRET == _DEFAULT_JWT_SECRET:
            import warnings
            warnings.warn(
                "CHERENKOV_JWT_SECRET is not set; MCP auth is enabled with an insecure default secret. "
                "Set CHERENKOV_JWT_SECRET before exposing this service.",
                stacklevel=2,
            )

    def authenticate(self, token: str | None, api_key: str | None = None) -> bool:
        """Authenticate a request using either an API key or a JWT."""
        if not self.require_auth:
            return True

        if api_key and api_key in self.valid_api_keys:
            return True

        if token:
            payload = verify_mcp_token(token)
            if payload and payload.get("sub"):
                return True

        return False
