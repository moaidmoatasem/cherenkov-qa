"""
cherenkov/mcp/client.py — lightweight MCP JSON-RPC 2.0 HTTP client (E2.2).

CHERENKOV can consume external MCP servers registered via mcp_registry_publish.
This client forwards tool calls and resource reads to registered servers over HTTP.

Only http/https transports are supported (stdio servers use the registry via
process spawn — out of scope for this increment). Calls time out at 30 s.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from cherenkov.core.errors import get_logger

log = get_logger(__name__)

_TIMEOUT = 30.0


class MCPClientError(Exception):
    """Raised when a remote MCP call fails at the transport or protocol level."""


class MCPClient:
    """Minimal MCP JSON-RPC 2.0 client for HTTP-transport servers.

    Instantiate per-call or cache a single instance per server URL.
    All methods are synchronous (blocking httpx calls).
    """

    def __init__(self, base_url: str, timeout: float = _TIMEOUT) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise MCPClientError(f"MCPClient only supports http/https URLs; got: {base_url!r}")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # ── JSON-RPC helpers ───────────────────────────────────────────────────────

    def _rpc(self, method: str, params: dict[str, Any]) -> Any:
        """Send a JSON-RPC 2.0 request and return the result field."""
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }
        try:
            resp = httpx.post(
                self._base_url,
                json=payload,
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MCPClientError(f"Timeout calling {self._base_url}: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise MCPClientError(
                f"HTTP {exc.response.status_code} from {self._base_url}"
            ) from exc
        except httpx.RequestError as exc:
            raise MCPClientError(f"Transport error calling {self._base_url}: {exc}") from exc

        try:
            body = resp.json()
        except json.JSONDecodeError as exc:
            raise MCPClientError(f"Non-JSON response from {self._base_url}") from exc

        if "error" in body:
            err = body["error"]
            raise MCPClientError(
                f"RPC error {err.get('code')} from {self._base_url}: {err.get('message')}"
            )
        return body.get("result")

    # ── Public API ─────────────────────────────────────────────────────────────

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the remote server and return its result dict."""
        result = self._rpc("tools/call", {"name": tool_name, "arguments": arguments})
        if result is None:
            return {"content": [], "isError": False}
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        """Fetch the tool catalogue from the remote server."""
        result = self._rpc("tools/list", {}) or {}
        return result.get("tools", [])

    def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource from the remote server by URI."""
        result = self._rpc("resources/read", {"uri": uri}) or {}
        return result
