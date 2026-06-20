"""Unit tests for E2.2 — MCP context consumer.

Covers:
  - MCPClient: construction, call_tool, list_tools, read_resource
  - MCPRegistry.forward_tool_call: routes to correct server, returns None for unknowns
  - handlers.auto_heal_code: dispatched, returns suggested_patch + applied=False
  - handlers mesh forward: unknown tool reaches mesh, forwards if registered
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.mcp.client import MCPClient, MCPClientError
from cherenkov.mcp.mesh_router import MCPRegistry
from cherenkov.mcp import handlers


# ── MCPClient ─────────────────────────────────────────────────────────────────


class TestMCPClientConstruction:
    def test_rejects_non_http_url(self) -> None:
        with pytest.raises(MCPClientError, match="http"):
            MCPClient("stdio://something")

    def test_accepts_http_url(self) -> None:
        client = MCPClient("http://localhost:9000")
        assert client._base_url == "http://localhost:9000"

    def test_strips_trailing_slash(self) -> None:
        client = MCPClient("http://localhost:9000/")
        assert client._base_url == "http://localhost:9000"


class TestMCPClientCallTool:
    def _mock_response(self, result: object) -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = {"jsonrpc": "2.0", "id": "x", "result": result}
        resp.raise_for_status = MagicMock()
        return resp

    def test_call_tool_success(self) -> None:
        client = MCPClient("http://localhost:9000")
        expected = {"content": [{"text": "ok"}], "isError": False}
        with patch("httpx.post", return_value=self._mock_response(expected)) as mock_post:
            result = client.call_tool("some_tool", {"arg": "val"})
        assert result == expected
        payload = mock_post.call_args[1]["json"]
        assert payload["method"] == "tools/call"
        assert payload["params"]["name"] == "some_tool"

    def test_call_tool_rpc_error_raises(self) -> None:
        client = MCPClient("http://localhost:9000")
        resp = MagicMock()
        resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": "x",
            "error": {"code": -32601, "message": "Method not found"},
        }
        resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=resp):
            with pytest.raises(MCPClientError, match="Method not found"):
                client.call_tool("nonexistent", {})

    def test_call_tool_timeout_raises(self) -> None:
        import httpx as _httpx

        client = MCPClient("http://localhost:9000")
        with patch("httpx.post", side_effect=_httpx.TimeoutException("timed out")):
            with pytest.raises(MCPClientError, match="Timeout"):
                client.call_tool("some_tool", {})

    def test_list_tools_returns_list(self) -> None:
        client = MCPClient("http://localhost:9000")
        tools_payload = [{"name": "tool_a"}, {"name": "tool_b"}]
        resp = MagicMock()
        resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": "x",
            "result": {"tools": tools_payload},
        }
        resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=resp):
            result = client.list_tools()
        assert result == tools_payload

    def test_null_result_returns_empty_content(self) -> None:
        client = MCPClient("http://localhost:9000")
        resp = MagicMock()
        resp.json.return_value = {"jsonrpc": "2.0", "id": "x", "result": None}
        resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=resp):
            result = client.call_tool("some_tool", {})
        assert result == {"content": [], "isError": False}


# ── MCPRegistry.forward_tool_call ─────────────────────────────────────────────


class TestMCPRegistryForward:
    def _registry_with_server(self) -> MCPRegistry:
        reg = MCPRegistry()
        reg.register_server(
            name="test_server",
            url="http://external:9001",
            tools=[{"name": "ext_tool", "description": "external tool"}],
        )
        return reg

    def test_forward_unknown_tool_returns_none(self) -> None:
        reg = MCPRegistry()
        assert reg.forward_tool_call("nonexistent_tool", {}) is None

    def test_forward_known_tool_calls_client(self) -> None:
        reg = self._registry_with_server()
        fake_result = {"content": [{"text": "done"}], "isError": False}
        with patch(
            "cherenkov.mcp.client.MCPClient.call_tool", return_value=fake_result
        ):
            result = reg.forward_tool_call("ext_tool", {"x": 1})
        assert result == fake_result

    def test_forward_propagates_client_error(self) -> None:
        reg = self._registry_with_server()
        with patch(
            "cherenkov.mcp.client.MCPClient.call_tool",
            side_effect=MCPClientError("network down"),
        ):
            with pytest.raises(MCPClientError, match="network down"):
                reg.forward_tool_call("ext_tool", {})


# ── auto_heal_code dispatch ───────────────────────────────────────────────────


def _call(name: str, args: dict) -> dict:
    with patch.object(handlers._policy, "is_tool_allowed", return_value=True):
        with patch("cherenkov.mcp.handlers.get_guard") as mock_guard:
            mock_guard.return_value.check_tool_call.return_value = MagicMock(allowed=True)
            return handlers.handle_tool_call({"name": name, "arguments": args})


class TestAutoHealCode:
    def test_auto_heal_code_registered(self) -> None:
        names = [t.name for t in handlers.TOOLS]
        assert "auto_heal_code" in names

    def test_missing_item_id_returns_error(self) -> None:
        result = _call("auto_heal_code", {})
        text = result["content"][0]["text"]
        assert "required" in text.lower() or result.get("isError")

    def test_item_not_found_returns_error(self) -> None:
        with patch("cherenkov.mcp.handlers.HitlQueue") as MockQ:
            MockQ.return_value.get.return_value = None
            result = _call("auto_heal_code", {"item_id": "does-not-exist"})
        data = json.loads(result["content"][0]["text"])
        assert "error" in data

    def test_returns_suggested_patch_not_applied(self) -> None:
        fake_item = MagicMock()
        fake_item.id = "item-abc"
        fake_item.review_gate_failed = "assertion"
        fake_item.mutation_label = "weakened"
        fake_item.confidence_reason = "status check was loosened"

        with patch("cherenkov.mcp.handlers.HitlQueue") as MockQ:
            MockQ.return_value.get.return_value = fake_item
            with patch(
                "cherenkov.mcp.handlers._tool_auto_heal_code",
                wraps=handlers._tool_auto_heal_code,
            ):
                result = _call("auto_heal_code", {"item_id": "item-abc"})

        data = json.loads(result["content"][0]["text"])
        assert "suggested_patch" in data
        assert data["applied"] is False
        assert "D7" in data.get("note", "")

    def test_llm_unavailable_returns_stub_patch(self) -> None:
        fake_item = MagicMock()
        fake_item.id = "item-xyz"
        fake_item.review_gate_failed = "prism-dryrun"
        fake_item.mutation_label = "hallucinated"
        fake_item.confidence_reason = "field not in spec"

        with patch("cherenkov.mcp.handlers.HitlQueue") as MockQ:
            MockQ.return_value.get.return_value = fake_item
            with patch(
                "cherenkov.ai.router.InferenceRouter.generate",
                side_effect=RuntimeError("no LLM"),
            ):
                result = _call("auto_heal_code", {"item_id": "item-xyz"})

        data = json.loads(result["content"][0]["text"])
        assert "suggested_patch" in data
        assert data["applied"] is False


# ── Mesh forwarding fallback in handle_tool_call ──────────────────────────────


class TestMeshForwardFallback:
    def test_unknown_tool_tries_mesh_and_fails_gracefully(self) -> None:
        result = _call("totally_unknown_tool_xyz", {})
        text = result["content"][0]["text"]
        assert "Unknown tool" in text or "error" in text.lower()

    def test_mesh_registered_tool_is_forwarded(self) -> None:
        fake_result = {"content": [{"text": json.dumps({"ok": True})}], "isError": False}
        mock_reg = MagicMock()
        mock_reg.forward_tool_call.return_value = fake_result
        with patch("cherenkov.mcp.mesh_router._registry", mock_reg):
            result = _call("ext_remote_tool", {"arg": "value"})

        assert result == fake_result
        mock_reg.forward_tool_call.assert_called_once_with("ext_remote_tool", {"arg": "value"})

    def test_mesh_client_error_returns_error_content(self) -> None:
        mock_reg = MagicMock()
        mock_reg.forward_tool_call.side_effect = MCPClientError("server down")
        with patch("cherenkov.mcp.mesh_router._registry", mock_reg):
            result = _call("ext_remote_tool", {})

        data = json.loads(result["content"][0]["text"])
        assert "server down" in data.get("error", "")
