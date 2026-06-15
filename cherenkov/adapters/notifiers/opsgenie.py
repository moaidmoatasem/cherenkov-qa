"""
CHERENKOV adapters/notifiers/opsgenie.py — OpsGenie Alert API Notifier.
"""

import os
import json
import urllib.request
from typing import Any, Dict
from cherenkov.core.events import CHERENKOVEvent
from cherenkov.core.errors import get_logger

_log = get_logger("OPSGENIE_NOTIFIER")


class OpsGenieNotifier:
    """Sends alerts to OpsGenie."""

    name: str = "opsgenie"

    def __init__(self):
        self.api_key = os.environ.get("CHERENKOV_OPSGENIE_API_KEY")

    def send_report(self, report: Dict[str, Any]) -> bool:
        if not self.api_key:
            _log.info("CHERENKOV_OPSGENIE_API_KEY not set; skipping OpsGenie.")
            return False

        failed_items = [item for item in report.get("items", []) if item.get("status") == "FAIL"]
        if not failed_items:
            # Only page if there are failures
            return True

        url = "https://api.opsgenie.com/v2/alerts"
        
        payload = {
            "message": f"CHERENKOV QA Drift Detected: {len(failed_items)} failures",
            "alias": report.get("execution_key", "cherenkov-run"),
            "description": json.dumps(report, indent=2),
            "priority": "P1"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"GenieKey {self.api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 202):
                    _log.info("OpsGenie alert created successfully.")
                    return True
                return False
        except Exception as exc:
            _log.error("Failed to create OpsGenie alert", error=str(exc))
            return False

    def send(self, report: Dict[str, Any]) -> bool:
        return self.send_report(report)

    def notify_event(self, event: CHERENKOVEvent) -> None:
        self.send_report(event.to_dict())
