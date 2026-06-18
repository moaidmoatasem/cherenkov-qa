"""
cherenkov/adapters/notifiers/teams.py — Microsoft Teams Adaptive Card Notifier.
"""

import os
import json
import urllib.request
from typing import Any, Dict
from cherenkov.core.events import CHERENKOVEvent


class TeamsNotifier:
    """Sends CHERENKOV reports to Microsoft Teams via Incoming Webhooks (Adaptive Cards)."""

    name: str = "teams"

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("CHERENKOV_TEAMS_WEBHOOK_URL")

    def send_report(self, report: Dict[str, Any]) -> bool:
        """Formats and sends a DivergenceReport to Teams."""
        if not self.webhook_url:
            return False

        failed_count = sum(
            1
            for i in report.get("items", [])
            if str(i.get("status", "")).upper() in ["FAIL", "DRIFT"]
        )
        total_count = len(report.get("items", []))
        color = "Attention" if failed_count > 0 else "Good"

        facts = [
            {"title": "Execution Key", "value": report.get("execution_key", "N/A")},
            {"title": "Total Tests", "value": str(total_count)},
            {"title": "Failures", "value": str(failed_count)},
        ]

        adaptive_card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Medium",
                                "weight": "Bolder",
                                "text": "🛑 CHERENKOV QA Run Failed"
                                if failed_count > 0
                                else "✅ CHERENKOV QA Run Passed",
                                "color": color,
                            },
                            {"type": "FactSet", "facts": facts},
                        ],
                    },
                }
            ],
        }

        req = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(adaptive_card).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except Exception:
            return False

    def send(self, report: Dict[str, Any]) -> bool:
        return self.send_report(report)

    def notify_event(self, event: CHERENKOVEvent) -> None:
        self.send_report(event.to_dict())
