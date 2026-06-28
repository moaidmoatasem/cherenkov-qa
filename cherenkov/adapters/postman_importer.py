"""
CHERENKOV adapters/postman_importer.py — Postman Collection Importer.
Converts Postman v2.1 collection format into CHERENKOV Scenario definitions.
"""

import json
from typing import Any

from cherenkov.core.contracts import Scenario
from cherenkov.core.errors import get_logger

_log = get_logger("POSTMAN_IMPORTER")


class PostmanImporter:
    """Parses Postman Collections and generates Cherenkov Scenarios."""

    def import_collection(self, file_path: str) -> list[Scenario]:
        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)
        except Exception as exc:
            _log.error("Failed to read Postman collection", error=str(exc))
            return []

        scenarios = []
        items = data.get("item", [])

        # Flattens folders
        def _extract_items(item_list: list[dict[str, Any]]):
            for it in item_list:
                if "item" in it:
                    _extract_items(it["item"])
                else:
                    scenarios.append(self._parse_item(it))

        _extract_items(items)
        _log.info("Postman collection imported", count=len(scenarios))
        return [s for s in scenarios if s is not None]

    def _parse_item(self, item: dict[str, Any]) -> Scenario | None:
        request = item.get("request")
        if not request:
            return None

        # Extract URL
        url_obj = request.get("url", {})
        if isinstance(url_obj, str):
            raw_url = url_obj
        else:
            raw_url = url_obj.get("raw", "")

        method = request.get("method", "GET").upper()

        headers = {}
        for h in request.get("header", []):
            headers[h.get("key")] = h.get("value")

        return Scenario(
            case_type="api_conformance",
            method=method,
            endpoint=raw_url,
            expected_status=200
        )
