"""
CHERENKOV openclaw/ — Tier-1 voice layer over the frozen hitl/v1 envelope.

Notifications + run triggers only. No DB access. Consumes the HITL queue
via HitlEnvelope and provides HTTP API endpoints for external voice layers
(dashboard, webhooks, Slack bots) to interact with the review queue.
"""
from cherenkov.openclaw.adapter import OpenClawAdapter, TriggerRequest
from cherenkov.openclaw.contracts import OpenClawConfig

__all__ = ["OpenClawAdapter", "TriggerRequest", "OpenClawConfig"]
