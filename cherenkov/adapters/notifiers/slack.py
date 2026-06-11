from __future__ import annotations

import os
import requests
from typing import Any

from cherenkov.core.errors import get_logger
from cherenkov.hitl.contracts import HitlEnvelope

class SlackNotifier:
    """Outbound Slack webhook notification channel for conformance alerts and HITL status updates."""

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or os.getenv("CHERENKOV_SLACK_WEBHOOK_URL")
        self._log = get_logger("SLACK_NOTIFIER")
        if not self.webhook_url:
            self._log.warning("Slack Webhook URL is not configured. Notifications will be skipped.")

    def notify_envelope(self, envelope: HitlEnvelope) -> None:
        """Central entry point matching the NotifyCallback interface."""
        if not self.webhook_url:
            return

        payload = self.format_block_kit(envelope)
        if payload:
            self.send_message(payload)

    def send_message(self, payload: dict[str, Any]) -> bool:
        """Sends the constructed JSON payload to the Slack Incoming Webhook endpoint."""
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=5)
            if resp.status_code == 200:
                self._log.info("Slack notification sent successfully")
                return True
            else:
                self._log.error("Slack returned error status code", status_code=resp.status_code, text=resp.text)
                return False
        except Exception as exc:
            self._log.error("Failed to post message to Slack webhook", error=str(exc))
            return False

    def format_block_kit(self, envelope: HitlEnvelope) -> dict[str, Any] | None:
        """Formats the envelope payload into a rich Slack Block Kit message structure."""
        command = envelope.command
        payload = envelope.payload

        if not payload:
            return None

        blocks: list[dict[str, Any]] = []

        if command == "openclaw.new_item":
            # Conformance drift / HITL item pending review
            endpoint = payload.get("endpoint") or "unknown endpoint"
            method = payload.get("method") or "GET"
            mutation_id = payload.get("mutation_id") or "N/A"
            mutation_label = payload.get("mutation_label") or "N/A"
            confidence = payload.get("confidence") or 0.0
            confidence_reason = payload.get("confidence_reason") or "No details"
            review_gate_failed = payload.get("review_gate_failed") or "unknown"
            spec_hash = payload.get("spec_hash") or "N/A"
            run_id = payload.get("run_id") or "N/A"

            # Check if expected and received statuses are mentioned in confidence_reason
            expected_status = "N/A"
            received_status = "N/A"
            import re
            m_exp = re.search(r"expected\s*`?(\d+)`?", confidence_reason.lower())
            m_rec = re.search(r"(?:received|got)\s*`?(\d+)`?", confidence_reason.lower())
            if m_exp:
                expected_status = m_exp.group(1)
            if m_rec:
                received_status = m_rec.group(1)

            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔴 CHERENKOV: Conformance drift detected",
                    "emoji": True
                }
            })
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Service:* payment-api | *Spec:* `{spec_hash[:8]}`\n"
                        f"*Run ID:* `{run_id}`\n"
                        f"*`{method} {endpoint}`*\n"
                        f"*Expected:* `{expected_status}` (spec) → *Got:* `{received_status}` (server)\n"
                        f"*Gate Failed:* `{review_gate_failed}`\n"
                        f"*Reason:* {confidence_reason}"
                    )
                }
            })

            # Action buttons
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Report",
                            "emoji": True
                        },
                        "value": "view_report",
                        "url": f"http://localhost:3000/conformance/{run_id}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Create Jira Ticket",
                            "emoji": True
                        },
                        "value": "create_jira",
                        "url": "http://localhost:3000/jira/export"
                    }
                ]
            })

        elif command == "openclaw.healing_suggestion":
            # Healing suggestion available
            scenario_id = payload.get("scenario_id") or "unknown"
            suggestion_text = payload.get("suggestion") or "No suggestion text"
            failure_class = payload.get("failure_class") or "UNKNOWN"

            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "💡 CHERENKOV: Healing Suggestion Available",
                    "emoji": True
                }
            })

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Scenario ID:* `{scenario_id}`\n"
                        f"*Failure Class:* `{failure_class}`\n"
                        f"*Proposed Heal:* \n"
                        f"```{suggestion_text.strip()}```"
                    )
                }
            })

        elif command in ("openclaw.approve", "openclaw.reject"):
            # HITL resolution
            action = payload.get("action") or "resolved"
            item_id = payload.get("id") or "unknown"
            actor = payload.get("actor") or "unknown"
            current_status = payload.get("current_status") or "resolved"
            
            emoji = "🟢" if action == "approve" else "🔴"
            title = f"{emoji} CHERENKOV: HITL Item {action.capitalize()}d"

            msg_text = (
                f"*Item ID:* `{item_id}`\n"
                f"*Action:* `{action.upper()}`\n"
                f"*Actor:* `{actor}`\n"
                f"*Status:* `{current_status}`"
            )
            if action == "reject" and payload.get("reject_reason"):
                msg_text += f"\n*Reason:* {payload['reject_reason']}"

            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title,
                    "emoji": True
                }
            })

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": msg_text
                }
            })
        else:
            return None

        return {"blocks": blocks}
