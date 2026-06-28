"""
CHERENKOV validate/asyncapi.py — AsyncAPI Specification Parser.
"""

import yaml
from typing import List
from cherenkov.core.contracts import Scenario
from cherenkov.core.errors import get_logger

_log = get_logger("ASYNCAPI_PARSER")


class AsyncAPIParser:
    """Parses AsyncAPI specifications to generate test scenarios."""

    def parse_spec(self, file_path: str) -> List[Scenario]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as exc:
            _log.error("Failed to read AsyncAPI spec", error=str(exc))
            return []

        scenarios = []
        channels = data.get("channels", {})

        for channel_name, channel_item in channels.items():
            # Check for publish/subscribe methods
            for operation in ["publish", "subscribe"]:
                if operation in channel_item:
                    scenarios.append(
                        Scenario(
                            case_type="async_conformance",
                            method=operation.upper(),
                            endpoint=channel_name,
                            expected_status=0  # Async usually doesn't have HTTP status codes
                        )
                    )

        _log.info("AsyncAPI spec parsed", channels_found=len(scenarios))
        return scenarios
