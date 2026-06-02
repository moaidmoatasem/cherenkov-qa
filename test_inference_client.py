#!/usr/bin/env python3
"""
test_inference_client.py — Unit tests for InferenceClient interface and OllamaInferenceClient implementation.
Verifies the abstraction contract, concrete implementation, and mock-tested behavior.
"""
import unittest
from unittest.mock import patch, MagicMock

from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import OllamaInferenceClient, complete_json, complete_code
from cherenkov.core.errors import OllamaJSONError


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


if __name__ == "__main__":
    unittest.main()
