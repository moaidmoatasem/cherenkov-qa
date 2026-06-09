from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from cherenkov.mcp.handlers import (
    handle_tool_call,
    handle_tools_list,
    handle_resource_read,
    TOOLS,
    RESOURCES,
    _tool_chat_query_verdicts,
    _tool_chat_query_idioms,
    _tool_chat_explain_divergence,
    _tool_chat_run_test,
)
from cherenkov.mcp.contracts import MCPToolCallResult


CHAT_TOOL_NAMES = [
    "chat_query_verdicts",
    "chat_query_idioms",
    "chat_explain_divergence",
    "chat_run_test",
]


class TestChatToolsInToolList(unittest.TestCase):
    def test_all_four_tools_registered(self):
        tool_names = [t.name for t in TOOLS]
        for name in CHAT_TOOL_NAMES:
            self.assertIn(name, tool_names)

    def test_tools_list_includes_chat_tools(self):
        result = handle_tools_list({})
        names = [t["name"] for t in result["tools"]]
        for name in CHAT_TOOL_NAMES:
            self.assertIn(name, names)


class TestChatResourceRegistered(unittest.TestCase):
    def test_chat_sessions_resource_exists(self):
        uris = [r.uri for r in RESOURCES]
        self.assertIn("cherenkov://chat/sessions", uris)


class TestToolChatQueryVerdicts(unittest.TestCase):
    @patch("cherenkov.mcp.handlers.query_verdicts", create=True)
    def test_returns_valid_result(self, mock_qv):
        mock_qv.return_value = {"verdicts": [], "total": 0}
        with patch("cherenkov.chat.tools.query_verdicts", mock_qv):
            result = _tool_chat_query_verdicts({"limit": 5})
        self.assertIsInstance(result, MCPToolCallResult)
        self.assertFalse(result.isError)
        payload = json.loads(result.content[0].text)
        self.assertIn("verdicts", payload)

    @patch("cherenkov.chat.tools.query_verdicts")
    def test_with_endpoint_filter(self, mock_qv):
        mock_qv.return_value = {"verdicts": [{"endpoint": "/users"}], "total": 1}
        result = _tool_chat_query_verdicts({"endpoint": "/users", "limit": 10})
        self.assertFalse(result.isError)
        mock_qv.assert_called_once_with(endpoint="/users", status_code=None, limit=10)

    def test_default_limit(self):
        with patch("cherenkov.chat.tools.query_verdicts", return_value={"verdicts": [], "total": 0}) as mock_qv:
            result = _tool_chat_query_verdicts({})
        self.assertFalse(result.isError)
        mock_qv.assert_called_once_with(endpoint=None, status_code=None, limit=10)


class TestToolChatQueryIdioms(unittest.TestCase):
    @patch("cherenkov.chat.tools.query_idioms")
    def test_returns_valid_result(self, mock_qi):
        mock_qi.return_value = {"idioms": [], "total": 0}
        result = _tool_chat_query_idioms({})
        self.assertIsInstance(result, MCPToolCallResult)
        self.assertFalse(result.isError)
        payload = json.loads(result.content[0].text)
        self.assertIn("idioms", payload)

    @patch("cherenkov.chat.tools.query_idioms")
    def test_with_pattern_filter(self, mock_qi):
        mock_qi.return_value = {"idioms": [{"pattern": "auth"}], "total": 1}
        result = _tool_chat_query_idioms({"pattern": "auth", "limit": 5})
        self.assertFalse(result.isError)
        mock_qi.assert_called_once_with(pattern="auth", limit=5)


class TestToolChatExplainDivergence(unittest.TestCase):
    @patch("cherenkov.chat.tools.explain_divergence")
    def test_returns_valid_result(self, mock_ed):
        mock_ed.return_value = {"explanation": "spec mismatch"}
        result = _tool_chat_explain_divergence({"endpoint": "/users"})
        self.assertIsInstance(result, MCPToolCallResult)
        self.assertFalse(result.isError)
        mock_ed.assert_called_once_with(endpoint="/users", method="GET")

    @patch("cherenkov.chat.tools.explain_divergence")
    def test_with_method(self, mock_ed):
        mock_ed.return_value = {"explanation": "divergence detail"}
        result = _tool_chat_explain_divergence({"endpoint": "/orders", "method": "POST"})
        self.assertFalse(result.isError)
        mock_ed.assert_called_once_with(endpoint="/orders", method="POST")

    def test_missing_endpoint_raises(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            _tool_chat_explain_divergence({})


class TestToolChatRunTest(unittest.TestCase):
    @patch("cherenkov.chat.tools.run_test")
    def test_returns_valid_result(self, mock_rt):
        mock_rt.return_value = {"status": "planned", "scenarios": 3}
        result = _tool_chat_run_test({"endpoint": "/users"})
        self.assertIsInstance(result, MCPToolCallResult)
        self.assertFalse(result.isError)
        mock_rt.assert_called_once_with(endpoint="/users", method="GET", spec_path=None)

    @patch("cherenkov.chat.tools.run_test")
    @patch("cherenkov.mcp.handlers._validate_spec_path", side_effect=lambda p: p)
    def test_with_all_params(self, _mock_vsp, mock_rt):
        mock_rt.return_value = {"status": "planned", "scenarios": 1}
        result = _tool_chat_run_test({"endpoint": "/orders", "method": "POST", "spec_path": "api.yaml"})
        self.assertFalse(result.isError)
        mock_rt.assert_called_once_with(endpoint="/orders", method="POST", spec_path="api.yaml")

    def test_missing_endpoint_raises(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            _tool_chat_run_test({})


class TestHandleToolCallRouting(unittest.TestCase):
    def setUp(self):
        from cherenkov.mcp.handlers import _policy
        _policy.reload()

    @patch("cherenkov.chat.tools.query_verdicts", return_value={"verdicts": [], "total": 0})
    def test_routes_chat_query_verdicts(self, mock_qv):
        result = handle_tool_call({"name": "chat_query_verdicts", "arguments": {}})
        self.assertFalse(result.get("isError", False))

    @patch("cherenkov.chat.tools.query_idioms", return_value={"idioms": [], "total": 0})
    def test_routes_chat_query_idioms(self, mock_qi):
        result = handle_tool_call({"name": "chat_query_idioms", "arguments": {}})
        self.assertFalse(result.get("isError", False))

    @patch("cherenkov.chat.tools.explain_divergence", return_value={"explanation": "ok"})
    def test_routes_chat_explain_divergence(self, mock_ed):
        result = handle_tool_call({"name": "chat_explain_divergence", "arguments": {"endpoint": "/x"}})
        self.assertFalse(result.get("isError", False))

    @patch("cherenkov.chat.tools.run_test", return_value={"status": "planned"})
    def test_routes_chat_run_test(self, mock_rt):
        result = handle_tool_call({"name": "chat_run_test", "arguments": {"endpoint": "/x"}})
        self.assertFalse(result.get("isError", False))

    def test_unknown_tool_returns_error(self):
        result = handle_tool_call({"name": "nonexistent_tool", "arguments": {}})
        self.assertTrue(result.get("isError", False))


class TestHandleResourceReadChatSessions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    @patch("cherenkov.chat.adapters.sqlite_memory.SQLiteConversationMemory")
    def test_returns_sessions(self, mock_cls):
        mock_memory = MagicMock()
        mock_session = MagicMock()
        mock_session.to_dict.return_value = {
            "session_id": "s1",
            "persona_id": "qa_assistant",
            "created_at": "2026-01-01T00:00:00",
            "message_count": 0,
            "metadata": {},
        }
        mock_memory.list_sessions.return_value = [mock_session]
        mock_cls.return_value = mock_memory

        result = handle_resource_read({"uri": "cherenkov://chat/sessions"})
        self.assertIn("contents", result)
        text = result["contents"][0]["text"]
        payload = json.loads(text)
        self.assertIn("sessions", payload)
        self.assertEqual(len(payload["sessions"]), 1)
        self.assertEqual(payload["sessions"][0]["session_id"], "s1")

    @patch("cherenkov.chat.adapters.sqlite_memory.SQLiteConversationMemory")
    def test_empty_sessions(self, mock_cls):
        mock_memory = MagicMock()
        mock_memory.list_sessions.return_value = []
        mock_cls.return_value = mock_memory

        result = handle_resource_read({"uri": "cherenkov://chat/sessions"})
        payload = json.loads(result["contents"][0]["text"])
        self.assertEqual(payload["sessions"], [])


if __name__ == "__main__":
    unittest.main()
