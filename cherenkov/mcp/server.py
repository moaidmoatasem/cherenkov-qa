"""
cherenkov/mcp/server.py
MCP server — initialize handshake, capability advertisement, dispatch wiring.

Implements the Model Context Protocol (MCP) lifecycle:
  1. Client sends `initialize` → server responds with protocolVersion + capabilities
  2. Client sends `initialized` notification → server is ready
  3. Client calls resources/list, resources/read, tools/list, tools/call
  4. Server processes until stdin closes

Transport: JSON-RPC 2.0 over stdio (protocol.py).
No third-party deps (no mcp SDK).

Usage
-----
  # From CLI:
  python -m cherenkov mcp serve

  # Claude Desktop config (mcpServers entry):
  {
    "cherenkov": {
      "command": "python3",
      "args": ["/path/to/cherenkov.py", "mcp", "serve"],
      "cwd": "/path/to/your/project"
    }
  }
"""
from __future__ import annotations

import sys
from typing import Any

from cherenkov.core.errors import get_logger
from cherenkov.mcp.contracts import (
    MCPCapabilities,
    MCPInitializeResult,
    MCPServerInfo,
)
from cherenkov.mcp.handlers import (
    handle_resource_read,
    handle_resources_list,
    handle_tool_call,
    handle_tools_list,
)
from cherenkov.mcp.protocol import DispatchTable, serve_stdio

log = get_logger(__name__)


def _handle_initialize(params: dict[str, Any]) -> dict[str, Any]:
    """MCP initialize handshake — advertise capabilities."""
    result = MCPInitializeResult(
        protocolVersion="2024-11-05",
        serverInfo=MCPServerInfo(name="cherenkov", version="1.0.0"),
        capabilities=MCPCapabilities(
            resources={"subscribe": False, "listChanged": False},
            tools={"listChanged": False},
            prompts={"listChanged": False},
        ),
    )
    return result.model_dump()


def _handle_initialized(params: dict[str, Any]) -> None:
    """MCP initialized notification — no reply required (notification handler)."""
    log.debug("MCP client initialized")
    return None


def _handle_ping(params: dict[str, Any]) -> dict[str, Any]:
    return {}


def build_dispatch_table() -> DispatchTable:
    """Build the full JSON-RPC method → handler mapping."""
    return {
        # ── MCP lifecycle ──────────────────────────────────────────────────
        "initialize":           _handle_initialize,
        "notifications/initialized": _handle_initialized,
        "ping":                 _handle_ping,

        # ── Resources ─────────────────────────────────────────────────────
        "resources/list":       handle_resources_list,
        "resources/read":       handle_resource_read,

        # ── Tools ──────────────────────────────────────────────────────────
        "tools/list":           handle_tools_list,
        "tools/call":           handle_tool_call,
    }


def run_mcp_server(
    *,
    input_stream=None,
    output_stream=None,
) -> None:
    """
    Start the MCP stdio server.

    input_stream / output_stream can be injected for testing without
    touching sys.stdin / sys.stdout.
    """
    log.info("CHERENKOV MCP server starting (mcp/v1, stdio transport)")
    table = build_dispatch_table()
    serve_stdio(table, input_stream=input_stream, output_stream=output_stream)
    log.info("CHERENKOV MCP server stopped (stdin closed)")
