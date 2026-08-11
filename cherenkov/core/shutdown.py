"""
cherenkov/core/shutdown.py — Graceful shutdown manager and OS signal handling.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

_Handler = Callable[[], None] | Callable[[], Awaitable[None]]
_background_tasks: set[asyncio.Task] = set()


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
        """Initialize ShutdownManager instance."""
        self._shutdown_requested = False
        self._handlers: list[_Handler] = []

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown has been requested by signal handler.

        Returns:
            bool: True if shutdown is requested, False otherwise.
        """
        return self._shutdown_requested

    def register(self) -> None:
        """Register SIGINT and SIGTERM OS signal handlers.

        Returns:
            None
        """
        signal.signal(signal.SIGINT, self._handle)
        signal.signal(signal.SIGTERM, self._handle)

    def on_shutdown(self, handler: _Handler) -> None:
        """Register a sync or async cleanup callback handler.

        Args:
            handler (_Handler): Sync or async callback function.

        Returns:
            None
        """
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
                        task = asyncio.ensure_future(result, loop=loop)
                        _background_tasks.add(task)
                        task.add_done_callback(_background_tasks.discard)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        loop.run_until_complete(result)
            except Exception as e:
                logger.error("shutdown handler failed: %s", e)

