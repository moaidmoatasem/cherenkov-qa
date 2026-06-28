"""MCP Authentication and Authorization (CC-3)."""
from __future__ import annotations

import time
from typing import Any

import jwt

# Secret key for signing JWTs. In production this should be in an env var.
JWT_SECRET = "cherenkov-mcp-jwt-secret-key-change-me"
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
