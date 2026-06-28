"""
CHERENKOV adapters/notifiers/pagerduty.py — PagerDuty Events API V2 Notifier.
"""

import os
import json
import urllib.request
from typing import Any, Dict
from cherenkov.core.events import CHERENKOVEvent
from cherenkov.core.errors import get_logger

_log = get_logger("PAGERDUTY_NOTIFIER")


class PagerDutyNotifier:
    """Sends incidents to PagerDuty via Events API V2."""

    name: str = "pagerduty"

    def __init__(self):
        self.routing_key = os.environ.get("CHERENKOV_PAGERDUTY_ROUTING_KEY")

    def send_report(self, report: Dict[str, Any]) -> bool:
        if not self.routing_key:
            _log.info("CHERENKOV_PAGERDUTY_ROUTING_KEY not set; skipping PagerDuty.")
            return False

        failed_items = [item for item in report.get("items", []) if item.get("status") == "FAIL"]
        if not failed_items:
            # Only page if there are failures
            return True

        url = "https://events.pagerduty.com/v2/enqueue"

        payload = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"CHERENKOV QA Drift Detected: {len(failed_items)} failures in {report.get('execution_key', 'Unknown Run')}",
                "source": "cherenkov-qa-engine",
                "severity": "critical",
                "custom_details": report
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 202:
                    _log.info("PagerDuty incident triggered successfully.")
                    return True
                return False
        except Exception as exc:
            _log.error("Failed to trigger PagerDuty incident", error=str(exc))
            return False

    def send(self, report: Dict[str, Any]) -> bool:
        return self.send_report(report)

    def notify_event(self, event: CHERENKOVEvent) -> None:
        self.send_report(event.to_dict())
