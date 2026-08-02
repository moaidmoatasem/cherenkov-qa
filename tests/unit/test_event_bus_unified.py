import tempfile
from pathlib import Path

import pytest

from cherenkov.core.events import CHERENKOVEvent, EventCategory, EventSeverity
import cherenkov.events as ev
from cherenkov.events import (
    CompositeEventFilter,
    FileEventSink,
    JsonEventSource,
    LogEventSink,
    UnifiedEventBus,
    get_event_bus,
    publish_event,
    set_event_bus,
    subscribe_to_event,
)


@pytest.fixture
def fresh_bus():
    bus = UnifiedEventBus()
    set_event_bus(bus)
    yield bus
    set_event_bus(None)


def test_sync_publish_dispatches_immediately(fresh_bus):
    received = []
    fresh_bus.subscribe("pipeline.start", lambda e: received.append(e))
    fresh_bus.publish(CHERENKOVEvent.pipeline_start(run_id="r1", scenarios=2))
    assert len(received) == 1
    assert received[0].name == "pipeline.start"
    assert received[0].payload["run_id"] == "r1"


def test_wildcard_subscriber(fresh_bus):
    received = []
    fresh_bus.subscribe("*", lambda e: received.append(e.name))
    fresh_bus.publish(CHERENKOVEvent.pipeline_start(run_id="r1"))
    fresh_bus.publish(CHERENKOVEvent.pipeline_complete(run_id="r1", success=True))
    assert received == ["pipeline.start", "pipeline.complete"]


def test_unsubscribe(fresh_bus):
    received = []
    handler = lambda e: received.append(e)  # noqa: E731
    fresh_bus.subscribe("pipeline.start", handler)
    fresh_bus.publish(CHERENKOVEvent.pipeline_start(run_id="r1"))
    fresh_bus.unsubscribe("pipeline.start", handler)
    fresh_bus.publish(CHERENKOVEvent.pipeline_start(run_id="r2"))
    assert len(received) == 1


def test_handler_exception_is_swallowed(fresh_bus):
    def bad(e):
        raise RuntimeError("boom")

    fresh_bus.subscribe("pipeline.start", bad)
    # must not raise
    fresh_bus.publish(CHERENKOVEvent.pipeline_start(run_id="r1"))


def test_file_sink_and_source(fresh_bus):
    path = Path(tempfile.mkdtemp()) / "events.jsonl"
    sink = FileEventSink(str(path))
    source = JsonEventSource(str(path))
    fresh_bus.add_sink(sink)
    fresh_bus.add_source(source)
    fresh_bus.publish(CHERENKOVEvent.pipeline_start(run_id="r1"))
    fresh_bus.publish(CHERENKOVEvent.pipeline_complete(run_id="r1", success=True))
    fetched = source.fetch_events()
    assert len(fetched) == 2
    assert fetched[0].name == "pipeline.start"
    by_id = source.get_event(fetched[1].event_id)
    assert by_id is not None
    sink.close()


def test_composite_filter(fresh_bus):
    received = []
    fresh_bus.add_filter(CompositeEventFilter(name_pattern="pipeline.", severity_filter=lambda s: s == EventSeverity.WARNING))
    fresh_bus.subscribe("*", lambda e: received.append(e))
    fresh_bus.publish(CHERENKOVEvent.pipeline_start(run_id="r1"))  # INFO -> filtered out
    fresh_bus.publish(CHERENKOVEvent.pipeline_complete(run_id="r1", success=False))  # WARNING -> passes
    assert len(received) == 1
    assert received[0].name == "pipeline.complete"


def test_global_helpers(fresh_bus):
    received = []
    subscribe_to_event("chat.message", lambda e: received.append(e))
    publish_event(CHERENKOVEvent(category=EventCategory.CHAT, name="chat.message", payload={"m": "hi"}))
    assert len(received) == 1
    assert received[0].payload["m"] == "hi"
    assert get_event_bus() is fresh_bus


def test_stats(fresh_bus):
    stats = fresh_bus.get_stats()
    assert stats["name"] == "unified_bus"
    assert "queue_size" in stats
    assert "handlers_count" in stats


def test_log_sink_emit_and_close():
    sink = LogEventSink("test_event_bus_log")
    sink.emit(CHERENKOVEvent(category=EventCategory.SYSTEM, name="x"))
    sink.close()
