import unittest
from unittest.mock import patch, MagicMock

from cherenkov.substrate.provider import (
    get_vlm_provider,
    provider_for_tier,
    _resolve_vlm_provider,
)


class TestTierAwareRouting(unittest.TestCase):
    def test_ollama_vlm_provider(self):
        with patch("cherenkov.substrate.provider.Config.TIER_VISION_PROVIDER", "ollama"):
            p = get_vlm_provider()
            self.assertIsNotNone(p)

    def test_openai_vlm_provider(self):
        with patch("cherenkov.substrate.provider.Config.TIER_VISION_PROVIDER", "openai"):
            with patch("cherenkov.substrate.provider.OpenAIInferenceClient") as mock:
                mock.return_value = MagicMock()
                p = get_vlm_provider()
                self.assertIsNotNone(p)

    def test_localai_vlm_provider(self):
        with patch("cherenkov.substrate.provider.Config.TIER_VISION_PROVIDER", "localai"):
            with patch("cherenkov.substrate.providers.localai.LocalAIVLMProvider") as mock:
                mock.return_value = MagicMock()
                p = get_vlm_provider()
                self.assertIsNotNone(p)

    def test_unknown_provider_raises(self):
        with patch("cherenkov.substrate.provider.Config.TIER_VISION_PROVIDER", "unknown"):
            with self.assertRaises(ValueError):
                get_vlm_provider()

    def test_provider_for_tier_small(self):
        with patch("cherenkov.substrate.provider.Config.TIER_SMALL_PROVIDER", "ollama"):
            p = provider_for_tier("small")
            self.assertEqual(p.capabilities().provider_name, "ollama")

    def test_provider_for_tier_deep(self):
        with patch("cherenkov.substrate.provider.Config.TIER_DEEP_PROVIDER", "ollama"):
            p = provider_for_tier("deep")
            self.assertEqual(p.capabilities().provider_name, "ollama")

    def test_provider_for_tier_vision(self):
        with patch("cherenkov.substrate.provider.Config.TIER_VISION_PROVIDER", "ollama"):
            p = provider_for_tier("vision")
            self.assertIsNotNone(p)

    def test_provider_for_tier_unknown_raises(self):
        with self.assertRaises(ValueError):
            provider_for_tier("invalid_tier")


class TestResolveVLMProvider(unittest.TestCase):
    def test_resolve_configured(self):
        with patch("cherenkov.substrate.provider.Config.TIER_VISION_PROVIDER", "openai"):
            result = _resolve_vlm_provider()
            self.assertEqual(result, "openai")

    def test_resolve_auto_local_docker(self):
        with patch("cherenkov.substrate.provider.Config.TIER_VISION_PROVIDER", "auto"):
            with patch("cherenkov.core.devices.DeviceInfo") as mock_info:
                info = MagicMock()
                info.vlm_tier = "local"
                info.has_docker = True
                mock_info.return_value = info
                result = _resolve_vlm_provider()
                self.assertEqual(result, "localai")

    def test_resolve_auto_local_no_docker(self):
        with patch("cherenkov.substrate.provider.Config.TIER_VISION_PROVIDER", "auto"):
            with patch("cherenkov.core.devices.DeviceInfo") as mock_info:
                info = MagicMock()
                info.vlm_tier = "local"
                info.has_docker = False
                mock_info.return_value = info
                result = _resolve_vlm_provider()
                self.assertEqual(result, "ollama")

    def test_resolve_auto_cloud(self):
        with patch("cherenkov.substrate.provider.Config.TIER_VISION_PROVIDER", "auto"):
            with patch("cherenkov.core.devices.DeviceInfo") as mock_info:
                info = MagicMock()
                info.vlm_tier = "cloud"
                mock_info.return_value = info
                result = _resolve_vlm_provider()
                self.assertEqual(result, "openai")
