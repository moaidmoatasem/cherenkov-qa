"""
CHERENKOV adapters/notifiers/slack.py — Slack Block Kit Notifier.
"""

import os
import json
import urllib.request
from typing import Any, Dict
from cherenkov.core.errors import get_logger
from cherenkov.core.events import CHERENKOVEvent

_log = get_logger("SLACK_NOTIFIER")


class SlackNotifier:
    """Sends rich Block Kit messages to Slack."""

    name: str = "slack"

    def __init__(self):
        self.webhook_url = os.environ.get("CHERENKOV_SLACK_WEBHOOK_URL")

    def send_report(self, report: Dict[str, Any]) -> bool:
        if not self.webhook_url:
            _log.info("CHERENKOV_SLACK_WEBHOOK_URL not set; skipping Slack.")
            return False

        failed_items = [item for item in report.get("items", []) if item.get("status") == "FAIL"]

        if not failed_items:
            color = "#36a64f"  # Green
            text = f"✅ CHERENKOV QA: All tests passed for {report.get('execution_key', 'Unknown Run')}!"
        else:
            color = "#ff0000"  # Red
            text = f"🛑 CHERENKOV QA: Detected {len(failed_items)} conformance failures in {report.get('execution_key', 'Unknown Run')}."

        payload = {
            "text": text,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": text
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Review the failure details and hit auto-heal using the MCP extension!*" if failed_items else "Systems normal."
                    }
                }
            ],
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Failed Endpoint" if failed_items else "Status",
                            "value": str(failed_items[0].get("id")) if failed_items else "OK",
                            "short": False
                        }
                    ]
                }
            ]
        }

        req = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    _log.info("Slack message sent successfully.")
                    resp_body = response.read().decode("utf-8")
                    if resp_body == "ok":
                        return True
                    try:
                        data = json.loads(resp_body)
                        return data.get("ok", False)
                    except json.JSONDecodeError:
                        return True
                return False
        except Exception as exc:
            _log.error("Failed to send Slack message", error=str(exc))
            return False

    def send_thread_reply(self, thread_ts: str, text: str) -> bool:
        """Send a reply to an existing Slack thread."""
        if not self.webhook_url:
            return False
        payload = {
            "text": text,
            "thread_ts": thread_ts
        }
        req = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
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
