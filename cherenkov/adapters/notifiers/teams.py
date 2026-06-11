"""
CHERENKOV adapters/notifiers/teams.py — Microsoft Teams Adaptive Card notifier.

Sends conformance drift alerts and HITL status updates to a Teams channel
via an Incoming Webhook, formatted as Teams Adaptive Cards (rich interactive
format natively supported in Teams channels).

Configuration:
    CHERENKOV_TEAMS_WEBHOOK_URL — Teams Incoming Webhook URL.

Usage:
    notifier = TeamsNotifier()
    notifier.notify_envelope(envelope)   # central dispatch

Architecture mirrors SlackNotifier (cherenkov/adapters/notifiers/slack.py)
with Teams-specific Adaptive Card payload format.
"""
from __future__ import annotations

import os
import requests
from typing import Any

from cherenkov.core.errors import get_logger
from cherenkov.hitl.contracts import HitlEnvelope


class TeamsNotifier:
    """Outbound Microsoft Teams webhook notification channel for conformance alerts and HITL status updates."""

    ADAPTIVE_CARD_SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or os.getenv("CHERENKOV_TEAMS_WEBHOOK_URL")
        self._log = get_logger("TEAMS_NOTIFIER")
        if not self.webhook_url:
            self._log.warning("Teams Webhook URL is not configured. Notifications will be skipped.")

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def notify_envelope(self, envelope: HitlEnvelope) -> None:
        """Central entry point matching the NotifyCallback interface."""
        if not self.webhook_url:
            return
        payload = self.format_adaptive_card(envelope)
        if payload:
            self.send_message(payload)

    def send_message(self, payload: dict[str, Any]) -> bool:
        """Sends the constructed JSON payload to the Teams Incoming Webhook endpoint."""
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=5)
            if resp.status_code in (200, 202):
                self._log.info("Teams notification sent successfully")
                return True
            else:
                self._log.error(
                    "Teams returned error status code",
                    status_code=resp.status_code,
                    text=resp.text,
                )
                return False
        except Exception as exc:
            self._log.error("Failed to post message to Teams webhook", error=str(exc))
            return False

    def format_adaptive_card(self, envelope: HitlEnvelope) -> dict[str, Any] | None:
        """
        Formats the envelope payload into a Teams Adaptive Card message.

        Teams Incoming Webhooks accept the MessageCard (legacy) or the newer
        Adaptive Card wrapped in an Attachment. We use Adaptive Cards v1.4
        for maximum richness.

        Returns:
            A dict representing the Teams message payload, or None if the
            envelope command is unrecognised.
        """
        command = envelope.command
        payload = envelope.payload

        if not payload:
            return None

        if command == "openclaw.new_item":
            return self._card_drift_detected(payload)
        elif command == "openclaw.healing_suggestion":
            return self._card_healing_suggestion(payload)
        elif command in ("openclaw.approve", "openclaw.reject"):
            return self._card_hitl_resolved(command, payload)

        return None

    # ── Card builders ─────────────────────────────────────────────────────────

    def _card_drift_detected(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = payload.get("endpoint") or "unknown"
        method = payload.get("method") or "GET"
        run_id = payload.get("run_id") or "N/A"
        spec_hash = payload.get("spec_hash") or "N/A"
        review_gate_failed = payload.get("review_gate_failed") or "unknown"
        confidence_reason = payload.get("confidence_reason") or "No details"

        import re
        m_exp = re.search(r"expected\s*`?(\d+)`?", confidence_reason.lower())
        m_rec = re.search(r"(?:received|got)\s*`?(\d+)`?", confidence_reason.lower())
        expected_status = m_exp.group(1) if m_exp else "N/A"
        received_status = m_rec.group(1) if m_rec else "N/A"

        return self._wrap_adaptive_card({
            "type": "AdaptiveCard",
            "$schema": self.ADAPTIVE_CARD_SCHEMA,
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "🔴 CHERENKOV: Conformance Drift Detected",
                    "weight": "Bolder",
                    "size": "Medium",
                    "color": "Attention"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Endpoint", "value": f"`{method} {endpoint}`"},
                        {"title": "Expected", "value": f"`{expected_status}` (spec)"},
                        {"title": "Received", "value": f"`{received_status}` (server)"},
                        {"title": "Gate Failed", "value": review_gate_failed},
                        {"title": "Run ID", "value": run_id},
                        {"title": "Spec Hash", "value": spec_hash[:8]},
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": f"**Reason:** {confidence_reason}",
                    "wrap": True
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View Report",
                    "url": f"http://localhost:3000/conformance/{run_id}"
                },
                {
                    "type": "Action.OpenUrl",
                    "title": "Create Jira Ticket",
                    "url": "http://localhost:3000/jira/export"
                }
            ]
        })

    def _card_healing_suggestion(self, payload: dict[str, Any]) -> dict[str, Any]:
        scenario_id = payload.get("scenario_id") or "unknown"
        suggestion_text = payload.get("suggestion") or "No suggestion text"
        failure_class = payload.get("failure_class") or "UNKNOWN"

        return self._wrap_adaptive_card({
            "type": "AdaptiveCard",
            "$schema": self.ADAPTIVE_CARD_SCHEMA,
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "💡 CHERENKOV: Healing Suggestion Available",
                    "weight": "Bolder",
                    "size": "Medium",
                    "color": "Warning"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Scenario ID", "value": scenario_id},
                        {"title": "Failure Class", "value": failure_class},
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": "**Proposed Heal:**",
                    "weight": "Bolder"
                },
                {
                    "type": "TextBlock",
                    "text": suggestion_text.strip(),
                    "fontType": "Monospace",
                    "wrap": True
                }
            ]
        })

    def _card_hitl_resolved(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        action = payload.get("action") or ("approve" if "approve" in command else "reject")
        item_id = payload.get("id") or "unknown"
        actor = payload.get("actor") or "unknown"
        current_status = payload.get("current_status") or "resolved"
        reject_reason = payload.get("reject_reason")

        is_approved = action == "approve"
        emoji = "🟢" if is_approved else "🔴"
        color = "Good" if is_approved else "Attention"
        title = f"{emoji} CHERENKOV: HITL Item {action.capitalize()}d"

        facts = [
            {"title": "Item ID", "value": item_id},
            {"title": "Action", "value": action.upper()},
            {"title": "Actor", "value": actor},
            {"title": "Status", "value": current_status},
        ]
        if not is_approved and reject_reason:
            facts.append({"title": "Reason", "value": reject_reason})

        return self._wrap_adaptive_card({
            "type": "AdaptiveCard",
            "$schema": self.ADAPTIVE_CARD_SCHEMA,
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": title,
                    "weight": "Bolder",
                    "size": "Medium",
                    "color": color
                },
                {
                    "type": "FactSet",
                    "facts": facts
                }
            ]
        })

    def _wrap_adaptive_card(self, card: dict[str, Any]) -> dict[str, Any]:
        """
        Wraps an Adaptive Card in the Teams webhook message envelope.
        Teams Incoming Webhooks require the card to be nested inside
        an `attachments` array.
        """
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": card
                }
            ]
        }
