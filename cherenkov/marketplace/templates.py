"""Test Template Marketplace Client (Phase 16)."""
from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

DEFAULT_TEMPLATE_URL = "https://marketplace.cherenkov.dev/api/v1/templates"
LOCAL_MARKETPLACE_DIR = Path.home() / ".cherenkov" / "marketplace" / "templates"


@dataclass
class MarketplaceTemplate:
    id: str
    name: str
    description: str
    version: str
    tags: list[str]
    download_url: str

    def to_dict(self) -> dict[str, str | list[str]]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> MarketplaceTemplate:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            download_url=data.get("download_url", ""),
        )


class TemplateRegistry:
    """Client for discovering, fetching, installing, and publishing test templates."""

    def __init__(self, base_url: str = DEFAULT_TEMPLATE_URL, local_dir: Path | None = None):
        self.base_url = base_url
        self.local_dir = local_dir or LOCAL_MARKETPLACE_DIR
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def discover_templates(self) -> list[MarketplaceTemplate]:
        """Fetch a list of available templates from local store and remote/stub."""
        templates = self._load_local_templates()
        remote_or_stub = self._stub_templates()

        # Combine, local overrides stub by ID
        local_ids = {t.id for t in templates}
        for t in remote_or_stub:
            if t.id not in local_ids:
                templates.append(t)

        return templates

    def get_template_info(self, template_id: str) -> MarketplaceTemplate | None:
        """Fetch detailed information for a specific template."""
        templates = self.discover_templates()
        for t in templates:
            if t.id == template_id:
                return t
        return None

    def install_template(self, template_id: str, dest_dir: str = ".cherenkov/templates") -> bool:
        """Install a template into the local project directory."""
        template = self.get_template_info(template_id)
        if not template:
            _log.error("Template %s not found in marketplace.", template_id)
            return False

        _log.info("Installing template %s (v%s)...", template.name, template.version)
        dest_path = Path(dest_dir) / template.id
        dest_path.mkdir(parents=True, exist_ok=True)

        # Check if local template source file exists
        local_src_file = self.local_dir / template.id / "suite.yaml"
        if local_src_file.exists():
            shutil.copy(local_src_file, dest_path / "suite.yaml")
        else:
            # Generate default template file
            yaml_content = f"""# CHERENKOV-QA Template: {template.name}
version: "{template.version}"
description: "{template.description}"
scenarios:
  - id: "{template.id}-base"
    name: "Base compliance check"
    rules: []
"""
            with open(dest_path / "suite.yaml", "w") as f:
                f.write(yaml_content)

        _log.info("Successfully installed template to %s", dest_path)
        return True

    def publish_template(
        self,
        template: MarketplaceTemplate,
        file_path: str | Path | None = None,
    ) -> bool:
        """Publish a template to the local marketplace store."""
        try:
            target_dir = self.local_dir / template.id
            target_dir.mkdir(parents=True, exist_ok=True)

            meta_file = target_dir / "template.json"
            meta_file.write_text(json.dumps(template.to_dict(), indent=2))

            if file_path and Path(file_path).exists():
                shutil.copy(Path(file_path), target_dir / "suite.yaml")

            _log.info("Published template %s to %s", template.id, target_dir)
            return True
        except Exception as e:
            _log.error("Failed to publish template %s: %s", template.id, e)
            return False

    def list_installed_templates(self, dest_dir: str = ".cherenkov/templates") -> list[str]:
        """List locally installed templates."""
        dest_path = Path(dest_dir)
        if not dest_path.exists():
            return []

        return [p.name for p in dest_path.iterdir() if p.is_dir()]

    def _load_local_templates(self) -> list[MarketplaceTemplate]:
        templates = []
        if not self.local_dir.exists():
            return templates

        for item in self.local_dir.iterdir():
            if item.is_dir():
                meta = item / "template.json"
                if meta.exists():
                    try:
                        data = json.loads(meta.read_text())
                        templates.append(MarketplaceTemplate.from_dict(data))
                    except Exception as e:
                        _log.warning("Failed to parse local template %s: %s", meta, e)

        return templates

    def _stub_templates(self) -> list[MarketplaceTemplate]:
        return [
            MarketplaceTemplate(
                id="hipaa-suite",
                name="HIPAA Compliance Suite",
                description="Checks for unencrypted PHI and strict access controls.",
                version="1.0.0",
                tags=["compliance", "healthcare", "security"],
                download_url="https://github.com/cherenkov/templates/hipaa-suite.zip",
            ),
            MarketplaceTemplate(
                id="pci-dss",
                name="PCI-DSS Suite",
                description="Validates credit card data masking and secure transmission.",
                version="1.2.0",
                tags=["compliance", "finance", "security"],
                download_url="https://github.com/cherenkov/templates/pci-dss.zip",
            ),
            MarketplaceTemplate(
                id="owasp-top10",
                name="OWASP Top 10 API Security",
                description="Tests for common vulnerabilities like BOLA, Broken Auth, and Injection.",
                version="2.1.0",
                tags=["security", "owasp"],
                download_url="https://github.com/cherenkov/templates/owasp-top10.zip",
            ),
        ]
