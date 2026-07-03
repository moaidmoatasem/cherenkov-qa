"""GitHub Webhook Consumer (CC-3)."""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

_log = logging.getLogger(__name__)

github_webhook_router = APIRouter(prefix="/api/v1/webhooks/github", tags=["webhooks"])


def _get_webhook_secret() -> str:
    from cherenkov.core.settings import get_settings
    return get_settings().GITHUB_WEBHOOK_SECRET


def verify_signature(payload_body: bytes, secret: str, signature_header: str) -> bool:
    if not signature_header or not secret:
        return False
    hash_object = hmac.new(secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)


@github_webhook_router.post("/events")
async def handle_github_event(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None)
) -> dict[str, Any]:
    """Handle incoming GitHub webhook events."""
    payload_body = await request.body()
    secret = _get_webhook_secret()

    if secret:
        # Secret is configured — enforce signature on every request.
        if not x_hub_signature_256 or not verify_signature(payload_body, secret, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid or missing webhook signature")
    else:
        _log.warning("CHERENKOV_GITHUB_WEBHOOK_SECRET is not set; webhook signature verification is disabled")

    payload = await request.json()
    _log.info("Received GitHub webhook event: %s", x_github_event)

    # Forward relevant events to the CHERENKOV event bus
    if x_github_event == "pull_request":
        action = payload.get("action")
        pr_number = payload.get("pull_request", {}).get("number")
        _log.info("PR %s action: %s", pr_number, action)
        # Here we would normally publish to `AsyncQueueEventBus`
        # bus.publish(CHERENKOVEvent(category="webhook", name="github.pr", data=payload))

    return {"status": "ok"}
