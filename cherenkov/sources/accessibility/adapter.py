"""
CHERENKOV cherenkov/sources/accessibility/adapter.py
Parses sitemap.xml or urls.txt into accessibility scenarios.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator

from cherenkov.sources.accessibility.contracts import AccessibilityScenario, PageTarget


class AccessibilitySourceAdapter:
    """Parses a sitemap.xml or urls.txt into accessibility targets."""

    def __init__(self, source_path: str):
        self.source_path = source_path

    def iter_scenarios(self) -> Iterator[AccessibilityScenario]:
        if not os.path.exists(self.source_path):
            return

        if self.source_path.endswith(".xml"):
            yield from self._parse_sitemap()
        else:
            yield from self._parse_urls_txt()

    def _parse_sitemap(self) -> Iterator[AccessibilityScenario]:
        try:
            tree = ET.parse(self.source_path)
            root = tree.getroot()
            # Handle XML namespace usually found in sitemaps
            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            
            # Find all <url><loc> tags
            urls = []
            for url_elem in root.findall("ns:url", ns) + root.findall("url"):
                loc = url_elem.find("ns:loc", ns)
                if loc is None:
                    loc = url_elem.find("loc")
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())
                    
            for i, url in enumerate(urls):
                scenario_id = f"a11y_page_{i}"
                name_part = url.split("/")[-1]
                if name_part:
                    scenario_id = f"a11y_{name_part.replace('.html', '').replace('-', '_')}"

                yield AccessibilityScenario(
                    scenario_id=scenario_id,
                    page_target=PageTarget(url=url, description=f"Audit {url}")
                )
        except ET.ParseError:
            pass

    def _parse_urls_txt(self) -> Iterator[AccessibilityScenario]:
        with open(self.source_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            
        for i, url in enumerate(lines):
            scenario_id = f"a11y_page_{i}"
            name_part = url.split("/")[-1]
            if name_part:
                scenario_id = f"a11y_{name_part.replace('.html', '').replace('-', '_')}"

            yield AccessibilityScenario(
                scenario_id=scenario_id,
                page_target=PageTarget(url=url, description=f"Audit {url}")
            )
