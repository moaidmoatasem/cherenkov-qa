"""Unit tests for MCP install config generator."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cherenkov.mcp.install import MCPConfigGenerator


class TestMCPConfigGenerator(unittest.TestCase):
    """Tests for MCPConfigGenerator."""

    def setUp(self):
        self.gen = MCPConfigGenerator(python_path="/usr/bin/python3")

    def test_claude_desktop_config_structure(self):
        config = self.gen.claude_desktop_config()
        self.assertIn("mcpServers", config)
        self.assertIn("cherenkov", config["mcpServers"])
        entry = config["mcpServers"]["cherenkov"]
        self.assertEqual(entry["command"], "/usr/bin/python3")
        self.assertIn("-m", entry["args"])
        self.assertIn("cherenkov.mcp.server", entry["args"])

    def test_cursor_mcp_config_structure(self):
        config = self.gen.cursor_mcp_config()
        self.assertIn("mcpServers", config)
        self.assertIn("cherenkov", config["mcpServers"])
        entry = config["mcpServers"]["cherenkov"]
        self.assertEqual(entry["command"], "/usr/bin/python3")

    def test_windsurf_mcp_config_structure(self):
        config = self.gen.windsurf_mcp_config()
        self.assertIn("mcpServers", config)
        self.assertIn("cherenkov", config["mcpServers"])
        entry = config["mcpServers"]["cherenkov"]
        self.assertEqual(entry["command"], "/usr/bin/python3")

    def test_all_configs_returns_three_platforms(self):
        configs = self.gen.all_configs()
        self.assertIn("claude_desktop", configs)
        self.assertIn("cursor", configs)
        self.assertIn("windsurf", configs)

    def test_configs_serialize_to_json(self):
        configs = self.gen.all_configs()
        for name, config in configs.items():
            dumped = json.dumps(config)
            restored = json.loads(dumped)
            self.assertEqual(restored, config)

    def test_write_claude_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "claude_desktop_config.json"
            with patch.object(self.gen, "claude_config_path", return_value=config_path):
                result = self.gen.write_claude_config(backup=False)
                self.assertEqual(result, config_path)
                self.assertTrue(config_path.exists())
                with open(config_path) as f:
                    data = json.load(f)
                self.assertIn("mcpServers", data)
                self.assertIn("cherenkov", data["mcpServers"])

    def test_write_claude_config_merges_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "claude_desktop_config.json"
            with open(config_path, "w") as f:
                json.dump({"mcpServers": {"existing_srv": {"command": "echo"}}}, f)
            with patch.object(self.gen, "claude_config_path", return_value=config_path):
                self.gen.write_claude_config(backup=False)
                with open(config_path) as f:
                    data = json.load(f)
                self.assertIn("cherenkov", data["mcpServers"])
                self.assertIn("existing_srv", data["mcpServers"])

    def test_write_cursor_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("cherenkov.mcp.install.Path.cwd", return_value=Path(tmpdir)):
                result = self.gen.write_cursor_config()
                self.assertTrue(result.exists())
                with open(result) as f:
                    data = json.load(f)
                self.assertIn("mcpServers", data)
                self.assertIn("cherenkov", data["mcpServers"])

    def test_write_cursor_config_merges_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cursor_dir = Path(tmpdir) / ".cursor"
            cursor_dir.mkdir()
            config_path = cursor_dir / "mcp.json"
            with open(config_path, "w") as f:
                json.dump({"mcpServers": {"other": {"command": "echo"}}}, f)
            with patch("cherenkov.mcp.install.Path.cwd", return_value=Path(tmpdir)):
                self.gen.write_cursor_config()
                with open(config_path) as f:
                    data = json.load(f)
                self.assertIn("cherenkov", data["mcpServers"])
                self.assertIn("other", data["mcpServers"])

    def test_print_configs_does_not_raise(self):
        try:
            self.gen.print_configs()
        except Exception as e:
            self.fail(f"print_configs raised: {e}")

    def test_run_mcp_install_all(self):
        from cherenkov.mcp.install import run_mcp_install
        try:
            run_mcp_install(platform_target="all", python_path="/usr/bin/python3")
        except Exception as e:
            self.fail(f"run_mcp_install raised: {e}")


if __name__ == "__main__":
    unittest.main()
