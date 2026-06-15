"""
CHERENKOV adapters/notifiers/webhook.py — Generic HTTP POST Webhook Notifier.
Authority: v3.1 + delta.
"""

from __future__ import annotations

import os
import requests
import threading

from cherenkov.core.errors import get_logger
from cherenkov.hitl.contracts import HitlEnvelope

_log = get_logger("WEBHOOK_NOTIFIER")


class WebhookNotifier:
    """Sends CHERENKOV HitlEnvelopes to a generic HTTP endpoint."""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("CHERENKOV_WEBHOOK_URL")
        if not self.webhook_url:
            _log.info("CHERENKOV_WEBHOOK_URL not set; skipping generic webhook.")

    def notify(self, envelope: HitlEnvelope) -> None:
        """Asynchronously send an envelope via HTTP POST."""
        if not self.webhook_url:
            return

        payload = envelope.model_dump()

        def _send() -> None:
            try:
                resp = requests.post(
                    self.webhook_url, json=payload, timeout=5
                )
                resp.raise_for_status()
                _log.info("generic webhook notification sent successfully")
            except Exception as e:
                _log.warning("failed to send generic webhook notification", error=str(e))

        t = threading.Thread(target=_send, daemon=True)
        t.start()
