"""MCP Marketplace Registry Client (CC-3)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

_log = logging.getLogger(__name__)

DEFAULT_MARKETPLACE_URL = "https://marketplace.cherenkov.dev/api/v1/tools"


@dataclass
class MarketplaceTool:
    id: str
    name: str
    description: str
    version: str
    repository_url: str
    install_command: str


class MarketplaceRegistry:
    """Client for discovering and fetching tools from the MCP Marketplace."""

    def __init__(self, base_url: str = DEFAULT_MARKETPLACE_URL):
        self.base_url = base_url

    def discover_tools(self) -> list[MarketplaceTool]:
        """Fetch a list of available tools from the marketplace."""
        try:
            # For demonstration, we simulate a network response or use a stub
            # In production, this would make an actual HTTP call.
            _log.info("Fetching MCP tools from %s", self.base_url)
            return self._stub_tools()
        except Exception as e:
            _log.error("Failed to discover tools: %s", e)
            return []

    def get_tool_info(self, tool_id: str) -> MarketplaceTool | None:
        """Fetch detailed information for a specific tool."""
        tools = self.discover_tools()
        for t in tools:
            if t.id == tool_id:
                return t
        return None

    def _stub_tools(self) -> list[MarketplaceTool]:
        return [
            MarketplaceTool(
                id="slack-notifier",
                name="Slack Notifier MCP",
                description="Sends notifications to Slack using Block Kit.",
                version="1.0.0",
                repository_url="https://github.com/cherenkov/mcp-slack",
                install_command="pip install cherenkov-mcp-slack"
            ),
            MarketplaceTool(
                id="github-webhooks",
                name="GitHub Webhooks",
                description="Receives PR events and triggers QA pipelines.",
                version="1.1.0",
                repository_url="https://github.com/cherenkov/mcp-github",
                install_command="pip install cherenkov-mcp-github"
            ),
            MarketplaceTool(
                id="jira-sync",
                name="Jira Sync MCP",
                description="Bidirectional sync with Jira for bugs and coverage.",
                version="2.0.1",
                repository_url="https://github.com/cherenkov/mcp-jira",
                install_command="pip install cherenkov-mcp-jira"
            )
        ]
