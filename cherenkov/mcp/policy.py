"""
CHERENKOV mcp/policy.py — Policy enforcement for MCP tool access.

Reads cherenkov-policy.json and validates tool calls against allowlists.
D7 invariant: policy gates are suggest-only; they block execution, not auto-edit.
Anti-lock-in: policy can be disabled by removing the policy file.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any


class PolicyEngine:
    """Thread-safe policy enforcement engine for MCP tool call security.

    Attributes:
        policy_path (str): Path to policy configuration JSON file.
        policy (dict[str, Any]): Loaded policy configuration dictionary.
    """

    def __init__(self, policy_path: str | None = None) -> None:
        """Initialize PolicyEngine and load policy rules.

        Args:
            policy_path (str | None): Optional explicit path to policy JSON file. Defaults to None.

        Returns:
            None
        """
        self._lock = threading.RLock()
        self.policy_path = policy_path or os.getenv(
            "CHERENKOV_POLICY_FILE", "cherenkov-policy.json"
        )
        self.policy = self._load()

    def _load(self) -> dict[str, Any]:
        """Load policy configuration from disk or return empty policy dict if absent.

        Returns:
            dict[str, Any]: Parsed JSON policy dictionary.
        """
        path = Path(self.policy_path)
        if not path.exists():
            return {"version": "0.0", "profiles": {}, "invariants": {}}
        return json.loads(path.read_text())

    def reload(self) -> None:
        """Reload policy configuration from disk under lock.

        Returns:
            None
        """
        with self._lock:
            self.policy = self._load()

    def is_tool_allowed(self, profile: str, server: str, tool: str) -> bool:
        """Check if a tool is permitted for execution under a specified profile and server.

        Args:
            profile (str): Profile key (e.g. 'full-dev').
            server (str): Server key (e.g. 'cherenkov').
            tool (str): Tool name (e.g. 'hitl_approve').

        Returns:
            bool: True if tool execution is allowed by policy; False otherwise.
        """
        with self._lock:
            profile_cfg = self.policy.get("profiles", {}).get(profile, {})
        server_cfg = profile_cfg.get("servers", {}).get(server, {})
        allowed = server_cfg.get("tools", ["*"])
        blocked = server_cfg.get("blocked_tools", [])
        if tool in blocked:
            return False
        if "*" in allowed:
            return True
        return tool in allowed

    def is_network_allowed(self, profile: str, server: str, host: str) -> bool:
        """Check if outbound network access to a target host is permitted.

        Args:
            profile (str): Profile key.
            server (str): Server key.
            host (str): Network host string to check.

        Returns:
            bool: True if network access is allowed; False otherwise.
        """
        with self._lock:
            profile_cfg = self.policy.get("profiles", {}).get(profile, {})
        server_cfg = profile_cfg.get("servers", {}).get(server, {})
        allowed = server_cfg.get("allow_network", ["*"])
        if "*" in allowed:
            return True
        return host in allowed

    def list_policy(self) -> dict[str, Any]:
        """Return a copy of the current policy configuration dict.

        Returns:
            dict[str, Any]: Policy rules dictionary.
        """
        with self._lock:
            return dict(self.policy)

