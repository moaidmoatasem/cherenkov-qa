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
    """Represents a tool package entry in the MCP Marketplace.

    Attributes:
        id (str): Unique tool identifier.
        name (str): Display name of the tool.
        description (str): Functional summary description.
        version (str): Semantic version string.
        repository_url (str): Source code repository URL.
        install_command (str): Shell installation command string.
    """

    id: str
    name: str
    description: str
    version: str
    repository_url: str
    install_command: str

    def to_dict(self) -> dict[str, str]:
        """Convert MarketplaceTool instance to dictionary format.

        Returns:
            dict[str, str]: Dictionary of tool attributes.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> MarketplaceTool:
        """Instantiate MarketplaceTool from a dictionary.

        Args:
            data (dict): Dictionary containing tool properties.

        Returns:
            MarketplaceTool: Constructed MarketplaceTool object.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            repository_url=data.get("repository_url", ""),
            install_command=data.get("install_command", ""),
        )


class MarketplaceRegistry:
    """Client for discovering, fetching, and publishing tools from the MCP Marketplace.

    Attributes:
        base_url (str): Remote marketplace API endpoint URL.
        local_dir (Path): Local filesystem directory for tool manifests.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_MARKETPLACE_URL,
        local_dir: Path | None = None,
    ) -> None:
        """Initialize MarketplaceRegistry.

        Args:
            base_url (str): Base marketplace API URL. Defaults to DEFAULT_MARKETPLACE_URL.
            local_dir (Path | None): Local directory path for caching tool manifests. Defaults to None.

        Returns:
            None
        """
        self.base_url = base_url
        self.local_dir = local_dir or LOCAL_TOOLS_DIR
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def discover_tools(self) -> list[MarketplaceTool]:
        """Fetch a list of available tools from local store and remote/stub.

        Returns:
            list[MarketplaceTool]: Combined list of discovered marketplace tools.
        """
        tools = self._load_local_tools()
        stubs = self._stub_tools()

        local_ids = {t.id for t in tools}
        for t in stubs:
            if t.id not in local_ids:
                tools.append(t)

        return tools

    def get_tool_info(self, tool_id: str) -> MarketplaceTool | None:
        """Fetch detailed information for a specific tool.

        Args:
            tool_id (str): Unique tool identifier.

        Returns:
            MarketplaceTool | None: Matching MarketplaceTool if found, else None.
        """
        tools = self.discover_tools()
        for t in tools:
            if t.id == tool_id:
                return t
        return None

    def publish_tool(self, tool: MarketplaceTool) -> bool:
        """Publish a new tool to the marketplace registry (and save locally).

        Args:
            tool (MarketplaceTool): MarketplaceTool object to publish.

        Returns:
            bool: True if publication succeeded; False otherwise.
        """
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
        """Load locally stored marketplace tools from local directory.

        Returns:
            list[MarketplaceTool]: List of tools loaded from disk.
        """
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
        """Return pre-defined stub MarketplaceTool instances.

        Returns:
            list[MarketplaceTool]: List of default built-in stub tools.
        """
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

