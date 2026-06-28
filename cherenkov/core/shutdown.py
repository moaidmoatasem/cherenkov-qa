from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

_Handler = Callable[[], None] | Callable[[], Awaitable[None]]


class ShutdownManager:
    """Manages graceful shutdown via OS signal handlers.

    Supports both sync and async handlers. Async handlers are awaited
    via a background task when the event loop is running.

    Usage:
        manager = ShutdownManager()
        manager.on_shutdown(my_cleanup_fn)
        manager.register()
    """

    def __init__(self):
        self._shutdown_requested = False
        self._handlers: list[_Handler] = []

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    def register(self) -> None:
        signal.signal(signal.SIGINT, self._handle)
        signal.signal(signal.SIGTERM, self._handle)

    def on_shutdown(self, handler: _Handler) -> None:
        self._handlers.append(handler)

    def _handle(self, signum: int, _frame) -> None:
        if self._shutdown_requested:
            return
        self._shutdown_requested = True
        logger.info("shutdown signal received (%s), running %d handlers", signum, len(self._handlers))
        for handler in self._handlers:
            try:
                result = handler()
                if isinstance(result, Awaitable):
                    try:
                        loop = asyncio.get_running_loop()
                        _ = loop.create_task(result)  # noqa: RUF006 — intentionally fire-and-forget
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        loop.run_until_complete(result)
            except Exception as e:
                logger.error("shutdown handler failed: %s", e)
