#!/usr/bin/env python3
"""
test_inference_client.py — Unit tests for InferenceClient interface and OllamaInferenceClient implementation.
Verifies the abstraction contract, concrete implementation, and mock-tested behavior.
"""
import unittest
from unittest.mock import patch, MagicMock

from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import OllamaInferenceClient, complete_json, complete_code
from cherenkov.core.errors import OllamaJSONError, ProviderJSONError
from cherenkov.ai.openai_client import OpenAIInferenceClient


class TestInferenceClient(unittest.TestCase):

    def test_interface_cannot_be_instantiated(self):
        """Verify InferenceClient is an abstract class and cannot be directly instantiated."""
        with self.assertRaises(TypeError):
            InferenceClient()  # type: ignore

    def test_ollama_client_implements_interface(self):
        """Verify OllamaInferenceClient is a subclass of InferenceClient."""
        client = OllamaInferenceClient()
        self.assertTrue(isinstance(client, InferenceClient))

    @patch("requests.post")
    def test_ollama_client_complete_json_success(self, mock_post):
        """Verify complete_json successfully requests, parses and returns JSON."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": '{"key": "value"}'}
        mock_post.return_value = mock_resp

        client = OllamaInferenceClient()
        result = client.complete_json(
            system_prompt="sys",
            user_prompt="user",
            model="qwen2.5-coder:7b"
        )
        self.assertEqual(result, {"key": "value"})
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_ollama_client_complete_json_failure_then_repair(self, mock_post):
        """Verify complete_json handles invalid JSON by attempting repair."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # First attempt returns malformed but repairable JSON (surrounded by text)
        mock_resp.json.return_value = {"response": 'Some prose here {"key": "value"} other prose'}
        mock_post.return_value = mock_resp

        client = OllamaInferenceClient()
        result = client.complete_json(
            system_prompt="sys",
            user_prompt="user",
            model="qwen2.5-coder:7b"
        )
        self.assertEqual(result, {"key": "value"})

    @patch("requests.post")
    def test_ollama_client_complete_json_exhausted_raises_error(self, mock_post):
        """Verify complete_json raises OllamaJSONError after reprompts are exhausted."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "completely invalid non-json text"}
        mock_post.return_value = mock_resp

        client = OllamaInferenceClient()
        with self.assertRaises(OllamaJSONError):
            client.complete_json(
                system_prompt="sys",
                user_prompt="user",
                model="qwen2.5-coder:7b",
                max_reprompts=1
            )
        # Should call mock_post twice (1 initial + 1 reprompt)
        self.assertEqual(mock_post.call_count, 2)

    @patch("requests.post")
    def test_ollama_client_complete_code_strips_markdown(self, mock_post):
        """Verify complete_code successfully strips markdown fences."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "```typescript\nconst a = 1;\n```"}
        mock_post.return_value = mock_resp

        client = OllamaInferenceClient()
        result = client.complete_code(
            system_prompt="sys",
            user_prompt="user",
            model="qwen2.5-coder:7b"
        )
        self.assertEqual(result, "const a = 1;")

    @patch("requests.post")
    def test_module_level_delegation(self, mock_post):
        """Verify module-level complete_json/complete_code delegate to default client."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": '{"status": "ok"}'}
        mock_post.return_value = mock_resp

        # Test complete_json delegation
        res_json = complete_json("sys", "user", "model")
        self.assertEqual(res_json, {"status": "ok"})

        # Test complete_code delegation
        mock_resp.json.return_value = {"response": "const x = 5;"}
        res_code = complete_code("sys", "user", "model")
        self.assertEqual(res_code, "const x = 5;")


class TestOpenAIInferenceClient(unittest.TestCase):
    """Same conformance tests applied to the OpenAI provider (E1-3)."""

    def test_openai_client_implements_interface(self):
        """Verify OpenAIInferenceClient is a subclass of InferenceClient."""
        client = OpenAIInferenceClient()
        self.assertTrue(isinstance(client, InferenceClient))

    @patch.object(OpenAIInferenceClient, "_chat_completion")
    def test_openai_client_complete_json_success(self, mock_chat):
        """Verify complete_json successfully returns parsed JSON."""
        mock_chat.return_value = '{"key": "value"}'

        client = OpenAIInferenceClient()
        result = client.complete_json(
            system_prompt="sys",
            user_prompt="user",
            model="gpt-4o-mini"
        )
        self.assertEqual(result, {"key": "value"})
        mock_chat.assert_called_once()

    @patch.object(OpenAIInferenceClient, "_chat_completion")
    def test_openai_client_complete_json_failure_then_repair(self, mock_chat):
        """Verify complete_json handles invalid JSON by attempting repair."""
        mock_chat.return_value = 'Some prose here {"key": "value"} other prose'

        client = OpenAIInferenceClient()
        result = client.complete_json(
            system_prompt="sys",
            user_prompt="user",
            model="gpt-4o-mini"
        )
        self.assertEqual(result, {"key": "value"})

    @patch.object(OpenAIInferenceClient, "_chat_completion")
    def test_openai_client_complete_json_exhausted_raises_error(self, mock_chat):
        """Verify complete_json raises ProviderJSONError after reprompts exhausted."""
        mock_chat.return_value = "completely invalid non-json text"

        client = OpenAIInferenceClient()
        with self.assertRaises(ProviderJSONError):
            client.complete_json(
                system_prompt="sys",
                user_prompt="user",
                model="gpt-4o-mini",
                max_reprompts=1
            )
        self.assertEqual(mock_chat.call_count, 2)

    @patch.object(OpenAIInferenceClient, "_chat_completion")
    def test_openai_client_complete_code_strips_markdown(self, mock_chat):
        """Verify complete_code successfully strips markdown fences."""
        mock_chat.return_value = "```typescript\nconst a = 1;\n```"

        client = OpenAIInferenceClient()
        result = client.complete_code(
            system_prompt="sys",
            user_prompt="user",
            model="gpt-4o-mini"
        )
        self.assertEqual(result, "const a = 1;")

    @patch.object(OpenAIInferenceClient, "_chat_completion")
    def test_openai_client_get_client_factory(self, mock_chat):
        """Verify get_client() returns OpenAIInferenceClient when configured."""
        from cherenkov.ai import get_client
        from cherenkov.core.config import Config

        original = Config.PROVIDER
        try:
            Config.PROVIDER = "openai"
            client = get_client()
            wrapped = client.wrapped_client if hasattr(client, "wrapped_client") else client
            self.assertIsInstance(wrapped, OpenAIInferenceClient)
        finally:
            Config.PROVIDER = original

    @patch.object(OpenAIInferenceClient, "_chat_completion")
    def test_openai_client_api_request_failure(self, mock_chat):
        """Verify complete_json raises ProviderJSONError on API failure."""
        from requests import RequestException

        mock_chat.side_effect = RequestException("Connection error")

        client = OpenAIInferenceClient()
        with self.assertRaises(ProviderJSONError):
            client.complete_json(
                system_prompt="sys",
                user_prompt="user",
                model="gpt-4o-mini",
                max_reprompts=0
            )


class TestClientMemoization(unittest.TestCase):
    """get_client() must reuse one client per provider so cache/accounting persist."""

    def setUp(self):
        import cherenkov.ai as ai_mod
        ai_mod.reset_client()

    def tearDown(self):
        import cherenkov.ai as ai_mod
        ai_mod.reset_client()

    def test_get_client_is_memoized_per_provider(self):
        """Repeated get_client() calls with the same provider return the SAME object."""
        from cherenkov.ai import get_client
        from cherenkov.core.config import Config

        original = Config.PROVIDER
        try:
            Config.PROVIDER = "ollama"
            first = get_client()
            second = get_client()
            self.assertIs(first, second,
                          "get_client() rebuilt the client — cache/accounting would reset")
        finally:
            Config.PROVIDER = original

    def test_provider_change_rebuilds(self):
        """Switching Config.PROVIDER yields a different client for the new provider."""
        from cherenkov.ai import get_client
        from cherenkov.core.config import Config

        original = Config.PROVIDER
        try:
            Config.PROVIDER = "ollama"
            ollama_client = get_client()
            Config.PROVIDER = "openai"
            openai_client = get_client()
            self.assertIsNot(ollama_client, openai_client)
            wrapped = getattr(openai_client, "wrapped_client", openai_client)
            self.assertIsInstance(wrapped, OpenAIInferenceClient)
        finally:
            Config.PROVIDER = original

    def test_set_and_reset_client(self):
        """set_client() injects; reset_client() clears so get_client() rebuilds."""
        import cherenkov.ai as ai_mod
        from cherenkov.ai import set_client, reset_client, CachedInferenceClient
        from cherenkov.core.config import Config

        original = Config.PROVIDER
        try:
            injected = CachedInferenceClient(OllamaInferenceClient())
            set_client(injected)
            self.assertIs(ai_mod._current_client, injected)
            reset_client()
            self.assertIsNone(ai_mod._current_client)
            Config.PROVIDER = "ollama"
            rebuilt = ai_mod.get_client()
            self.assertIsNot(rebuilt, injected)
        finally:
            Config.PROVIDER = original
            reset_client()


if __name__ == "__main__":
    unittest.main()
