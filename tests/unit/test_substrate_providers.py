import unittest
from unittest.mock import MagicMock, patch

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.substrate.providers.ollama import OllamaProvider
from cherenkov.substrate.providers.openai import OpenAIProvider
from cherenkov.substrate.providers.vlm import VLMProvider as VLMImpl


class TestOllamaProvider(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_client.complete.return_value = "ollama response"
        self.mock_client.complete_json.return_value = '{"key": "value"}'
        self.prov = OllamaProvider(client=self.mock_client)

    def test_init(self):
        self.assertEqual(self.prov.provider_name, "ollama")
        self.assertFalse(self.prov.requires_egress)

    def test_generate(self):
        req = ReasoningRequest(task="hello", capability_tier="small")
        result = self.prov.generate(req)
        self.assertIsInstance(result, ReasoningResult)
        self.assertEqual(result.content, "ollama response")
        self.assertEqual(result.provider, "ollama")

    def test_generate_with_schema(self):
        req = ReasoningRequest(task="test", capability_tier="small",
                               output_schema={"type": "object"})
        result = self.prov.generate(req)
        self.assertEqual(result.content, '{"key": "value"}')

    def test_capabilities(self):
        caps = self.prov.capabilities()
        self.assertIn("vision", caps.capability_tiers)
        self.assertFalse(caps.requires_egress)


class TestOpenAIProvider(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_client.complete.return_value = "openai response"
        self.prov = OpenAIProvider(client=self.mock_client)

    def test_init(self):
        self.assertEqual(self.prov.provider_name, "openai")
        self.assertTrue(self.prov.requires_egress)

    def test_generate(self):
        req = ReasoningRequest(task="hello", capability_tier="small")
        result = self.prov.generate(req)
        self.assertIsInstance(result, ReasoningResult)
        self.assertEqual(result.content, "openai response")
        self.assertEqual(result.provider, "openai")

    def test_capabilities(self):
        caps = self.prov.capabilities()
        self.assertIn("small", caps.capability_tiers)
        self.assertTrue(caps.requires_egress)


class TestVLMProvider(unittest.TestCase):
    def test_init(self):
        vlm = VLMImpl(provider_name="ollama")
        self.assertEqual(vlm.provider_name, "ollama")

    def test_health_ollama(self):
        vlm = VLMImpl(provider_name="ollama")
        self.assertTrue(vlm.health())

    def test_health_not_ollama(self):
        vlm = VLMImpl(provider_name="openai")
        self.assertFalse(vlm.health())
