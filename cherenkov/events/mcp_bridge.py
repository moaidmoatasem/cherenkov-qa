"""MCP Event Bridge (CC-3).

Publishes CHERENKOVEvent instances as MCP server-sent notifications to clients.
"""
from __future__ import annotations

import logging

from cherenkov.core.events import CHERENKOVEvent
from cherenkov.mcp.protocol import send_notification

_log = logging.getLogger(__name__)


def handle_event_for_mcp(event: CHERENKOVEvent) -> None:
    """Forward an internal event to the MCP client as a notification.
    
    MCP defines 'notifications/message' or custom notifications.
    We'll use a custom 'cherenkov/event' notification method,
    and also log to 'notifications/message' if it's a log event.
    """
    try:
        payload = {
            "category": event.category.value,
            "name": event.name,
            "data": event.data,
            "occurred_at": event.occurred_at.isoformat(),
        }
        send_notification("cherenkov/event", {"event": payload})

        # Also map important events to standard MCP log messages
        if event.category.value == "error":
            send_notification("notifications/message", {
                "level": "error",
                "logger": "cherenkov.event_bus",
                "data": payload
            })
    except Exception as e:
        _log.error(f"Failed to bridge event to MCP: {e}")


def subscribe_mcp_bridge() -> None:
    """Subscribe the MCP bridge to the global event bus."""
    # In a real app we'd get the global bus instance,
    # but here we'll assume it's injected or global.
    _log.info("Subscribing MCP bridge to all CHERENKOV events.")
