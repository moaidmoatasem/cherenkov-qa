"""MCP Marketplace Registry Client (Phase 16 & CC-3)."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

DEFAULT_MARKETPLACE_URL = "https://marketplace.cherenkov.dev/api/v1/tools"
LOCAL_TOOLS_DIR = Path.home() / ".cherenkov" / "marketplace" / "tools"


@dataclass
class MarketplaceTool:
    id: str
    name: str
    description: str
    version: str
    repository_url: str
    install_command: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> MarketplaceTool:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            repository_url=data.get("repository_url", ""),
            install_command=data.get("install_command", ""),
        )


class MarketplaceRegistry:
    """Client for discovering, fetching, and publishing tools from the MCP Marketplace."""

    def __init__(
        self,
        base_url: str = DEFAULT_MARKETPLACE_URL,
        local_dir: Path | None = None,
    ):
        self.base_url = base_url
        self.local_dir = local_dir or LOCAL_TOOLS_DIR
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def discover_tools(self) -> list[MarketplaceTool]:
        """Fetch a list of available tools from local store and remote/stub."""
        tools = self._load_local_tools()
        stubs = self._stub_tools()

        local_ids = {t.id for t in tools}
        for t in stubs:
            if t.id not in local_ids:
                tools.append(t)

        return tools

    def get_tool_info(self, tool_id: str) -> MarketplaceTool | None:
        """Fetch detailed information for a specific tool."""
        tools = self.discover_tools()
        for t in tools:
            if t.id == tool_id:
                return t
        return None

    def publish_tool(self, tool: MarketplaceTool) -> bool:
        """Publish a new tool to the marketplace registry (and save locally)."""
        try:
            _log.info("Publishing tool %s to %s", tool.id, self.base_url)
            target_dir = self.local_dir / tool.id
            target_dir.mkdir(parents=True, exist_ok=True)

            meta_file = target_dir / "tool.json"
            meta_file.write_text(json.dumps(tool.to_dict(), indent=2))
            _log.info("Published tool %s locally at %s", tool.id, meta_file)
            return True
        except Exception as e:
            _log.error("Failed to publish tool %s: %s", tool.id, e)
            return False

    def _load_local_tools(self) -> list[MarketplaceTool]:
        tools = []
        if not self.local_dir.exists():
            return tools

        for item in self.local_dir.iterdir():
            if item.is_dir():
                meta = item / "tool.json"
                if meta.exists():
                    try:
                        data = json.loads(meta.read_text())
                        tools.append(MarketplaceTool.from_dict(data))
                    except Exception as e:
                        _log.warning("Failed to parse local tool %s: %s", meta, e)

        return tools

    def _stub_tools(self) -> list[MarketplaceTool]:
        return [
            MarketplaceTool(
                id="slack-notifier",
                name="Slack Notifier MCP",
                description="Sends notifications to Slack using Block Kit.",
                version="1.0.0",
                repository_url="https://github.com/cherenkov/mcp-slack",
                install_command="pip install cherenkov-mcp-slack",
            ),
            MarketplaceTool(
                id="github-webhooks",
                name="GitHub Webhooks",
                description="Receives PR events and triggers QA pipelines.",
                version="1.1.0",
                repository_url="https://github.com/cherenkov/mcp-github",
                install_command="pip install cherenkov-mcp-github",
            ),
            MarketplaceTool(
                id="jira-sync",
                name="Jira Sync MCP",
                description="Bidirectional sync with Jira for bugs and coverage.",
                version="2.0.1",
                repository_url="https://github.com/cherenkov/mcp-jira",
                install_command="pip install cherenkov-mcp-jira",
            ),
        ]
