"""tests/unit/test_marketplace_phase16.py — Phase 16 Marketplace & Platform unit tests.

Tests cover:
  - TemplateRegistry: discovery, local publishing, template metadata, installation
  - MarketplaceRegistry: tool discovery, local tool publishing, metadata parsing
  - CLI: 'cherenkov template search', 'cherenkov template install', 'cherenkov template publish'
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from click.testing import CliRunner

from cherenkov.marketplace.templates import MarketplaceTemplate, TemplateRegistry
from cherenkov.mcp.marketplace.registry import MarketplaceTool, MarketplaceRegistry
from cherenkov.cli.commands.template_cmd import template_cmd


@pytest.fixture
def temp_marketplace(tmp_path: Path):
    template_dir = tmp_path / "templates"
    tool_dir = tmp_path / "tools"
    return template_dir, tool_dir


class TestTemplateRegistry:
    def test_discover_default_stubs(self, temp_marketplace):
        template_dir, _ = temp_marketplace
        reg = TemplateRegistry(local_dir=template_dir)
        templates = reg.discover_templates()
        assert len(templates) >= 3
        ids = [t.id for t in templates]
        assert "hipaa-suite" in ids
        assert "owasp-top10" in ids

    def test_publish_and_discover_local_template(self, temp_marketplace):
        template_dir, _ = temp_marketplace
        reg = TemplateRegistry(local_dir=template_dir)

        tmpl = MarketplaceTemplate(
            id="custom-sec",
            name="Custom Security Suite",
            description="Tests custom security endpoints",
            version="1.0.0",
            tags=["security", "custom"],
            download_url="local://custom-sec",
        )
        assert reg.publish_template(tmpl) is True

        # Check local persistence
        meta_file = template_dir / "custom-sec" / "template.json"
        assert meta_file.exists()

        # Check discovery includes custom template
        discovered = reg.discover_templates()
        custom = [t for t in discovered if t.id == "custom-sec"]
        assert len(custom) == 1
        assert custom[0].name == "Custom Security Suite"

    def test_install_template(self, temp_marketplace, tmp_path: Path):
        template_dir, _ = temp_marketplace
        reg = TemplateRegistry(local_dir=template_dir)

        install_dest = tmp_path / "installed_templates"
        res = reg.install_template("hipaa-suite", dest_dir=str(install_dest))
        assert res is True
        assert (install_dest / "hipaa-suite" / "suite.yaml").exists()

        installed_list = reg.list_installed_templates(dest_dir=str(install_dest))
        assert "hipaa-suite" in installed_list


class TestMCPMarketplaceRegistry:
    def test_discover_default_tools(self, temp_marketplace):
        _, tool_dir = temp_marketplace
        reg = MarketplaceRegistry(local_dir=tool_dir)
        tools = reg.discover_tools()
        assert len(tools) >= 3
        ids = [t.id for t in tools]
        assert "slack-notifier" in ids

    def test_publish_and_discover_local_tool(self, temp_marketplace):
        _, tool_dir = temp_marketplace
        reg = MarketplaceRegistry(local_dir=tool_dir)

        tool = MarketplaceTool(
            id="custom-mcp",
            name="Custom MCP Tool",
            description="Custom integration",
            version="0.5.0",
            repository_url="https://github.com/example/custom",
            install_command="pip install custom-mcp",
        )
        assert reg.publish_tool(tool) is True

        meta_file = tool_dir / "custom-mcp" / "tool.json"
        assert meta_file.exists()

        info = reg.get_tool_info("custom-mcp")
        assert info is not None
        assert info.name == "Custom MCP Tool"


class TestTemplateCLI:
    def test_template_search(self):
        runner = CliRunner()
        result = runner.invoke(template_cmd, ["search"])
        assert result.exit_code == 0
        assert "HIPAA Compliance Suite" in result.output

    def test_template_publish_cli(self, temp_marketplace, tmp_path: Path):
        template_dir, _ = temp_marketplace
        runner = CliRunner()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("cherenkov.marketplace.templates.LOCAL_MARKETPLACE_DIR", template_dir)
            result = runner.invoke(
                template_cmd,
                [
                    "publish",
                    "--id", "cli-template",
                    "--name", "CLI Published Template",
                    "--description", "Testing CLI publishing",
                    "--tags", "cli,test",
                ],
            )
            assert result.exit_code == 0
            assert "Successfully published" in result.output
