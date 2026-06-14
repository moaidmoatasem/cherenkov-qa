from cherenkov.core.settings import get_settings
import pytest
from unittest.mock import patch, MagicMock

from cherenkov.substrate.provider import (
    get_vlm_provider,
    provider_for_tier,
    _resolve_vlm_provider,
)


def test_ollama_vlm_provider():
    with patch.object(get_settings(), "TIER_VISION_PROVIDER", "ollama"):
        p = get_vlm_provider()
        assert p is not None


def test_openai_vlm_provider():
    with patch.object(get_settings(), "TIER_VISION_PROVIDER", "openai"):
        with patch("cherenkov.substrate.provider.OpenAIInferenceClient") as mock:
            mock.return_value = MagicMock()
            p = get_vlm_provider()
            assert p is not None


def test_localai_vlm_provider():
    with patch.object(get_settings(), "TIER_VISION_PROVIDER", "localai"):
        with patch("cherenkov.substrate.providers.localai.LocalAIVLMProvider") as mock:
            mock.return_value = MagicMock()
            p = get_vlm_provider()
            assert p is not None


def test_unknown_provider_raises():
    with patch.object(get_settings(), "TIER_VISION_PROVIDER", "unknown"):
        with pytest.raises(ValueError):
            get_vlm_provider()


def test_provider_for_tier_small():
    with patch.object(get_settings(), "TIER_SMALL_PROVIDER", "ollama"):
        p = provider_for_tier("small")
        assert p.capabilities().provider_name == "ollama"


def test_provider_for_tier_deep():
    with patch.object(get_settings(), "TIER_DEEP_PROVIDER", "ollama"):
        p = provider_for_tier("deep")
        assert p.capabilities().provider_name == "ollama"


def test_provider_for_tier_vision():
    with patch.object(get_settings(), "TIER_VISION_PROVIDER", "ollama"):
        p = provider_for_tier("vision")
        assert p is not None


def test_provider_for_tier_unknown_raises():
    with pytest.raises(ValueError):
        provider_for_tier("invalid_tier")


def test_resolve_configured():
    with patch.object(get_settings(), "TIER_VISION_PROVIDER", "openai"):
        result = _resolve_vlm_provider()
        assert result == "openai"


def test_resolve_auto_local_docker():
    with patch.object(get_settings(), "TIER_VISION_PROVIDER", "auto"):
        with patch("cherenkov.core.devices.DeviceInfo") as mock_info:
            info = MagicMock()
            info.vlm_tier = "local"
            info.has_docker = True
            mock_info.return_value = info
            result = _resolve_vlm_provider()
            assert result == "localai"


def test_resolve_auto_local_no_docker():
    with patch.object(get_settings(), "TIER_VISION_PROVIDER", "auto"):
        with patch("cherenkov.core.devices.DeviceInfo") as mock_info:
            info = MagicMock()
            info.vlm_tier = "local"
            info.has_docker = False
            mock_info.return_value = info
            result = _resolve_vlm_provider()
            assert result == "ollama"


def test_resolve_auto_cloud():
    with patch.object(get_settings(), "TIER_VISION_PROVIDER", "auto"):
        with patch("cherenkov.core.devices.DeviceInfo") as mock_info:
            info = MagicMock()
            info.vlm_tier = "cloud"
            mock_info.return_value = info
            result = _resolve_vlm_provider()
            assert result == "openai"
