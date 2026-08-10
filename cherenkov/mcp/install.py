"""MCP server installation helpers for Claude Desktop, Cursor, and Windsurf."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _resolve_python() -> str:
    """Resolve and return absolute path of the current Python executable.

    Returns:
        str: Absolute path string of sys.executable.
    """
    return os.path.abspath(sys.executable)


def install_marketplace_tool(tool_id: str) -> bool:
    """Install a tool from the MCP Marketplace.

    Args:
        tool_id (str): Unique tool identifier string in marketplace registry.

    Returns:
        bool: True if installation succeeded; False otherwise.
    """
    from cherenkov.mcp.marketplace.registry import MarketplaceRegistry
    from cherenkov.mcp.marketplace.sandbox import SandboxValidator

    registry = MarketplaceRegistry()
    tool = registry.get_tool_info(tool_id)
    if not tool:
        return False

    validator = SandboxValidator()
    # Mocking manifest validation since we don't fetch full raw manifests yet
    manifest = {"id": tool.id, "name": tool.name, "install_command": tool.install_command}
    if not validator.validate_tool_manifest(manifest):
        return False

    if validator.run_in_sandbox(tool.install_command):
        try:
            import shlex
            cmd_tokens = shlex.split(tool.install_command)
            subprocess.run(cmd_tokens, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    return False


class MCPConfigGenerator:
    """Generates configuration snippets for MCP-compatible AI assistants.

    Attributes:
        python_path (str): Absolute path to python executable.
        module_args (list[str]): Module invocation arguments for MCP server.
    """

    def __init__(self, python_path: str | None = None) -> None:
        """Initialize MCPConfigGenerator.

        Args:
            python_path (str | None): Optional explicit path to Python executable. Defaults to None.

        Returns:
            None
        """
        self.python_path = python_path or _resolve_python()
        self.module_args = ["-m", "cherenkov.mcp.server"]

    def _base_config_entry(self) -> dict:
        """Generate base MCP server configuration dict.

        Returns:
            dict: Configuration dictionary specifying command and args.
        """
        return {
            "command": self.python_path,
            "args": self.module_args,
        }

    def claude_desktop_config(self) -> dict:
        """Generate configuration dictionary for Claude Desktop.

        Returns:
            dict: Claude Desktop mcpServers configuration structure.
        """
        return {"mcpServers": {"cherenkov": self._base_config_entry()}}

    def cursor_mcp_config(self) -> dict:
        """Generate configuration dictionary for Cursor IDE.

        Returns:
            dict: Cursor mcpServers configuration structure.
        """
        return {"mcpServers": {"cherenkov": self._base_config_entry()}}

    def windsurf_mcp_config(self) -> dict:
        """Generate configuration dictionary for Windsurf IDE.

        Returns:
            dict: Windsurf mcpServers configuration structure.
        """
        return {"mcpServers": {"cherenkov": self._base_config_entry()}}

    def all_configs(self) -> dict[str, dict]:
        """Return combined configurations for all supported target applications.

        Returns:
            dict[str, dict]: Dictionary mapping application name to configuration dict.
        """
        return {
            "claude_desktop": self.claude_desktop_config(),
            "cursor": self.cursor_mcp_config(),
            "windsurf": self.windsurf_mcp_config(),
        }

    def print_configs(self) -> None:
        """Print or iterate over all generated configuration snippets.

        Returns:
            None
        """
        for _name, _config in self.all_configs().items():
            pass

    def claude_config_path(self) -> Path | None:
        """Locate Claude Desktop configuration file path for the host OS.

        Returns:
            Path | None: Path to config file if platform is supported, else None.
        """
        system = platform.system()
        if system == "Darwin":
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        if system == "Windows":
            return Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
        if system == "Linux":
            return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        return None

    def cursor_config_path(self) -> Path:
        """Return path to project-local Cursor MCP config file.

        Returns:
            Path: Path to .cursor/mcp.json.
        """
        return Path.cwd() / ".cursor" / "mcp.json"

    def windsurf_config_path(self) -> Path:
        """Return path to project-local Windsurf MCP config file.

        Returns:
            Path: Path to .windsurf/mcp_config.json.
        """
        return Path.cwd() / ".windsurf" / "mcp_config.json"

    def write_claude_config(self, backup: bool = True) -> Path | None:
        """Write or update Claude Desktop configuration file.

        Args:
            backup (bool): Whether to create a backup file if config exists. Defaults to True.

        Returns:
            Path | None: Path to written configuration file, or None if platform unsupported.
        """
        config_path = self.claude_config_path()
        if config_path is None:
            return None
        config_path.parent.mkdir(parents=True, exist_ok=True)
        existing = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                existing = json.load(f)
            if backup:
                shutil.copy2(config_path, config_path.with_suffix(".json.bak"))
        existing.setdefault("mcpServers", {}).update(
            self.claude_desktop_config()["mcpServers"]
        )
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        return config_path

    def write_cursor_config(self) -> Path:
        """Write or update project-local Cursor configuration file.

        Returns:
            Path: Path to written .cursor/mcp.json file.
        """
        config_path = self.cursor_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        existing = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                existing = json.load(f)
        existing.setdefault("mcpServers", {}).update(
            self.cursor_mcp_config()["mcpServers"]
        )
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        return config_path


def run_mcp_install(platform_target: str = "all", python_path: str | None = None) -> None:
    """Run the MCP install/setup process for the specified platform target.

    Args:
        platform_target (str): Target platform ('all', 'claude', 'cursor', 'windsurf'). Defaults to 'all'.
        python_path (str | None): Optional path to python binary. Defaults to sys.executable.

    Returns:
        None
    """
    if python_path is None:
        python_path = sys.executable
    gen = MCPConfigGenerator(python_path=python_path)
    if platform_target == "all":
        gen.print_configs()
    elif platform_target == "claude":
        path = gen.write_claude_config()
        if path:
            pass
        else:
            pass
    elif platform_target == "cursor":
        path = gen.write_cursor_config()
    elif platform_target == "windsurf":
        gen.windsurf_mcp_config()
    else:
        pass

