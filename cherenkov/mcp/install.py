"""MCP server installation helpers for Claude Desktop, Cursor, and Windsurf."""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path


def _resolve_python() -> str:
    return os.path.abspath(sys.executable)


def install_marketplace_tool(tool_id: str) -> bool:
    """Install a tool from the MCP Marketplace."""
    import subprocess

    from cherenkov.mcp.marketplace.registry import MarketplaceRegistry
    from cherenkov.mcp.marketplace.sandbox import SandboxValidator

    registry = MarketplaceRegistry()
    tool = registry.get_tool_info(tool_id)
    if not tool:
        print(f"Tool {tool_id} not found in marketplace.")
        return False

    validator = SandboxValidator()
    # Mocking manifest validation since we don't fetch full raw manifests yet
    manifest = {"id": tool.id, "name": tool.name, "install_command": tool.install_command}
    if not validator.validate_tool_manifest(manifest):
        print(f"Tool {tool_id} failed sandbox validation.")
        return False

    print(f"Installing {tool.name}...")
    if validator.run_in_sandbox(tool.install_command):
        try:
            import shlex
            cmd_tokens = shlex.split(tool.install_command)
            subprocess.run(cmd_tokens, check=True)
            print(f"Successfully installed {tool.name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Installation failed: {e}")
            return False
    return False



class MCPConfigGenerator:
    """Generates configuration snippets for MCP-compatible AI assistants."""

    def __init__(self, python_path: str | None = None):
        self.python_path = python_path or _resolve_python()
        self.module_args = ["-m", "cherenkov.mcp.server"]

    def _base_config_entry(self) -> dict:
        return {
            "command": self.python_path,
            "args": self.module_args,
        }

    def claude_desktop_config(self) -> dict:
        return {"mcpServers": {"cherenkov": self._base_config_entry()}}

    def cursor_mcp_config(self) -> dict:
        return {"mcpServers": {"cherenkov": self._base_config_entry()}}

    def windsurf_mcp_config(self) -> dict:
        return {"mcpServers": {"cherenkov": self._base_config_entry()}}

    def all_configs(self) -> dict[str, dict]:
        return {
            "claude_desktop": self.claude_desktop_config(),
            "cursor": self.cursor_mcp_config(),
            "windsurf": self.windsurf_mcp_config(),
        }

    def print_configs(self) -> None:
        for name, config in self.all_configs().items():
            print(f"\n{'='*60}")
            print(f"  {name.upper()} MCP Configuration")
            print(f"{'='*60}")
            print(json.dumps(config, indent=2))

    def claude_config_path(self) -> Path | None:
        system = platform.system()
        if system == "Darwin":
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        if system == "Windows":
            return Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
        if system == "Linux":
            return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        return None

    def cursor_config_path(self) -> Path:
        return Path.cwd() / ".cursor" / "mcp.json"

    def windsurf_config_path(self) -> Path:
        return Path.cwd() / ".windsurf" / "mcp_config.json"

    def write_claude_config(self, backup: bool = True) -> Path | None:
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
    """Run the MCP install/setup process."""
    if python_path is None:
        python_path = sys.executable
    gen = MCPConfigGenerator(python_path=python_path)
    if platform_target == "all":
        gen.print_configs()
    elif platform_target == "claude":
        path = gen.write_claude_config()
        if path:
            print(f"Written to {path}")
        else:
            print("Unsupported platform for Claude Desktop")
    elif platform_target == "cursor":
        path = gen.write_cursor_config()
        print(f"Written to {path}")
    elif platform_target == "windsurf":
        config = gen.windsurf_mcp_config()
        print(json.dumps(config, indent=2))
        print(f"\nPlace this in: {gen.windsurf_config_path()}")
    else:
        print(f"Unknown platform: {platform_target}, supported: claude, cursor, windsurf, all")
