from __future__ import annotations

import json
import time
from typing import Any, Callable

from cherenkov.core.errors import get_logger
from cherenkov.hitl.contracts import (
    HitlEnvelope,
    HitlItem,
    HitlStatus,
    err_envelope,
    ok_envelope,
    SCHEMA_VERSION,
)
from cherenkov.hitl.store import HitlQueue
from cherenkov.openclaw.contracts import OpenClawConfig, TriggerRequest

NotifyCallback = Callable[[HitlEnvelope], None]
TriggerCallback = Callable[[TriggerRequest], HitlEnvelope]


class OpenClawAdapter:
    """Tier-1 voice layer over the frozen hitl/v1 envelope.

    Wraps HitlQueue and adds:
    - Notification callbacks when items reach HITL or change status.
    - Run trigger commands for external re-run requests.
    - All responses use the frozen HitlEnvelope format.

    No direct DB access — delegates to HitlQueue. Defer CQRS healing + embeddings.
    """

    def __init__(
        self,
        queue: HitlQueue | None = None,
        config: OpenClawConfig | None = None,
    ) -> None:
        self._queue = queue or HitlQueue()
        self._config = config or OpenClawConfig()
        self._notify_callbacks: list[NotifyCallback] = []
        self._trigger_handlers: list[TriggerCallback] = []
        self._log = get_logger("OPENCLAW")
        self._last_poll: list[HitlItem] = []

    # ── notification registration ─────────────────────────────────────────

    def on_notify(self, callback: NotifyCallback) -> None:
        """Register a notification callback called when items change state."""
        self._notify_callbacks.append(callback)

    def on_trigger(self, handler: TriggerCallback) -> None:
        """Register a handler for run-trigger requests."""
        self._trigger_handlers.append(handler)

    def _notify(self, envelope: HitlEnvelope) -> None:
        for cb in self._notify_callbacks:
            try:
                cb(envelope)
            except Exception as exc:
                self._log.warning("notify callback failed", error=str(exc))

    # ── envelope operations ───────────────────────────────────────────────

    def list_envelope(self, status: str | None = "pending") -> HitlEnvelope:
        """List HITL items as a frozen hitl/v1 envelope."""
        try:
            items = self._queue.list(status=status)
            return ok_envelope("openclaw.list", {
                "status_filter": status,
                "count": len(items),
                "items": [i.model_dump() for i in items],
            })
        except Exception as exc:
            return err_envelope("openclaw.list", "invalid_input", str(exc))

    def show_envelope(self, item_id: str) -> HitlEnvelope:
        """Show a single HITL item as a frozen hitl/v1 envelope."""
        try:
            item = self._queue.get(item_id)
            if item is None:
                return err_envelope(
                    "openclaw.show", "not_found",
                    f"{item_id} not found.", {"id": item_id},
                )
            return ok_envelope("openclaw.show", {"id": item_id, "item": item.model_dump()})
        except Exception as exc:
            return err_envelope("openclaw.show", "invalid_input", str(exc))

    def approve_envelope(self, item_id: str, actor: str) -> HitlEnvelope:
        """Approve a pending HITL item. Returns envelope, notifies on success."""
        env = self._queue.approve(item_id=item_id, actor=actor, source="openclaw")
        if env.ok:
            notify_env = ok_envelope("openclaw.approve", env.payload)
            self._notify(notify_env)
        return env

    def reject_envelope(self, item_id: str, actor: str, reason: str) -> HitlEnvelope:
        """Reject a pending HITL item. Returns envelope, notifies on success."""
        env = self._queue.reject(item_id=item_id, actor=actor, reason=reason, source="openclaw")
        if env.ok:
            notify_env = ok_envelope("openclaw.reject", env.payload)
            self._notify(notify_env)
        return env

    def trigger_run(self, request: TriggerRequest) -> HitlEnvelope:
        """Trigger a re-run via registered handlers.

        If no handler is registered, returns an error envelope.
        """
        if not self._trigger_handlers:
            return err_envelope(
                "openclaw.trigger", "not_found",
                "No run-trigger handler registered. Defer to manual execution.",
                {"reason": request.reason},
            )
        last_env: HitlEnvelope = err_envelope(
            "openclaw.trigger", "invalid_input",
            "All trigger handlers returned errors.",
        )
        for handler in self._trigger_handlers:
            try:
                env = handler(request)
                last_env = env
                if env.ok:
                    self._notify(env)
                    return env
            except Exception as exc:
                last_env = err_envelope(
                    "openclaw.trigger", "invalid_input",
                    f"Trigger handler error: {exc}",
                )
        return last_env

    def poll_envelope(self) -> HitlEnvelope:
        """Poll for new pending items since last poll.

        Returns only items that are new since the last call.
        Useful for notification polling by voice layers that can't
        maintain a persistent connection.
        """
        current = self._queue.list(status="pending")
        current_ids = {item.id for item in current}
        seen_ids = {item.id for item in self._last_poll}
        new_items = [item for item in current if item.id not in seen_ids]
        self._last_poll = current
        return ok_envelope("openclaw.poll", {
            "new_count": len(new_items),
            "pending_count": len(current),
            "new_items": [i.model_dump() for i in new_items],
        })
