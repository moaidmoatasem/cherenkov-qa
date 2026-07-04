from unittest.mock import patch

from cherenkov.core.events import CHERENKOVEvent, EventCategory, EventSeverity
from cherenkov.events.mcp_bridge import handle_event_for_mcp


def _event(severity: EventSeverity = EventSeverity.INFO) -> CHERENKOVEvent:
    return CHERENKOVEvent(
        category=EventCategory.PIPELINE,
        name="pipeline.start",
        payload={"run_id": "abc"},
        severity=severity,
    )


def test_forwards_event_as_mcp_notification():
    with patch("cherenkov.events.mcp_bridge.send_notification") as send:
        handle_event_for_mcp(_event())
    send.assert_called_once()
    method, params = send.call_args[0]
    assert method == "cherenkov/event"
    assert params["event"]["name"] == "pipeline.start"
    assert params["event"]["category"] == "pipeline"
    assert params["event"]["payload"] == {"run_id": "abc"}


def test_error_severity_also_maps_to_mcp_log_message():
    with patch("cherenkov.events.mcp_bridge.send_notification") as send:
        handle_event_for_mcp(_event(severity=EventSeverity.ERROR))
    methods = [call.args[0] for call in send.call_args_list]
    assert methods == ["cherenkov/event", "notifications/message"]
    log_params = send.call_args_list[1].args[1]
    assert log_params["level"] == "error"


def test_bridge_never_raises_on_send_failure():
    with patch(
        "cherenkov.events.mcp_bridge.send_notification",
        side_effect=RuntimeError("mcp transport down"),
    ):
        handle_event_for_mcp(_event())  # must swallow, not raise
