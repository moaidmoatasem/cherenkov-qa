"""GitHub Webhook Consumer (CC-3)."""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

_log = logging.getLogger(__name__)

github_webhook_router = APIRouter(prefix="/webhooks/github", tags=["webhooks"])

# Assuming standard CHERENKOV secret setup
GITHUB_SECRET = "placeholder-secret-change-me"


def verify_signature(payload_body: bytes, secret: str, signature_header: str) -> bool:
    if not signature_header:
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

    if not verify_signature(payload_body, GITHUB_SECRET, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    _log.info(f"Received GitHub webhook event: {x_github_event}")

    # Forward relevant events to the CHERENKOV event bus
    if x_github_event == "pull_request":
        action = payload.get("action")
        pr_number = payload.get("pull_request", {}).get("number")
        _log.info(f"PR {pr_number} action: {action}")
        # Here we would normally publish to `AsyncQueueEventBus`
        # bus.publish(CHERENKOVEvent(category="webhook", name="github.pr", data=payload))

    return {"status": "ok"}
