"""Unit tests for MCP Marketplace (CC-3)."""

from cherenkov.mcp.marketplace.registry import MarketplaceRegistry
from cherenkov.mcp.marketplace.sandbox import SandboxValidator


def test_marketplace_registry_discover():
    registry = MarketplaceRegistry()
    tools = registry.discover_tools()
    
    assert len(tools) > 0
    assert any(t.id == "slack-notifier" for t in tools)


def test_marketplace_registry_get_info():
    registry = MarketplaceRegistry()
    tool = registry.get_tool_info("github-webhooks")
    
    assert tool is not None
    assert tool.id == "github-webhooks"
    assert "github" in tool.install_command


def test_sandbox_validator_allowed():
    validator = SandboxValidator()
    manifest = {
        "id": "safe-tool",
        "name": "Safe Tool",
        "install_command": "pip install safe-tool"
    }
    
    assert validator.validate_tool_manifest(manifest) is True


def test_sandbox_validator_missing_keys():
    validator = SandboxValidator()
    manifest = {
        "id": "bad-tool",
        # missing name and install_command
    }
    
    assert validator.validate_tool_manifest(manifest) is False


def test_sandbox_validator_malicious_command():
    validator = SandboxValidator()
    manifest = {
        "id": "bad-tool",
        "name": "Bad Tool",
        "install_command": "sudo rm -rf /"
    }
    
    assert validator.validate_tool_manifest(manifest) is False
