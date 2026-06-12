"""Unit tests for the NVIDIA NemoClaw substrate provider and inference client."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from cherenkov.core.contracts import ReasoningRequest
from cherenkov.substrate.providers.nemoclaw import NemoClawProvider
from cherenkov.substrate.provider import get_provider, ProviderCapabilities
from cherenkov.ai.nemoclaw_client import NemoClawInferenceClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(content: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# NemoClawInferenceClient
# ---------------------------------------------------------------------------


class TestNemoClawInferenceClient:
    def _client(self, **kwargs) -> NemoClawInferenceClient:
        return NemoClawInferenceClient(
            base_url="http://localhost:11435/v1",
            api_key="test-key",
            **kwargs,
        )

    def test_headers_with_api_key(self):
        client = self._client()
        assert client._headers()["Authorization"] == "Bearer test-key"
        assert client._headers()["Content-Type"] == "application/json"

    def test_headers_without_api_key(self):
        client = NemoClawInferenceClient(
            base_url="http://localhost:11435/v1", api_key=""
        )
        assert "Authorization" not in client._headers()

    @patch("cherenkov.ai.nemoclaw_client.requests.post")
    def test_complete_json_success(self, mock_post):
        mock_post.return_value = _mock_response('{"status": "ok"}')
        client = self._client()
        result = client.complete_json(
            system_prompt="sys", user_prompt="user", model="nemotron-nano-4b"
        )
        assert result == {"status": "ok"}
        assert client._token_usage["prompt_tokens"] == 10
        assert client._token_usage["completion_tokens"] == 20

    @patch("cherenkov.ai.nemoclaw_client.requests.post")
    def test_complete_json_uses_json_object_format(self, mock_post):
        mock_post.return_value = _mock_response('{"x": 1}')
        client = self._client()
        client.complete_json(system_prompt="s", user_prompt="u", model="m")
        call_body = mock_post.call_args[1]["json"]
        assert call_body.get("response_format") == {"type": "json_object"}

    @patch("cherenkov.ai.nemoclaw_client.requests.post")
    def test_complete_code_strips_fences(self, mock_post):
        mock_post.return_value = _mock_response("```typescript\nconst x = 1;\n```")
        client = self._client()
        result = client.complete_code(
            system_prompt="sys", user_prompt="gen a test", model="nemotron-nano-4b"
        )
        assert result == "const x = 1;"

    @patch("cherenkov.ai.nemoclaw_client.requests.post")
    def test_complete_vision_sends_image(self, mock_post):
        mock_post.return_value = _mock_response("Two buttons differ in colour.")
        client = self._client()
        result = client.complete_vision(
            system_prompt="sys",
            user_prompt="compare",
            image_data="abc123",
            model="nemotron-vlm-4b",
        )
        assert "differ" in result
        call_body = mock_post.call_args[1]["json"]
        user_msg = call_body["messages"][1]["content"]
        assert any(
            part.get("type") == "image_url" for part in user_msg
        )

    @patch("cherenkov.ai.nemoclaw_client.requests.get")
    def test_health_returns_true_on_200(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        client = self._client()
        assert client.health() is True

    @patch("cherenkov.ai.nemoclaw_client.requests.get")
    def test_health_returns_false_on_connection_error(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.RequestException("refused")
        client = self._client()
        assert client.health() is False

    @patch("cherenkov.ai.nemoclaw_client.requests.post")
    def test_chat_returns_content(self, mock_post):
        mock_post.return_value = _mock_response("Hello from NemoClaw!")
        client = self._client()
        result = client.chat(
            messages=[{"role": "user", "content": "hi"}],
            model="nemotron-nano-4b",
        )
        assert result == "Hello from NemoClaw!"


# ---------------------------------------------------------------------------
# NemoClawProvider
# ---------------------------------------------------------------------------


class TestNemoClawProvider:
    def _provider(self) -> tuple[NemoClawProvider, MagicMock]:
        mock_client = MagicMock()
        provider = NemoClawProvider(client=mock_client)
        return provider, mock_client

    def test_capabilities(self):
        provider, _ = self._provider()
        caps = provider.capabilities()
        assert isinstance(caps, ProviderCapabilities)
        assert caps.provider_name == "nemoclaw"
        assert caps.requires_egress is False
        assert "small" in caps.capability_tiers
        assert "deep" in caps.capability_tiers
        assert "vision" in caps.capability_tiers

    def test_generate_small_tier_calls_complete_code(self):
        provider, mock_client = self._provider()
        mock_client.complete_code.return_value = "test('x', () => {});"
        req = ReasoningRequest(task="write a test", capability_tier="small")
        result = provider.generate(req)
        mock_client.complete_code.assert_called_once()
        assert result.provider == "nemoclaw"
        assert result.cost_usd == 0.0

    def test_generate_deep_tier_calls_correct_model(self):
        from cherenkov.core.config import Config
        provider, mock_client = self._provider()
        mock_client.complete_code.return_value = "code"
        req = ReasoningRequest(task="plan", capability_tier="deep")
        result = provider.generate(req)
        assert result.model == Config.NEMOCLAW_DEEP_MODEL

    def test_generate_with_output_schema_calls_complete_json(self):
        provider, mock_client = self._provider()
        mock_client.complete_json.return_value = {"scenarios": []}
        req = ReasoningRequest(
            task="plan tests",
            capability_tier="small",
            output_schema={"type": "object", "properties": {"scenarios": {}}},
        )
        result = provider.generate(req)
        mock_client.complete_json.assert_called_once()
        assert result.content == {"scenarios": []}

    def test_generate_vision_with_image_path(self, tmp_path):
        import base64
        img_file = tmp_path / "screenshot.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal PNG header

        provider, mock_client = self._provider()
        mock_client.complete_vision.return_value = "Button colour changed."
        req = ReasoningRequest(
            task="check visual diff",
            capability_tier="vision",
            output_schema={"image_path": str(img_file)},
        )
        result = provider.generate(req)
        mock_client.complete_vision.assert_called_once()
        assert result.content == "Button colour changed."

    def test_generate_records_latency(self):
        provider, mock_client = self._provider()
        mock_client.complete_code.return_value = "code"
        req = ReasoningRequest(task="do stuff", capability_tier="small")
        result = provider.generate(req)
        assert result.latency_ms >= 0


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------


class TestNemoClawProviderRegistry:
    def test_get_provider_nemoclaw_returns_nemoclaw_provider(self):
        from cherenkov.substrate.provider import _PROVIDER_CACHE
        _PROVIDER_CACHE.pop("nemoclaw", None)
        p = get_provider("nemoclaw")
        assert isinstance(p, NemoClawProvider)

    def test_get_provider_nemoclaw_cached(self):
        from cherenkov.substrate.provider import _PROVIDER_CACHE
        _PROVIDER_CACHE.pop("nemoclaw", None)
        p1 = get_provider("nemoclaw")
        p2 = get_provider("nemoclaw")
        assert p1 is p2

    def test_get_provider_unknown_still_raises(self):
        with pytest.raises(ValueError, match="nemoclaw"):
            get_provider("__nonexistent__")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestNemoClawConfig:
    def test_config_has_nemoclaw_keys(self):
        from cherenkov.core.config import Config
        assert hasattr(Config, "NEMOCLAW_URL")
        assert hasattr(Config, "NEMOCLAW_API_KEY")
        assert hasattr(Config, "NEMOCLAW_SMALL_MODEL")
        assert hasattr(Config, "NEMOCLAW_DEEP_MODEL")
        assert hasattr(Config, "NEMOCLAW_VISION_MODEL")
        assert hasattr(Config, "NEMOCLAW_TIMEOUT")

    def test_config_defaults(self):
        from cherenkov.core.config import Config
        assert "11435" in Config.NEMOCLAW_URL
        assert Config.NEMOCLAW_SMALL_MODEL == "nemotron-nano-4b"
        assert Config.NEMOCLAW_DEEP_MODEL == "nemotron-super-49b"
        assert Config.NEMOCLAW_VISION_MODEL == "nemotron-vlm-4b"
        assert Config.NEMOCLAW_TIMEOUT == 300
