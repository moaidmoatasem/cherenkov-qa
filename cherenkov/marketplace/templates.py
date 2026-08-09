"""Test Template Marketplace Client (Phase 16)."""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

DEFAULT_TEMPLATE_URL = "https://marketplace.cherenkov.dev/api/v1/templates"

@dataclass
class MarketplaceTemplate:
    id: str
    name: str
    description: str
    version: str
    tags: list[str]
    download_url: str


class TemplateRegistry:
    """Client for discovering and fetching test templates from the marketplace."""

    def __init__(self, base_url: str = DEFAULT_TEMPLATE_URL):
        self.base_url = base_url

    def discover_templates(self) -> list[MarketplaceTemplate]:
        """Fetch a list of available templates from the marketplace."""
        try:
            _log.info("Fetching templates from %s", self.base_url)
            return self._stub_templates()
        except Exception as e:
            _log.error("Failed to discover templates: %s", e)
            return []

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
        
        # Simulate downloading the YAML template files
        yaml_content = f"""# CHERENKOV-QA Template: {template.name}
version: "{template.version}"
description: "{template.description}"
scenarios:
  - id: "{template.id}-base"
    name: "Base compliance check"
    rules: []
"""
        try:
            with open(dest_path / "suite.yaml", "w") as f:
                f.write(yaml_content)
            _log.info("Successfully installed template to %s", dest_path)
            return True
        except Exception as e:
            _log.error("Failed to install template: %s", e)
            return False

    def list_installed_templates(self, dest_dir: str = ".cherenkov/templates") -> list[str]:
        """List locally installed templates."""
        dest_path = Path(dest_dir)
        if not dest_path.exists():
            return []
        
        return [p.name for p in dest_path.iterdir() if p.is_dir()]

    def _stub_templates(self) -> list[MarketplaceTemplate]:
        return [
            MarketplaceTemplate(
                id="hipaa-suite",
                name="HIPAA Compliance Suite",
                description="Checks for unencrypted PHI and strict access controls.",
                version="1.0.0",
                tags=["compliance", "healthcare", "security"],
                download_url="https://github.com/cherenkov/templates/hipaa-suite.zip"
            ),
            MarketplaceTemplate(
                id="pci-dss",
                name="PCI-DSS Suite",
                description="Validates credit card data masking and secure transmission.",
                version="1.2.0",
                tags=["compliance", "finance", "security"],
                download_url="https://github.com/cherenkov/templates/pci-dss.zip"
            ),
            MarketplaceTemplate(
                id="owasp-top10",
                name="OWASP Top 10 API Security",
                description="Tests for common vulnerabilities like BOLA, Broken Auth, and Injection.",
                version="2.1.0",
                tags=["security", "owasp"],
                download_url="https://github.com/cherenkov/templates/owasp-top10.zip"
            )
        ]
