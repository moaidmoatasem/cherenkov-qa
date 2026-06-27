from __future__ import annotations

import logging
import signal
from collections.abc import Callable

logger = logging.getLogger(__name__)


class ShutdownManager:
    """Manages graceful shutdown via OS signal handlers.

    Usage:
        manager = ShutdownManager()
        manager.on_shutdown(my_cleanup_fn)
        manager.register()
    """

    def __init__(self):
        self._shutdown_requested = False
        self._handlers: list[Callable[[], None]] = []

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    def register(self) -> None:
        signal.signal(signal.SIGINT, self._handle)
        signal.signal(signal.SIGTERM, self._handle)

    def on_shutdown(self, handler: Callable[[], None]) -> None:
        self._handlers.append(handler)

    def _handle(self, signum: int, _frame) -> None:
        if self._shutdown_requested:
            return
        self._shutdown_requested = True
        logger.info("shutdown signal received (%s), running %d handlers", signum, len(self._handlers))
        for handler in self._handlers:
            try:
                handler()
            except Exception as e:
                logger.error("shutdown handler failed: %s", e)
