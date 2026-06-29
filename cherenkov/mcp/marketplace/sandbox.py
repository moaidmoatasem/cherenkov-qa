"""MCP Sandbox Validator (CC-3)."""
from __future__ import annotations

import logging
import re
from typing import Any

_log = logging.getLogger(__name__)

# Only allow: pip install <package-name>
# Package names: letters, digits, hyphens, underscores, dots, and version specifiers.
_ALLOWED_INSTALL_RE = re.compile(
    r"^pip install [a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?(\[[\w,]+\])?(==[\w.*]+)?$"
)


class SandboxValidator:
    """Validates 3rd-party MCP tools before and during installation."""

    def __init__(self):
        self.max_install_time_seconds = 120

    def validate_tool_manifest(self, manifest: dict[str, Any]) -> bool:
        """Validate a tool manifest to ensure it is safe to install."""
        required_keys = {"id", "name", "install_command"}
        if not required_keys.issubset(manifest.keys()):
            _log.warning("Manifest missing required keys: %s", required_keys - manifest.keys())
            return False

        cmd = manifest.get("install_command", "")
        if not _ALLOWED_INSTALL_RE.match(cmd):
            _log.warning("install_command rejected for %s: %r", manifest.get("id"), cmd)
            return False

        return True

    def run_in_sandbox(self, command: str) -> bool:
        """Execute a command in an isolated environment (simulation)."""
        _log.info("Running in sandbox: %s", command)
        # In a real implementation, this would use Docker, gVisor, or a restricted subprocess.
        return True
