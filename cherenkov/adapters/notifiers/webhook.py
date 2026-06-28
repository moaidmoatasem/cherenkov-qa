"""
CHERENKOV adapters/notifiers/webhook.py — Generic HTTP POST Webhook Notifier.
"""

from __future__ import annotations

import os
import requests
import threading
from typing import Any, Dict

from cherenkov.core.errors import get_logger
from cherenkov.hitl.contracts import HitlEnvelope, ok_envelope
from cherenkov.core.events import CHERENKOVEvent

_log = get_logger("WEBHOOK_NOTIFIER")


class WebhookNotifier:
    """Sends CHERENKOV HitlEnvelopes to a generic HTTP endpoint."""

    name: str = "webhook"

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
            import hmac
            import hashlib
            import json
            try:
                # Optional HMAC signing for secure webhook dispatch
                headers = {"Content-Type": "application/json"}
                secret = os.environ.get("CHERENKOV_WEBHOOK_SECRET")
                body_bytes = json.dumps(payload).encode("utf-8")
                
                if secret:
                    signature = hmac.new(secret.encode("utf-8"), msg=body_bytes, digestmod=hashlib.sha256).hexdigest()
                    headers["X-Cherenkov-Signature-256"] = f"sha256={signature}"

                resp = requests.post(
                    self.webhook_url, data=body_bytes, headers=headers, timeout=5
                )
                resp.raise_for_status()
                _log.info("generic webhook notification sent successfully")
            except Exception as e:
                _log.warning("failed to send generic webhook notification", error=str(e))

        t = threading.Thread(target=_send, name="webhook-send")
        t.start()
    def send(self, report: Dict[str, Any]) -> bool:
        envelope = ok_envelope(
            command=report.get("command", "notify"),
            payload=report,
        )
        self.notify(envelope)
        return True

    def notify_event(self, event: CHERENKOVEvent) -> None:
        envelope = ok_envelope(
            command=event.name,
            payload=event.to_dict(),
        )
        self.notify(envelope)
