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
from cherenkov.mcp.client import MCPClient

log = get_logger(__name__)

@dataclass
class MCPServerRegistration:
    """A registered external MCP server with its capabilities.

    Attributes:
        name (str): Server name.
        url (str): Target base URL of the remote MCP server.
        tools (list[dict[str, Any]]): List of tool definition dictionaries.
        resources (list[dict[str, Any]]): List of resource definition dictionaries.
        version (str): Server version string. Defaults to "1.0.0".
        attestation (str): Cryptographic or identity attestation string. Defaults to "".
        registered_at (float): Unix timestamp when registered. Defaults to 0.0.
        last_seen (float): Unix timestamp when last seen active. Defaults to 0.0.
        healthy (bool): Health status flag. Defaults to True.
    """

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

    Attributes:
        _servers (dict[str, MCPServerRegistration]): Registration ID mapping to server object.
        _tool_map (dict[str, str]): Tool name mapping to registration ID.
    """

    def __init__(self) -> None:
        """Initialize MCPRegistry.

        Returns:
            None
        """
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

        Args:
            name (str): Name of the MCP server.
            url (str): Base URL of the MCP server.
            tools (list[dict[str, Any]]): List of tool definition dictionaries.
            resources (list[dict[str, Any]] | None): Optional list of resource definitions. Defaults to None.
            version (str): Server version string. Defaults to "1.0.0".
            attestation (str): Optional attestation string. Defaults to "".

        Returns:
            str: Registration ID hash generated from name and url.
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
        log.info("Registered MCP server", name=name, reg_id=reg_id, tools_count=len(tools))
        return reg_id

    def unregister_server(self, reg_id: str) -> bool:
        """Remove a server registration.

        Args:
            reg_id (str): Registration ID of the server to remove.

        Returns:
            bool: True if server was found and unregistered; False otherwise.
        """
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
        """List all registered servers.

        Returns:
            list[dict[str, Any]]: List of dictionary representations for registered servers.
        """
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
        """Get a specific server registration by ID.

        Args:
            reg_id (str): Registration ID of the server.

        Returns:
            MCPServerRegistration | None: Matching registration if found, else None.
        """
        return self._servers.get(reg_id)

    def resolve_tool(self, tool_name: str) -> MCPServerRegistration | None:
        """Resolve which server handles a given tool name.

        Args:
            tool_name (str): Name of the tool to resolve.

        Returns:
            MCPServerRegistration | None: Responsible MCPServerRegistration if registered, else None.
        """
        reg_id = self._tool_map.get(tool_name)
        if reg_id:
            return self._servers.get(reg_id)
        return None

    def get_combined_tools(self) -> list[dict[str, Any]]:
        """Aggregate all tool definitions from all registered servers.

        Returns:
            list[dict[str, Any]]: Combined list of all registered tool definitions.
        """
        tools = []
        for server in self._servers.values():
            tools.extend(server.tools)
        return tools

    def get_combined_resources(self) -> list[dict[str, Any]]:
        """Aggregate all resource definitions from all registered servers.

        Returns:
            list[dict[str, Any]]: Combined list of all registered resource definitions.
        """
        resources = []
        for server in self._servers.values():
            resources.extend(server.resources)
        return resources

    def health_check(self, reg_id: str) -> bool:
        """Mark a server as healthy and update its last_seen timestamp.

        Args:
            reg_id (str): Registration ID of server.

        Returns:
            bool: True if server was found and updated; False otherwise.
        """
        if reg_id not in self._servers:
            return False
        self._servers[reg_id].last_seen = time.time()
        self._servers[reg_id].healthy = True
        return True

    def prune_stale(self, max_age_seconds: int = 300) -> int:
        """Remove servers that haven't been seen recently.

        Args:
            max_age_seconds (int): Threshold age in seconds. Defaults to 300.

        Returns:
            int: Number of stale servers pruned.
        """
        now = time.time()
        stale = [
            reg_id
            for reg_id, s in self._servers.items()
            if now - s.last_seen > max_age_seconds
        ]
        for reg_id in stale:
            self.unregister_server(reg_id)
        return len(stale)

    def forward_tool_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Forward a tool call to the registered server that owns it.

        Args:
            tool_name (str): Name of tool to forward.
            arguments (dict[str, Any]): Arguments dictionary for tool call.

        Returns:
            dict[str, Any] | None: Result dictionary from remote server, or None if tool not registered.

        Raises:
            MCPClientError: On transport or protocol failure.
        """
        server = self.resolve_tool(tool_name)
        if server is None:
            return None
        client = MCPClient(server.url)
        result = client.call_tool(tool_name, arguments)
        # Mark server as healthy after a successful call
        self.health_check(
            next(
                (rid for rid, s in self._servers.items() if s is server),
                "",
            )
        )
        return result

# Global singleton
_registry = MCPRegistry()

def get_registry() -> MCPRegistry:
    """Return global MCPRegistry singleton instance.

    Returns:
        MCPRegistry: Global mesh registry object.
    """
    return _registry

