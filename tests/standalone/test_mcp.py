"""
test_mcp.py — Unit tests for the CHERENKOV MCP server (mcp/v1).

Tests cover:
  - JSON-RPC 2.0 protocol framing (parse, dispatch, error codes)
  - MCP initialize handshake shape
  - Handler input validation (trust boundary)
  - hitl_list / hitl_approve / hitl_reject tool dispatch
  - Resource list / resource read dispatch
  - validate_run_gate suggest-only (no auto-apply)
  - Malformed input rejection before any queue is touched
"""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import MagicMock, patch

from cherenkov.mcp.contracts import (
    HitlApproveInput,
    HitlListInput,
    HitlRejectInput,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
)
from cherenkov.mcp.protocol import dispatch_one
from cherenkov.mcp.server import build_dispatch_table, _handle_initialize


class TestJsonRpcProtocol(unittest.TestCase):
    """JSON-RPC 2.0 framing — parse, dispatch, error handling."""

    def setUp(self):
        self.table = build_dispatch_table()

    def test_parse_error_on_invalid_json(self):
        resp = dispatch_one("not json{{", self.table)
        self.assertIsNotNone(resp)
        self.assertIsNotNone(resp.error)
        self.assertEqual(resp.error.code, PARSE_ERROR)

    def test_method_not_found(self):
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "nonexistent", "params": {}}
        )
        resp = dispatch_one(raw, self.table)
        self.assertIsNotNone(resp.error)
        self.assertEqual(resp.error.code, METHOD_NOT_FOUND)

    def test_notification_no_reply(self):
        # Notifications have no 'id' field — server must not reply
        raw = json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        )
        resp = dispatch_one(raw, self.table)
        self.assertIsNone(resp)

    def test_ping_returns_empty_dict(self):
        raw = json.dumps({"jsonrpc": "2.0", "id": 42, "method": "ping", "params": {}})
        resp = dispatch_one(raw, self.table)
        self.assertIsNone(resp.error)
        self.assertEqual(resp.result, {})
        self.assertEqual(resp.id, 42)

    def test_id_echoed_in_response(self):
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": "abc-123", "method": "ping", "params": {}}
        )
        resp = dispatch_one(raw, self.table)
        self.assertEqual(resp.id, "abc-123")

    def test_empty_line_skipped(self):
        # serve_stdio skips empty lines; dispatch_one itself never sees them
        # but confirm dispatch_one on empty JSON returns parse error
        resp = dispatch_one("", self.table)
        self.assertIsNotNone(resp.error)
        self.assertEqual(resp.error.code, PARSE_ERROR)


class TestMCPInitialize(unittest.TestCase):
    """MCP initialize handshake shape."""

    def test_initialize_returns_protocol_version(self):
        result = _handle_initialize({})
        self.assertEqual(result["protocolVersion"], "2024-11-05")

    def test_initialize_has_server_info(self):
        result = _handle_initialize({})
        self.assertEqual(result["serverInfo"]["name"], "cherenkov")
        self.assertIn("version", result["serverInfo"])

    def test_initialize_has_capabilities(self):
        result = _handle_initialize({})
        caps = result["capabilities"]
        self.assertIn("resources", caps)
        self.assertIn("tools", caps)

    def test_initialize_via_dispatch(self):
        table = build_dispatch_table()
        raw = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "clientInfo": {}},
            }
        )
        resp = dispatch_one(raw, table)
        self.assertIsNone(resp.error)
        self.assertIn("protocolVersion", resp.result)


class TestResourcesListDispatch(unittest.TestCase):
    """resources/list — catalogue shape."""

    def setUp(self):
        self.table = build_dispatch_table()

    def test_resources_list_returns_list(self):
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}}
        )
        resp = dispatch_one(raw, self.table)
        self.assertIsNone(resp.error)
        self.assertIn("resources", resp.result)
        self.assertIsInstance(resp.result["resources"], list)
        self.assertGreaterEqual(len(resp.result["resources"]), 4)

    def test_resources_have_required_fields(self):
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}}
        )
        resp = dispatch_one(raw, self.table)
        for r in resp.result["resources"]:
            self.assertIn("uri", r)
            self.assertIn("name", r)
            self.assertIn("description", r)


class TestToolsListDispatch(unittest.TestCase):
    """tools/list — catalogue shape."""

    def setUp(self):
        self.table = build_dispatch_table()

    def test_tools_list_returns_expected_tools(self):
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        resp = dispatch_one(raw, self.table)
        self.assertIsNone(resp.error)
        names = {t["name"] for t in resp.result["tools"]}
        self.assertIn("hitl_list", names)
        self.assertIn("hitl_approve", names)
        self.assertIn("hitl_reject", names)
        self.assertIn("validate_run_gate", names)

    def test_tools_have_input_schema(self):
        raw = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        resp = dispatch_one(raw, self.table)
        for t in resp.result["tools"]:
            self.assertIn("inputSchema", t)
            self.assertEqual(t["inputSchema"]["type"], "object")


class TestInputValidation(unittest.TestCase):
    """Trust boundary: invalid inputs are rejected before any queue is touched."""

    def test_hitl_approve_rejects_empty_item_id(self):
        with self.assertRaises(Exception):
            HitlApproveInput.model_validate({"item_id": ""})

    def test_hitl_reject_rejects_empty_item_id(self):
        with self.assertRaises(Exception):
            HitlRejectInput.model_validate({"item_id": ""})

    def test_hitl_list_rejects_invalid_status(self):
        with self.assertRaises(Exception):
            HitlListInput.model_validate({"status": "invalid_status"})

    def test_hitl_list_accepts_none_status(self):
        inp = HitlListInput.model_validate({"status": None})
        self.assertIsNone(inp.status)

    def test_hitl_list_defaults_to_pending(self):
        inp = HitlListInput.model_validate({})
        self.assertEqual(inp.status, "pending")

    def test_hitl_approve_via_tool_call_rejects_empty_id(self):
        """Verify that tools/call with empty item_id returns isError=True, not a crash."""
        table = build_dispatch_table()
        raw = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "hitl_approve", "arguments": {"item_id": ""}},
            }
        )
        resp = dispatch_one(raw, table)
        self.assertIsNone(resp.error)  # JSON-RPC level is fine
        result = resp.result
        self.assertTrue(result.get("isError", False))  # MCP-level is error


class TestHitlToolsWithMockQueue(unittest.TestCase):
    """hitl_list / hitl_approve / hitl_reject — delegates to HitlQueue."""

    def setUp(self):
        self.table = build_dispatch_table()

    def _call(self, tool: str, arguments: dict) -> dict:
        raw = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            }
        )
        resp = dispatch_one(raw, self.table)
        self.assertIsNone(resp.error)
        return resp.result

    @patch("cherenkov.mcp.handlers._queue")
    def test_hitl_list_calls_queue_list(self, mock_queue_factory):
        mock_q = MagicMock()
        mock_q.list.return_value = []
        mock_queue_factory.return_value = mock_q

        result = self._call("hitl_list", {"status": "pending"})
        mock_q.list.assert_called_once_with(status="pending")
        self.assertFalse(result.get("isError", False))

    @patch("cherenkov.mcp.handlers._queue")
    def test_hitl_list_all_statuses(self, mock_queue_factory):
        mock_q = MagicMock()
        mock_q.list.return_value = []
        mock_queue_factory.return_value = mock_q

        result = self._call("hitl_list", {"status": None})
        mock_q.list.assert_called_once_with(status=None)

    @patch("cherenkov.mcp.handlers._queue")
    def test_hitl_approve_calls_queue_approve(self, mock_queue_factory):
        from cherenkov.hitl.contracts import ok_envelope

        mock_q = MagicMock()
        mock_q.approve.return_value = ok_envelope(
            "hitl.approve", {"id": "x", "action": "approve"}
        )
        mock_queue_factory.return_value = mock_q

        result = self._call("hitl_approve", {"item_id": "item-1", "actor": "alice"})
        mock_q.approve.assert_called_once_with(
            item_id="item-1", actor="alice", source="mcp"
        )
        self.assertFalse(result.get("isError", False))

    @patch("cherenkov.mcp.handlers._queue")
    def test_hitl_reject_calls_queue_reject(self, mock_queue_factory):
        from cherenkov.hitl.contracts import ok_envelope

        mock_q = MagicMock()
        mock_q.reject.return_value = ok_envelope(
            "hitl.reject", {"id": "x", "action": "reject"}
        )
        mock_queue_factory.return_value = mock_q

        result = self._call(
            "hitl_reject", {"item_id": "item-1", "actor": "bob", "reason": "wrong"}
        )
        mock_q.reject.assert_called_once_with(
            item_id="item-1", actor="bob", reason="wrong", source="mcp"
        )
        self.assertFalse(result.get("isError", False))

    @patch("cherenkov.mcp.handlers._queue")
    def test_hitl_approve_missing_actor_uses_default(self, mock_queue_factory):
        from cherenkov.hitl.contracts import ok_envelope

        mock_q = MagicMock()
        mock_q.approve.return_value = ok_envelope("hitl.approve", {})
        mock_queue_factory.return_value = mock_q

        result = self._call("hitl_approve", {"item_id": "item-1"})
        # default actor is 'mcp-peer'
        call_kwargs = mock_q.approve.call_args
        self.assertEqual(call_kwargs.kwargs["actor"], "mcp-peer")


class TestValidateRunGate(unittest.TestCase):
    """validate_run_gate — suggest-only, never auto-applies."""

    def setUp(self):
        self.table = build_dispatch_table()

    @patch("cherenkov.mcp.handlers.ValidationGate")
    def test_validate_run_gate_returns_report(self, mock_gate_cls):
        from cherenkov.validate.contracts import ValidationReport
        import uuid
        from datetime import datetime, timezone

        mock_report = ValidationReport(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            result="pass",
            gates=[],
            summary="All gates passed.",
        )
        mock_gate = MagicMock()
        mock_gate.run.return_value = mock_report
        mock_gate_cls.return_value = mock_gate

        raw = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "validate_run_gate", "arguments": {}},
            }
        )
        resp = dispatch_one(raw, self.table)
        self.assertIsNone(resp.error)
        self.assertFalse(resp.result.get("isError", False))
        content = resp.result["content"][0]["text"]
        data = json.loads(content)
        self.assertEqual(data["result"], "pass")
        # Must not auto-apply anything
        mock_gate.run.assert_called_once()  # called once, no side effects

    @patch("cherenkov.mcp.handlers.ValidationGate")
    def test_validate_run_gate_error_returns_iserror(self, mock_gate_cls):
        mock_gate = MagicMock()
        mock_gate.run.side_effect = RuntimeError("gate failed")
        mock_gate_cls.return_value = mock_gate

        raw = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "validate_run_gate", "arguments": {}},
            }
        )
        resp = dispatch_one(raw, self.table)
        self.assertIsNone(resp.error)
        self.assertTrue(resp.result.get("isError", False))


class TestStdioTransport(unittest.TestCase):
    """serve_stdio — stream injection for hermetic testing."""

    def test_serve_stdio_processes_multiple_requests(self):
        from cherenkov.mcp.protocol import serve_stdio

        requests = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}}),
        ]
        inp = io.StringIO("\n".join(requests) + "\n")
        out = io.StringIO()
        table = build_dispatch_table()
        serve_stdio(table, input_stream=inp, output_stream=out)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            resp = json.loads(line)
            self.assertIsNone(resp.get("error"))

    def test_serve_stdio_skips_empty_lines(self):
        from cherenkov.mcp.protocol import serve_stdio

        inp = io.StringIO(
            "\n\n"
            + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}})
            + "\n\n"
        )
        out = io.StringIO()
        serve_stdio(build_dispatch_table(), input_stream=inp, output_stream=out)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)

    def test_serve_stdio_handles_malformed_json(self):
        from cherenkov.mcp.protocol import serve_stdio

        inp = io.StringIO("{{broken\n")
        out = io.StringIO()
        serve_stdio(build_dispatch_table(), input_stream=inp, output_stream=out)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        resp = json.loads(lines[0])
        self.assertEqual(resp["error"]["code"], PARSE_ERROR)


if __name__ == "__main__":
    unittest.main()
