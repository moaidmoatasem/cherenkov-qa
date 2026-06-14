#!/usr/bin/env python3
"""
smoke_test_provider.py -- smoke test to verify ModelProvider SPI.
"""

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.ai.ollama_client import InferenceClient
from cherenkov.substrate.provider import OllamaProvider


class MockInferenceClient(InferenceClient):
    def complete_json(
        self, system_prompt: str, user_prompt: str, model: str, **kwargs
    ) -> dict:
        return {"test": "success"}

    def complete_code(
        self, system_prompt: str, user_prompt: str, model: str, **kwargs
    ) -> str:
        return "success"


def test_ollama_provider_conformance():
    print("=== PASS 1: Test OllamaProvider ===")
    mock_client = MockInferenceClient()
    provider = OllamaProvider(mock_client)

    request = ReasoningRequest(
        task="Write a test",
        output_schema={"type": "object", "properties": {"test": {"type": "string"}}},
        capability_tier="small",
    )

    result = provider.generate(request)
    assert isinstance(result, ReasoningResult)
    assert result.content == {"test": "success"}
    assert result.provider == "ollama"

    # Test round trip via model_validate_json
    json_str = result.model_dump_json()
    round_trip = ReasoningResult.model_validate_json(json_str)
    assert round_trip.content == result.content
    assert round_trip.provider == result.provider
    assert round_trip.model == result.model

    print("[PASS] OllamaProvider conformance test passed.")


if __name__ == "__main__":
    test_ollama_provider_conformance()
    print("=======================================================")
    print("  ALL PROVIDER SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")
