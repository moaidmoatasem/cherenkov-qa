from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable

from cherenkov.core.events import CHERENKOVEvent

logger = logging.getLogger(__name__)


class AsyncQueueEventBus:
    """In-process event bus using asyncio.Queue for dispatch.

    Supports both async and sync publish patterns.  In async contexts the
    dispatch loop runs as a background task; in sync contexts events are
    dispatched synchronously on publish().
    """

    def __init__(self, max_queue_size: int = 500):
        self._queue: asyncio.Queue[CHERENKOVEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._handlers: dict[str, list[Callable[[CHERENKOVEvent], None]]] = {}
        self._task: asyncio.Task | None = None
        self._running = False

    # ── EventBus protocol ─────────────────────────────────────────

    def publish(self, event: CHERENKOVEvent) -> None:
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("event bus queue full, dropping event: %s/%s", event.category.value, event.name)
            return

        # If we're in an async context, ensure the dispatch loop is running
        try:
            loop = asyncio.get_running_loop()
            if not self._running:
                self._start(loop)
        except RuntimeError:
            # No running loop — dispatch synchronously
            self._dispatch_sync(event)

    def subscribe(
        self, event_name: str, handler: Callable[[CHERENKOVEvent], None]
    ) -> None:
        self._handlers.setdefault(event_name, []).append(handler)

    def unsubscribe(
        self, event_name: str, handler: Callable[[CHERENKOVEvent], None]
    ) -> None:
        handlers = self._handlers.get(event_name, [])
        if handler in handlers:
            handlers.remove(handler)

    @property
    def handlers(self) -> dict[str, list[Callable[[CHERENKOVEvent], None]]]:
        return dict(self._handlers)

    # ── Lifecycle ─────────────────────────────────────────────────

    def _start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._running = True
        self._task = loop.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    # ── Dispatch ──────────────────────────────────────────────────

    async def _dispatch_loop(self) -> None:
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                self._dispatch_sync(event)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("event dispatch error")

    def _dispatch_sync(self, event: CHERENKOVEvent) -> None:
        matched = self._handlers.get(event.name, []) + self._handlers.get("*", [])
        for handler in matched:
            try:
                handler(event)
            except Exception:
                logger.exception("event handler failed for %s", event.name)
