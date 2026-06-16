"""
CHERENKOV mcp/policy.py — Policy enforcement for MCP tool access.

Reads cherenkov-policy.json and validates tool calls against allowlists.
D7 invariant: policy gates are suggest-only; they block execution, not auto-edit.
Anti-lock-in: policy can be disabled by removing the policy file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class PolicyEngine:
    def __init__(self, policy_path: str | None = None):
        self.policy_path = policy_path or os.getenv(
            "CHERENKOV_POLICY_FILE", "cherenkov-policy.json"
        )
        self.policy = self._load()

    def _load(self) -> dict[str, Any]:
        path = Path(self.policy_path)
        if not path.exists():
            return {"version": "0.0", "profiles": {}, "invariants": {}}
        return json.loads(path.read_text())

    def reload(self) -> None:
        self.policy = self._load()

    def is_tool_allowed(self, profile: str, server: str, tool: str) -> bool:
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
        profile_cfg = self.policy.get("profiles", {}).get(profile, {})
        server_cfg = profile_cfg.get("servers", {}).get(server, {})
        allowed = server_cfg.get("allow_network", ["*"])
        if "*" in allowed:
            return True
        return host in allowed

    def list_policy(self) -> dict[str, Any]:
        return dict(self.policy)
