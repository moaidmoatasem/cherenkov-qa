from unittest.mock import MagicMock

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.substrate.providers.ollama import OllamaProvider
from cherenkov.substrate.providers.openai import OpenAIProvider
from cherenkov.substrate.providers.vlm import VLMProvider as VLMImpl


def _ollama_provider():
    mock_client = MagicMock()
    mock_client.complete.return_value = "ollama response"
    mock_client.complete_json.return_value = '{"key": "value"}'
    return OllamaProvider(client=mock_client)


def _openai_provider():
    mock_client = MagicMock()
    mock_client.complete.return_value = "openai response"
    return OpenAIProvider(client=mock_client)


def test_ollama_provider_init():
    prov = _ollama_provider()
    assert prov.provider_name == "ollama"
    assert not prov.requires_egress


def test_ollama_provider_generate():
    prov = _ollama_provider()
    req = ReasoningRequest(task="hello", capability_tier="small")
    result = prov.generate(req)
    assert isinstance(result, ReasoningResult)
    assert result.content == "ollama response"
    assert result.provider == "ollama"


def test_ollama_provider_generate_with_schema():
    prov = _ollama_provider()
    req = ReasoningRequest(task="test", capability_tier="small",
                           output_schema={"type": "object"})
    result = prov.generate(req)
    assert result.content == '{"key": "value"}'


def test_ollama_provider_capabilities():
    prov = _ollama_provider()
    caps = prov.capabilities()
    assert "vision" in caps.capability_tiers
    assert not caps.requires_egress


def test_openai_provider_init():
    prov = _openai_provider()
    assert prov.provider_name == "openai"
    assert prov.requires_egress


def test_openai_provider_generate():
    prov = _openai_provider()
    req = ReasoningRequest(task="hello", capability_tier="small")
    result = prov.generate(req)
    assert isinstance(result, ReasoningResult)
    assert result.content == "openai response"
    assert result.provider == "openai"


def test_openai_provider_capabilities():
    prov = _openai_provider()
    caps = prov.capabilities()
    assert "small" in caps.capability_tiers
    assert caps.requires_egress


def test_vlm_provider_init():
    vlm = VLMImpl(provider_name="ollama")
    assert vlm.provider_name == "ollama"


def test_vlm_provider_health_ollama():
    vlm = VLMImpl(provider_name="ollama")
    assert vlm.health()


def test_vlm_provider_health_not_ollama():
    vlm = VLMImpl(provider_name="openai")
    assert not vlm.health()
