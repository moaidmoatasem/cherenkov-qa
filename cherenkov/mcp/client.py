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

    Attributes:
        _base_url (str): Base HTTP URL of the remote MCP server.
        _timeout (float): Request timeout limit in seconds.
    """

    def __init__(self, base_url: str, timeout: float = _TIMEOUT) -> None:
        """Initialize MCPClient with target server URL and timeout.

        Args:
            base_url (str): Target MCP server HTTP/HTTPS URL.
            timeout (float): Request timeout in seconds. Defaults to 30.0.

        Returns:
            None

        Raises:
            MCPClientError: If base_url does not start with http:// or https://.
        """
        if not base_url.startswith(("http://", "https://")):
            raise MCPClientError(f"MCPClient only supports http/https URLs; got: {base_url!r}")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # ── JSON-RPC helpers ───────────────────────────────────────────────────────

    def _rpc(self, method: str, params: dict[str, Any]) -> Any:
        """Send a JSON-RPC 2.0 request and return the result field.

        Args:
            method (str): JSON-RPC method name to invoke.
            params (dict[str, Any]): Dictionary of method parameters.

        Returns:
            Any: The 'result' payload from the JSON-RPC response object.

        Raises:
            MCPClientError: On transport timeout, HTTP status error, JSON decode failure, or RPC error.
        """
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
        """Call a tool on the remote server and return its result dict.

        Args:
            tool_name (str): Name of the remote tool to execute.
            arguments (dict[str, Any]): Dictionary of arguments for the tool call.

        Returns:
            dict[str, Any]: Result dictionary returned by the tool execution.

        Raises:
            MCPClientError: If the remote RPC call fails.
        """
        result = self._rpc("tools/call", {"name": tool_name, "arguments": arguments})
        if result is None:
            return {"content": [], "isError": False}
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        """Fetch the tool catalogue from the remote server.

        Returns:
            list[dict[str, Any]]: List of tool definition dictionaries.

        Raises:
            MCPClientError: If the remote RPC call fails.
        """
        result = self._rpc("tools/list", {}) or {}
        return result.get("tools", [])

    def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource from the remote server by URI.

        Args:
            uri (str): Resource URI string to fetch.

        Returns:
            dict[str, Any]: Dictionary containing resource contents or metadata.

        Raises:
            MCPClientError: If the remote RPC call fails.
        """
        return self._rpc("resources/read", {"uri": uri}) or {}

