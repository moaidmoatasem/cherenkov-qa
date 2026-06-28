"""Unit tests for MCP Authentication (CC-3)."""

import pytest
import time
import jwt

from cherenkov.mcp.auth import (
    generate_mcp_token,
    verify_mcp_token,
    MCPAuthMiddleware,
    JWT_SECRET,
    JWT_ALGORITHM
)


def test_generate_and_verify_token():
    token = generate_mcp_token("test-client")
    payload = verify_mcp_token(token)
    
    assert payload is not None
    assert payload["sub"] == "test-client"
    assert "exp" in payload


def test_verify_expired_token():
    # Create an expired token manually
    now = int(time.time())
    payload = {
        "sub": "test",
        "iat": now - 7200,
        "exp": now - 3600,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    assert verify_mcp_token(token) is None


def test_verify_invalid_token():
    assert verify_mcp_token("invalid.token.here") is None


def test_auth_middleware_disabled():
    middleware = MCPAuthMiddleware(require_auth=False)
    assert middleware.authenticate(None, None) is True
    assert middleware.authenticate("invalid", "invalid") is True


def test_auth_middleware_api_key():
    middleware = MCPAuthMiddleware(require_auth=True, valid_api_keys={"secret-key"})
    assert middleware.authenticate(None, "secret-key") is True
    assert middleware.authenticate(None, "wrong-key") is False


def test_auth_middleware_jwt():
    middleware = MCPAuthMiddleware(require_auth=True)
    token = generate_mcp_token("client-1")
    
    assert middleware.authenticate(token) is True
    assert middleware.authenticate("invalid.token") is False
