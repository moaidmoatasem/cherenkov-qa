"""Unit tests for documentation version warning banner and docs structure parity (v1.4)."""
from __future__ import annotations

import os
from pathlib import Path
import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_docs_site_overrides_outdated_block():
    """Verify docs-site/overrides/main.html overrides outdated block with link to 1.4."""
    override_path = REPO_ROOT / "docs-site" / "overrides" / "main.html"
    assert override_path.is_file(), f"Missing {override_path}"
    content = override_path.read_text(encoding="utf-8")
    assert '{% block outdated %}' in content
    assert 'class="md-version-warning"' in content
    assert "https://moaidmoatasem.github.io/cherenkov-qa/1.4/" in content


def test_root_overrides_outdated_block():
    """Verify root overrides/main.html overrides outdated block with link to 1.4."""
    override_path = REPO_ROOT / "overrides" / "main.html"
    assert override_path.is_file(), f"Missing {override_path}"
    content = override_path.read_text(encoding="utf-8")
    assert '{% block outdated %}' in content
    assert 'class="md-version-warning"' in content
    assert "https://moaidmoatasem.github.io/cherenkov-qa/1.4/" in content


def test_mkdocs_configurations_version_1_4():
    """Verify root mkdocs.yml and docs-site/mkdocs.yml have version 1.4 set as current."""
    root_cfg_path = REPO_ROOT / "mkdocs.yml"
    site_cfg_path = REPO_ROOT / "docs-site" / "mkdocs.yml"

    assert root_cfg_path.is_file()
    assert site_cfg_path.is_file()

    root_cfg = yaml.safe_load(root_cfg_path.read_text(encoding="utf-8"))
    site_cfg = yaml.safe_load(site_cfg_path.read_text(encoding="utf-8"))

    assert root_cfg.get("extra", {}).get("version", {}).get("current") == "1.4"
    assert "1.4" in root_cfg.get("extra", {}).get("version", {}).get("versions", [])

    assert site_cfg.get("extra", {}).get("version", {}).get("current") == "1.4"
    assert site_cfg.get("extra", {}).get("version", {}).get("provider") == "mike"


def test_version_banner_js_logic():
    """Verify version-banner.js contains logic to suppress on 1.4/latest and show on older."""
    js_path = REPO_ROOT / "docs-site" / "docs" / "javascripts" / "version-banner.js"
    assert js_path.is_file()
    content = js_path.read_text(encoding="utf-8")
    assert "/1.4/" in content
    assert "/latest/" in content
    assert "/1.3/" in content
    assert "/1.2/" in content
    assert "md-version-warning" in content


def test_version_banner_css_styling():
    """Verify extra.css defines .md-version-warning banner styles."""
    css_path = REPO_ROOT / "docs-site" / "docs" / "stylesheets" / "extra.css"
    assert css_path.is_file()
    content = css_path.read_text(encoding="utf-8")
    assert ".md-version-warning" in content


def test_docs_1_4_and_docs_site_parity():
    """Verify complete parity between docs/1.4/ and docs-site/docs/ markdown pages."""
    docs_1_4_dir = REPO_ROOT / "docs" / "1.4"
    docs_site_dir = REPO_ROOT / "docs-site" / "docs"

    assert docs_1_4_dir.is_dir()
    assert docs_site_dir.is_dir()

    md_1_4 = {
        str(p.relative_to(docs_1_4_dir)).replace("\\", "/")
        for p in docs_1_4_dir.rglob("*.md")
    }
    md_site = {
        str(p.relative_to(docs_site_dir)).replace("\\", "/")
        for p in docs_site_dir.rglob("*.md")
    }

    assert len(md_site) == 55
    assert md_1_4 == md_site, f"Mismatch between docs/1.4 and docs-site/docs: {md_1_4 ^ md_site}"

    # Verify content identical
    for rel_path in md_site:
        f1 = (docs_1_4_dir / rel_path).read_text(encoding="utf-8")
        f2 = (docs_site_dir / rel_path).read_text(encoding="utf-8")
        assert f1 == f2, f"Content mismatch in {rel_path}"
