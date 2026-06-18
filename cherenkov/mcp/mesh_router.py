"""
Multi-Agent MCP Mesh Router (Horizon 3)
Provides dynamic MCP server registration and discovery.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from cherenkov.core.errors import get_logger

log = get_logger(__name__)


@dataclass
class MCPServerRegistration:
    """A registered external MCP server with its capabilities."""

    name: str
    url: str
    tools: list[dict[str, Any]]
    resources: list[dict[str, Any]]
    version: str = "1.0.0"
    attestation: str = ""
    registered_at: float = 0.0
    last_seen: float = 0.0
    healthy: bool = True


class MCPRegistry:
    """Registry for dynamic MCP server discovery and tool routing.

    Supports registering external MCP servers and discovering their
    capabilities at runtime. Integrates with the existing dispatch table
    by routing tool calls to the appropriate registered server.
    """

    def __init__(self):
        self._servers: dict[str, MCPServerRegistration] = {}
        self._tool_map: dict[str, str] = {}  # tool_name -> server_name

    def register_server(
        self,
        name: str,
        url: str,
        tools: list[dict[str, Any]],
        resources: list[dict[str, Any]] | None = None,
        version: str = "1.0.0",
        attestation: str = "",
    ) -> str:
        """Register an external MCP server.

        Returns the registration ID (hash of name + url).
        """
        reg_id = hashlib.sha256(f"{name}:{url}".encode()).hexdigest()[:12]
        now = time.time()
        self._servers[reg_id] = MCPServerRegistration(
            name=name,
            url=url,
            tools=tools,
            resources=resources or [],
            version=version,
            attestation=attestation,
            registered_at=now,
            last_seen=now,
            healthy=True,
        )
        # Build tool name -> server mapping
        for tool in tools:
            tool_name = tool.get("name", "")
            if tool_name:
                self._tool_map[tool_name] = reg_id
        log.info(
            "Registered MCP server", name=name, reg_id=reg_id, tools_count=len(tools)
        )
        return reg_id

    def unregister_server(self, reg_id: str) -> bool:
        """Remove a server registration."""
        if reg_id not in self._servers:
            return False
        server = self._servers[reg_id]
        # Remove tool mappings
        for tool in server.tools:
            tool_name = tool.get("name", "")
            self._tool_map.pop(tool_name, None)
        del self._servers[reg_id]
        log.info("Unregistered MCP server", reg_id=reg_id)
        return True

    def list_servers(self) -> list[dict[str, Any]]:
        """List all registered servers."""
        return [
            {
                "id": reg_id,
                "name": s.name,
                "url": s.url,
                "tools_count": len(s.tools),
                "resources_count": len(s.resources),
                "version": s.version,
                "healthy": s.healthy,
                "registered_at": s.registered_at,
                "last_seen": s.last_seen,
            }
            for reg_id, s in self._servers.items()
        ]

    def get_server(self, reg_id: str) -> MCPServerRegistration | None:
        """Get a specific server registration."""
        return self._servers.get(reg_id)

    def resolve_tool(self, tool_name: str) -> MCPServerRegistration | None:
        """Resolve which server handles a given tool name."""
        reg_id = self._tool_map.get(tool_name)
        if reg_id:
            return self._servers.get(reg_id)
        return None

    def get_combined_tools(self) -> list[dict[str, Any]]:
        """Aggregate all tool definitions from all registered servers."""
        tools = []
        for server in self._servers.values():
            tools.extend(server.tools)
        return tools

    def get_combined_resources(self) -> list[dict[str, Any]]:
        """Aggregate all resource definitions from all registered servers."""
        resources = []
        for server in self._servers.values():
            resources.extend(server.resources)
        return resources

    def health_check(self, reg_id: str) -> bool:
        """Mark a server as healthy or unhealthy."""
        if reg_id not in self._servers:
            return False
        self._servers[reg_id].last_seen = time.time()
        self._servers[reg_id].healthy = True
        return True

    def prune_stale(self, max_age_seconds: int = 300) -> int:
        """Remove servers that haven't been seen recently."""
        now = time.time()
        stale = [
            reg_id
            for reg_id, s in self._servers.items()
            if now - s.last_seen > max_age_seconds
        ]
        for reg_id in stale:
            self.unregister_server(reg_id)
        return len(stale)


# Global singleton
_registry = MCPRegistry()


def get_registry() -> MCPRegistry:
    return _registry
