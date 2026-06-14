"""
Tests for cherenkov/ai/model_runner_client.py — Docker Model Runner adapter.
Authority: v3.1 + delta.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

from cherenkov.ai.model_runner_client import ModelRunnerClient
from cherenkov.ai.router import InferenceRouter


class TestModelRunnerClient(unittest.TestCase):
    @patch("subprocess.run")
    def test_complete_returns_string(self, mock_run):
        mock_run.return_value = MagicMock(stdout="test output", returncode=0)
        client = ModelRunnerClient(model="test-model")
        result = client.complete("hello")
        self.assertIsInstance(result, str)
        self.assertEqual(result, "test output")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("docker", args)
        self.assertIn("model", args)
        self.assertIn("run", args)

    @patch("subprocess.run")
    def test_list_models_returns_list(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='[{"name": "model1"}, {"name": "model2"}]',
            returncode=0,
            text=True,
        )
        client = ModelRunnerClient()
        result = client.list_models()
        self.assertEqual(result, ["model1", "model2"])

    @patch("subprocess.run")
    def test_list_models_empty_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=1)
        client = ModelRunnerClient()
        result = client.list_models()
        self.assertEqual(result, [])


class TestInferenceRouter(unittest.TestCase):
    def test_router_defaults_to_ollama(self):
        router = InferenceRouter()
        self.assertEqual(router.provider, "ollama")

    def test_router_switches_provider(self):
        router = InferenceRouter(provider="model-runner")
        self.assertEqual(router.provider, "model-runner")

    def test_router_set_provider(self):
        router = InferenceRouter()
        router.set_provider("model-runner")
        self.assertEqual(router.provider, "model-runner")


if __name__ == "__main__":
    unittest.main()
