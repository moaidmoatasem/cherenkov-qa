from __future__ import annotations

from typing import Any, Callable

from cherenkov.core.errors import get_logger
from cherenkov.core.contracts import ReasoningRequest
from cherenkov.substrate.router import route
from cherenkov.hitl.contracts import (
    HitlEnvelope,
    HitlItem,
    HitlStatus,
    err_envelope,
    ok_envelope,
)
from cherenkov.hitl.store import HitlQueue
from cherenkov.openclaw.contracts import (
    OpenClawConfig,
    TriggerRequest,
    ClassificationRequest,
)
from cherenkov.openclaw.feedback import HealingFeedbackStore

NotifyCallback = Callable[[HitlEnvelope], None]
TriggerCallback = Callable[[TriggerRequest], HitlEnvelope]


class OpenClawAdapter:
    """Tier-2 voice layer over the frozen hitl/v1 envelope.

    Wraps HitlQueue and adds:
    - Tier-1: Notification callbacks, run triggers, polling.
    - Tier-2 (#149): Chat identity mapping, pre-check, optimistic card lock, conflict UX.
    - Tier-2 (#150): Healing feedback classification loop with CQRS thresholds.
    - All responses use the frozen HitlEnvelope format.
    - No direct DB access — delegates to HitlQueue + HealingFeedbackStore.
    """

    def __init__(
        self,
        queue: HitlQueue | None = None,
        feedback_store: HealingFeedbackStore | None = None,
        config: OpenClawConfig | None = None,
    ) -> None:
        self._queue = queue or HitlQueue()
        self._feedback = feedback_store or HealingFeedbackStore()
        self._config = config or OpenClawConfig()
        self._notify_callbacks: list[NotifyCallback] = []
        self._trigger_handlers: list[TriggerCallback] = []
        self._log = get_logger("OPENCLAW")
        self._last_poll: list[HitlItem] = []
        # Tier-2: chat_user_id -> @cli_user identity map
        self._identity_map: dict[str, str] = {}

    # ── Tier-2: identity mapping (#149) ───────────────────────────────────

    def register_chat_user(self, chat_user_id: str, cli_user: str) -> None:
        """Map a chat user ID to a CLI actor name."""
        self._identity_map[chat_user_id] = cli_user
        self._log.info(
            "registered chat user", chat_user_id=chat_user_id, cli_user=cli_user
        )

    def _resolve_actor(self, chat_user_id: str) -> str | None:
        """Resolve chat user to CLI actor. Returns None if unmapped."""
        return self._identity_map.get(chat_user_id)

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

    # ── Tier-2: pre-check before mutation (#149) ──────────────────────────

    def _pre_check(self, item_id: str, chat_user_id: str | None) -> HitlEnvelope | None:
        """Pre-check item before mutating. Returns error envelope if blocked, None if OK."""
        if chat_user_id is not None and self._resolve_actor(chat_user_id) is None:
            return err_envelope(
                "openclaw.auth",
                "forbidden",
                f"Chat user '{chat_user_id}' is not mapped to a CLI user. "
                "Please register with /register.",
                {"chat_user_id": chat_user_id},
            )
        item = self._queue.get(item_id)
        if item is None:
            return err_envelope(
                "openclaw.show",
                "not_found",
                f"{item_id} not found.",
                {"id": item_id},
            )
        if item.status != HitlStatus.PENDING:
            return err_envelope(
                "openclaw.mutation",
                "conflict",
                f"{item_id} is no longer pending. Already {item.status.value} "
                f"by {item.approved_by}.",
                {
                    "current_status": item.status.value,
                    "current_actor": item.approved_by,
                    "current_actor_at": item.approved_at,
                },
            )
        return None

    # ── envelope operations ───────────────────────────────────────────────

    def list_envelope(self, status: str | None = "pending") -> HitlEnvelope:
        """List HITL items as a frozen hitl/v1 envelope."""
        try:
            items = self._queue.list(status=status)
            return ok_envelope(
                "openclaw.list",
                {
                    "status_filter": status,
                    "count": len(items),
                    "items": [i.model_dump() for i in items],
                },
            )
        except Exception as exc:
            return err_envelope("openclaw.list", "invalid_input", str(exc))

    def show_envelope(self, item_id: str) -> HitlEnvelope:
        """Show a single HITL item as a frozen hitl/v1 envelope."""
        try:
            item = self._queue.get(item_id)
            if item is None:
                return err_envelope(
                    "openclaw.show",
                    "not_found",
                    f"{item_id} not found.",
                    {"id": item_id},
                )
            return ok_envelope(
                "openclaw.show", {"id": item_id, "item": item.model_dump()}
            )
        except Exception as exc:
            return err_envelope("openclaw.show", "invalid_input", str(exc))

    def approve_envelope(
        self, item_id: str, actor: str, chat_user_id: str | None = None
    ) -> HitlEnvelope:
        """Approve a pending HITL item. Tier-2: supports chat identity resolution.

        Returns envelope, notifies on success. Unmapped chat users are refused.
        """
        block = self._pre_check(item_id, chat_user_id)
        if block is not None:
            return block
        resolved = self._resolve_actor(chat_user_id) if chat_user_id else actor
        env = self._queue.approve(item_id=item_id, actor=resolved, source="openclaw")
        if env.ok:
            notify_env = ok_envelope("openclaw.approve", env.payload)
            self._notify(notify_env)
        return env

    def reject_envelope(
        self, item_id: str, actor: str, reason: str, chat_user_id: str | None = None
    ) -> HitlEnvelope:
        """Reject a pending HITL item. Tier-2: supports chat identity resolution.

        Returns envelope, notifies on success. Unmapped chat users are refused.
        """
        block = self._pre_check(item_id, chat_user_id)
        if block is not None:
            return block
        resolved = self._resolve_actor(chat_user_id) if chat_user_id else actor
        env = self._queue.reject(
            item_id=item_id, actor=resolved, reason=reason, source="openclaw"
        )
        if env.ok:
            notify_env = ok_envelope("openclaw.reject", env.payload)
            self._notify(notify_env)
        return env

    # ── Tier-2: optimistic card lock (#149) ───────────────────────────────

    def lock_envelope(self, item_id: str, chat_user_id: str) -> HitlEnvelope:
        """Optimistically lock an item as 'reviewing by @user'.

        Prevents two chat users from reviewing the same item simultaneously.
        Best-effort: if the item is already resolved, returns conflict.
        """
        resolved = self._resolve_actor(chat_user_id)
        if resolved is None:
            return err_envelope(
                "openclaw.auth",
                "forbidden",
                f"Chat user '{chat_user_id}' is not mapped.",
                {"chat_user_id": chat_user_id},
            )
        item = self._queue.get(item_id)
        if item is None:
            return err_envelope(
                "openclaw.lock", "not_found", f"{item_id} not found.", {"id": item_id}
            )
        if item.status != HitlStatus.PENDING:
            return err_envelope(
                "openclaw.lock",
                "conflict",
                f"{item_id} is already {item.status.value} by {item.approved_by}.",
                {
                    "current_status": item.status.value,
                    "current_actor": item.approved_by,
                },
            )
        lock = self._queue.optimistic_lock(item_id=item_id, reviewer=resolved)
        if not lock:
            return err_envelope(
                "openclaw.lock",
                "conflict",
                f"{item_id} is already being reviewed.",
                {"id": item_id},
            )
        return ok_envelope(
            "openclaw.lock",
            {
                "id": item_id,
                "reviewer": resolved,
                "action": "lock",
            },
        )

    def trigger_run(self, request: TriggerRequest) -> HitlEnvelope:
        """Trigger a re-run via registered handlers.

        If no handler is registered, returns an error envelope.
        """
        if not self._trigger_handlers:
            return err_envelope(
                "openclaw.trigger",
                "not_found",
                "No run-trigger handler registered. Defer to manual execution.",
                {"reason": request.reason},
            )
        last_env: HitlEnvelope = err_envelope(
            "openclaw.trigger",
            "invalid_input",
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
                    "openclaw.trigger",
                    "invalid_input",
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
        return ok_envelope(
            "openclaw.poll",
            {
                "new_count": len(new_items),
                "pending_count": len(current),
                "new_items": [i.model_dump() for i in new_items],
            },
        )

    # ── Tier-2: healing feedback classification (#150) ────────────────────

    def classify_envelope(self, request: ClassificationRequest) -> HitlEnvelope:
        """Classify a HITL item as regression, intended, or ignore.

        Writes to the append-only healing_feedback_log and recomputes thresholds.
        Suggestions surface only at confidence >= 0.70 AND count >= 3.
        """
        item = self._queue.get(request.item_id)
        if item is None:
            return err_envelope(
                "openclaw.classify",
                "not_found",
                f"{request.item_id} not found.",
                {"id": request.item_id},
            )

        try:
            self._feedback.record_feedback(
                item_id=request.item_id,
                endpoint=item.endpoint or "",
                mutation_id=item.mutation_id or "",
                classification=request.classification,
                actor=request.actor,
                detail=request.detail,
            )
        except Exception as exc:
            return err_envelope(
                "openclaw.classify", "invalid_input", f"Feedback record failed: {exc}"
            )

        thresholds = self._feedback.compute_thresholds(
            endpoint=item.endpoint or "",
            mutation_id=item.mutation_id or "",
        )

        suggestion: dict[str, Any] | None = None
        if thresholds["count"] >= 3 and thresholds["confidence"] >= 0.70:
            classification = thresholds["dominant_classification"]
            suggestion = {
                "classification": classification,
                "confidence": thresholds["confidence"],
                "count": thresholds["count"],
                "label": "Suggest auto-handling"
                if classification == "ignore"
                else "Likely intended drift"
                if classification == "intended"
                else "Regression - flag for review",
            }

        return ok_envelope(
            "openclaw.classify",
            {
                "item_id": request.item_id,
                "recorded_classification": request.classification,
                "thresholds": thresholds,
                "suggestion": suggestion,
            },
        )

    def suggestion_envelope(self, endpoint: str, mutation_id: str) -> HitlEnvelope:
        """Get the current suggestion threshold for an endpoint+mutation pair."""
        try:
            thresholds = self._feedback.compute_thresholds(
                endpoint=endpoint, mutation_id=mutation_id
            )
        except Exception as exc:
            return err_envelope("openclaw.suggestion", "invalid_input", str(exc))

        return ok_envelope(
            "openclaw.suggestion",
            {
                "endpoint": endpoint,
                "mutation_id": mutation_id,
                "thresholds": thresholds,
            },
        )

    def explain_envelope(self, item_id: str) -> HitlEnvelope:
        """Get an AI explanation for why the test failed, without recommending action."""
        item = self._queue.get(item_id)
        if item is None:
            return err_envelope(
                "openclaw.explain",
                "not_found",
                f"{item_id} not found.",
                {"id": item_id},
            )

        try:
            thresholds = self._feedback.compute_thresholds(
                item.endpoint or "", item.mutation_id or ""
            )
        except Exception:
            thresholds = {}

        xml_context = (
            f"<item_id>{item.id}</item_id>\n"
            f"<endpoint>{item.endpoint or ''}</endpoint>\n"
            f"<method>{item.method or ''}</method>\n"
            f"<mutation_id>{item.mutation_id or ''}</mutation_id>\n"
            f"<review_gate_failed>{item.review_gate_failed or ''}</review_gate_failed>\n"
            f"<confidence>{item.confidence or ''}</confidence>\n"
            f"<dominant_classification>{thresholds.get('dominant_classification') or ''}</dominant_classification>\n"
            f"<historical_votes_count>{thresholds.get('count') or 0}</historical_votes_count>\n"
        )

        prompt = (
            "You are an expert failure triage AI. Explain why this API conformance test was flagged for human review "
            "based strictly on the metadata parameters provided below. Do NOT recommend approval/rejection and do NOT suggest code fixes.\n\n"
            f"Context:\n{xml_context}\n"
            "Format your explanation clearly and prefix it with [AI 🤖]."
        )

        req = ReasoningRequest(task=prompt, capability_tier="small")

        try:
            res = route(req)
            explanation = str(res.content).strip()
            if not explanation.startswith("[AI 🤖]"):
                explanation = f"[AI 🤖] {explanation}"
            return ok_envelope(
                "openclaw.explain", {"id": item_id, "explanation": explanation}
            )
        except Exception as exc:
            return err_envelope(
                "openclaw.explain",
                "llm_unavailable",
                f"Offline path: Local model is down or unreachable. Error: {str(exc)}",
            )
