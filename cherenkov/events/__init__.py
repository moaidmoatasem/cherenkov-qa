"""
Unified Event Bus (ADR-016) — Consolidate multiple event systems.

Replaces:
  1. AsyncQueueEventBus (cherenkov/events/bus.py)
  2. Event sourcing & logging in core/orchestrator.py
  3. CHERENKOVEvent domain events (core/events.py)
  4. Event bridges (knowledge/bridges/*, reflector/*)
  5. Event callback pattern in orchestrator

Features:
- AsyncQueueEventBus as primary implementation with async dispatch
- EventSink abstraction for logging/file output
- EventSource abstraction for event history
- Integration with existing components via adapters
- Config-driven event routing and filtering
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from cherenkov.core.events import CHERENKOVEvent, EventCategory, EventSeverity

logger = logging.getLogger(__name__)

# Number of published events retained in memory for fetch_events/get_event
# when no external EventSource has been registered.
MAX_RETAINED_EVENTS = 2000

# ─── Event System Abstractions ────────────────────────────────────────────────

class EventSink(ABC):
    """Abstract sink for event delivery (log, file, webhook, etc.)."""

    @abstractmethod
    def emit(self, event: CHERENKOVEvent) -> None:
        """Process an event.

        Args:
            event (CHERENKOVEvent): Event object to emit.

        Returns:
            None
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up resources.

        Returns:
            None
        """
        pass


class EventSource(ABC):
    """Abstract source for event retrieval."""

    @abstractmethod
    def fetch_events(
        self, after_id: str | None = None, limit: int = 100, category: str | None = None
    ) -> list[CHERENKOVEvent]:
        """Retrieve events from source.

        Args:
            after_id (str | None, optional): Event ID after which to fetch events. Defaults to None.
            limit (int, optional): Maximum number of events to fetch. Defaults to 100.
            category (str | None, optional): Category filter string. Defaults to None.

        Returns:
            list[CHERENKOVEvent]: List of fetched events matching criteria.
        """
        pass

    @abstractmethod
    def get_event(self, event_id: str) -> CHERENKOVEvent | None:
        """Get a specific event by ID.

        Args:
            event_id (str): Unique event identifier.

        Returns:
            CHERENKOVEvent | None: Event matching event_id, or None if not found.
        """
        pass


class EventFilter(ABC):
    """Abstract filter for event routing."""

    @abstractmethod
    def should_handle(self, event: CHERENKOVEvent) -> bool:
        """Check if filter matches event.

        Args:
            event (CHERENKOVEvent): Event to check.

        Returns:
            bool: True if filter matches event, False otherwise.
        """
        pass

    @abstractmethod
    def get_handler(self, event: CHERENKOVEvent) -> Callable[[CHERENKOVEvent], Any] | None:
        """Get handler for event.

        Args:
            event (CHERENKOVEvent): Event object to get handler for.

        Returns:
            Callable[[CHERENKOVEvent], Any] | None: Callable handler for event, or None.
        """
        pass


# ─── Concrete Implementations ─────────────────────────────────────────────────

class LogEventSink(EventSink):
    """Event sink that logs to structured logger."""

    def __init__(self, logger_name: str = "event_bus"):
        """Initialize log event sink.

        Args:
            logger_name (str, optional): Name of logger instance. Defaults to "event_bus".
        """
        self.logger = logging.getLogger(logger_name)

    def emit(self, event: CHERENKOVEvent) -> None:
        """Log event with structured format.

        Args:
            event (CHERENKOVEvent): Event to write to structured logger.

        Returns:
            None
        """
        self.logger.info(
            "Event: %s/%s - %s - %s",
            event.category.value,
            event.name,
            event.severity.value,
            json.dumps(event.payload, default=str),
        )

    def close(self) -> None:
        """Close sink - nothing to clean up for logging.

        Returns:
            None
        """
        pass


class FileEventSink(EventSink):
    """Event sink that writes to JSONL file."""

    def __init__(self, file_path: str):
        """Initialize file event sink.

        Args:
            file_path (str): Target path for JSONL output file.
        """
        self.file_path = file_path
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        import os

        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def emit(self, event: CHERENKOVEvent) -> None:
        """Write event to JSONL file.

        Args:
            event (CHERENKOVEvent): Event to append to file.

        Returns:
            None
        """
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                json.dump(event.to_dict(), f)
                f.write("\n")
        except Exception as e:
            logger.error("Failed to write event to file %s: %s", self.file_path, e)

    def close(self) -> None:
        """Close sink - nothing to clean up.

        Returns:
            None
        """
        pass


class JsonEventSource(EventSource):
    """Event source that reads from JSONL file."""

    def __init__(self, file_path: str):
        """Initialize JSON event source.

        Args:
            file_path (str): Path to JSONL event file.
        """
        self.file_path = file_path

    def fetch_events(
        self, after_id: str | None = None, limit: int = 100, category: str | None = None
    ) -> list[CHERENKOVEvent]:
        """Fetch events from file.

        Args:
            after_id (str | None, optional): Event ID filter boundary. Defaults to None.
            limit (int, optional): Maximum number of events to fetch. Defaults to 100.
            category (str | None, optional): Category filter string. Defaults to None.

        Returns:
            list[CHERENKOVEvent]: List of events read from JSONL file.
        """
        events = []
        try:
            with open(self.file_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    event_dict = json.loads(line)
                    event = CHERENKOVEvent(**event_dict)

                    if after_id and event.event_id <= after_id:
                        continue

                    if category and event.category.value != category:
                        continue

                    events.append(event)

                    if len(events) >= limit:
                        break
        except FileNotFoundError:
            logger.warning("Event file not found: %s", self.file_path)
        except Exception as e:
            logger.error("Failed to read events from file %s: %s", self.file_path, e)

        return events

    def get_event(self, event_id: str) -> CHERENKOVEvent | None:
        """Get specific event by ID.

        Args:
            event_id (str): Unique event ID.

        Returns:
            CHERENKOVEvent | None: Event matching event_id, or None if not found.
        """
        events = self.fetch_events()
        for event in events:
            if event.event_id == event_id:
                return event
        return None


class CompositeEventFilter(EventFilter):
    """Composite filter for event routing."""

    def __init__(
        self,
        category_filter: Callable[[EventCategory], bool] | None = None,
        name_pattern: str | None = None,
        severity_filter: Callable[[EventSeverity], bool] | None = None,
        payload_contains: dict[str, Any] | None = None,
        custom_filter: Callable[[CHERENKOVEvent], bool] | None = None,
    ):
        """Initialize composite event filter.

        Args:
            category_filter (Callable | None, optional): Category predicate. Defaults to None.
            name_pattern (str | None, optional): Name substring pattern. Defaults to None.
            severity_filter (Callable | None, optional): Severity predicate. Defaults to None.
            payload_contains (dict | None, optional): Key-value payload matching dict. Defaults to None.
            custom_filter (Callable | None, optional): Custom predicate function. Defaults to None.
        """
        self.category_filter = category_filter
        self.name_pattern = name_pattern
        self.severity_filter = severity_filter
        self.payload_contains = payload_contains
        self.custom_filter = custom_filter

    def should_handle(self, event: CHERENKOVEvent) -> bool:
        """Check if event matches all filters.

        Args:
            event (CHERENKOVEvent): Event to evaluate.

        Returns:
            bool: True if event matches all filter conditions, False otherwise.
        """
        if self.category_filter and not self.category_filter(event.category):
            return False

        if self.name_pattern and self.name_pattern not in event.name:
            return False

        if self.severity_filter and not self.severity_filter(event.severity):
            return False

        if self.payload_contains:
            for key, expected_value in self.payload_contains.items():
                if key not in event.payload or event.payload[key] != expected_value:
                    return False

        return not (self.custom_filter and not self.custom_filter(event))

    def get_handler(
        self, _event: CHERENKOVEvent
    ) -> Callable[[CHERENKOVEvent], Any] | None:
        """Get handler for event (returns None for CompositeEventFilter).

        Args:
            _event (CHERENKOVEvent): Event object.

        Returns:
            Callable[[CHERENKOVEvent], Any] | None: Always returns None for composite filter.
        """
        return None


# ─── AsyncQueueEventBus Replacement ────────────────────────────────────────────

class UnifiedEventBus:
    """Unified event bus with async dispatch and multiple sinks/sources."""

    def __init__(
        self,
        name: str = "unified_bus",
        max_queue_size: int = 500,
        dispatch_interval: float = 1.0,
    ):
        """Initialize unified event bus.

        Args:
            name (str, optional): Name identifier for bus. Defaults to "unified_bus".
            max_queue_size (int, optional): Maximum capacity of internal queue. Defaults to 500.
            dispatch_interval (float, optional): Poll interval in seconds for dispatch loop. Defaults to 1.0.
        """
        self.name = name
        self._queue: asyncio.Queue[CHERENKOVEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._filters: list[EventFilter] = []
        self._sinks: list[EventSink] = []
        self._sources: list[EventSource] = []
        self._handlers: dict[str, list[Callable[[CHERENKOVEvent], Any]]] = {}
        self._task: asyncio.Task | None = None
        self._running = False
        self._dispatch_interval = dispatch_interval
        self._local = threading.local()
        self._published: deque[CHERENKOVEvent] = deque(maxlen=MAX_RETAINED_EVENTS)

    # EventBus protocol (backwards compatibility)

    def publish(self, event: CHERENKOVEvent) -> None:
        """Publish event to bus.

        Args:
            event (CHERENKOVEvent): Event to publish.

        Returns:
            None
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - dispatch synchronously
            self._dispatch_sync(event)
            return

        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("event bus queue full, dropping event: %s/%s", event.category.value, event.name)
            return

        if not self._running:
            self._start(loop)

    def subscribe(
        self, event_name: str, handler: Callable[[CHERENKOVEvent], Any]
    ) -> None:
        """Subscribe to event by name.

        Args:
            event_name (str): Target event name or wildcard '*'.
            handler (Callable[[CHERENKOVEvent], Any]): Callback function to invoke.

        Returns:
            None
        """
        self._handlers.setdefault(event_name, []).append(handler)

    def unsubscribe(
        self, event_name: str, handler: Callable[[CHERENKOVEvent], Any]
    ) -> None:
        """Unsubscribe from event by name.

        Args:
            event_name (str): Target event name.
            handler (Callable[[CHERENKOVEvent], Any]): Callback function to remove.

        Returns:
            None
        """
        handlers = self._handlers.get(event_name, [])
        if handler in handlers:
            handlers.remove(handler)

    # Event system extensions

    def add_sink(self, sink: EventSink) -> None:
        """Add event sink.

        Args:
            sink (EventSink): EventSink instance to register.

        Returns:
            None
        """
        self._sinks.append(sink)

    def add_source(self, source: EventSource) -> None:
        """Add event source.

        Args:
            source (EventSource): EventSource instance to register.

        Returns:
            None
        """
        self._sources.append(source)

    def add_filter(self, filter: EventFilter) -> None:
        """Add event filter.

        Args:
            filter (EventFilter): EventFilter instance to register.

        Returns:
            None
        """
        self._filters.append(filter)

    # Lifecycle

    async def start(self) -> None:
        """Start event bus dispatch loop.

        Returns:
            None
        """
        if not self._running:
            self._running = True
            self._start(asyncio.get_running_loop())

    async def stop(self) -> None:
        """Stop event bus dispatch.

        Returns:
            None
        """
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    def close(self) -> None:
        """Close all sinks and sources.

        Returns:
            None
        """
        for sink in self._sinks:
            sink.close()

    # Internal dispatch

    def _start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._running = True
        self._task = loop.create_task(self._dispatch_loop())

    async def _dispatch_loop(self) -> None:
        """Main dispatch loop."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=self._dispatch_interval)
                self._dispatch(event)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("event dispatch error")

    def _dispatch_sync(self, event: CHERENKOVEvent) -> None:
        """Dispatch event synchronously (for sync contexts)."""
        self._dispatch(event)

    def _dispatch(self, event: CHERENKOVEvent) -> None:
        """Dispatch event to all sinks, sources, and handlers."""
        try:
            # Check all filters
            for filter_obj in self._filters:
                if not filter_obj.should_handle(event):
                    return

            # Handle via handlers (backwards compatibility)
            matched_handlers = self._handlers.get(event.name, []) + (self._handlers.get("*") or [])
            for handler in matched_handlers:
                try:
                    handler(event)
                except Exception:
                    logger.exception("event handler failed for %s", event.name)

            # Send to sinks
            for sink in self._sinks:
                try:
                    sink.emit(event)
                except Exception:
                    logger.exception("event sink failed for %s", event.name)

            # Store in sources (for write sources)
            for source in self._sources:
                try:
                    if hasattr(source, "store_event"):
                        source.store_event(event)
                except Exception:
                    logger.exception("event source failed for %s", event.name)

            # Retain in-memory so fetch_events/get_event work without a source
            self._published.append(event)

        except Exception:
            logger.exception("event dispatch error for %s", event.name)

    # Event system API

    def fetch_events(
        self, after_id: str | None = None, limit: int = 100, category: str | None = None
    ) -> list[CHERENKOVEvent]:
        """Fetch events from in-memory retention, then from all sources.

        Args:
            after_id (str | None, optional): Event ID filter boundary. Defaults to None.
            limit (int, optional): Maximum number of events to fetch. Defaults to 100.
            category (str | None, optional): Category filter string. Defaults to None.

        Returns:
            list[CHERENKOVEvent]: Combined list of matching events.
        """
        all_events: list[CHERENKOVEvent] = []
        for event in self._published:
            if after_id and event.event_id <= after_id:
                continue
            if category and event.category.value != category:
                continue
            all_events.append(event)
            if len(all_events) >= limit:
                break
        seen_ids = {e.event_id for e in all_events}
        for source in self._sources:
            events = source.fetch_events(after_id, limit, category)
            for event in events:
                if event.event_id not in seen_ids:
                    all_events.append(event)
                    seen_ids.add(event.event_id)
        return all_events[:limit]

    def get_event(self, event_id: str) -> CHERENKOVEvent | None:
        """Get event by ID from in-memory retention or sources.

        Args:
            event_id (str): Unique event ID to locate.

        Returns:
            CHERENKOVEvent | None: Matching event object, or None if not found.
        """
        for event in self._published:
            if event.event_id == event_id:
                return event
        for source in self._sources:
            event = source.get_event(event_id)
            if event:
                return event
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics.

        Returns:
            dict[str, Any]: Dictionary containing event bus performance metrics.
        """
        return {
            "name": self.name,
            "queue_size": self._queue.qsize(),
            "running": self._running,
            "sinks_count": len(self._sinks),
            "sources_count": len(self._sources),
            "filters_count": len(self._filters),
            "handlers_count": sum(len(handlers) for handlers in self._handlers.values()),
        }


# ─── Global Event Bus Instance ───────────────────────────────────────────────

_global_bus: UnifiedEventBus | None = None


def get_event_bus() -> UnifiedEventBus:
    """Get or create the global event bus instance.

    Returns:
        UnifiedEventBus: Global event bus singleton instance.
    """
    global _global_bus
    if _global_bus is None:
        _global_bus = UnifiedEventBus()
    return _global_bus


def set_event_bus(bus: UnifiedEventBus) -> None:
    """Set the global event bus instance.

    Args:
        bus (UnifiedEventBus): Global event bus instance to set.

    Returns:
        None
    """
    global _global_bus
    _global_bus = bus


# ─── Backwards Compatibility Helpers ─────────────────────────────────────────


def publish_event(event: CHERENKOVEvent) -> None:
    """Backwards compatible event publish function.

    Args:
        event (CHERENKOVEvent): Event to publish to global bus.

    Returns:
        None
    """
    get_event_bus().publish(event)


def subscribe_to_event(event_name: str, handler: Callable[[CHERENKOVEvent], Any]) -> None:
    """Backwards compatible event subscribe function.

    Args:
        event_name (str): Event name to subscribe to.
        handler (Callable[[CHERENKOVEvent], Any]): Callback function.

    Returns:
        None
    """
    get_event_bus().subscribe(event_name, handler)


_bus_control_task: asyncio.Task | None = None


def start_event_bus() -> None:
    """Start the global event bus.

    Returns:
        None
    """
    global _bus_control_task

    import asyncio

    bus = get_event_bus()
    _bus_control_task = asyncio.create_task(bus.start())


def stop_event_bus() -> None:
    """Stop the global event bus.

    Returns:
        None
    """
    global _bus_control_task

    import asyncio

    bus = get_event_bus()
    _bus_control_task = asyncio.create_task(bus.stop())
