"""
cherenkov/substrate/providers/anthropic.py — Anthropic Claude BYOK provider.

Implements ModelProvider via the Anthropic SDK so enterprise users can
bring their own key (ANTHROPIC_API_KEY) and get higher-quality test
generation than local Ollama.

Egress: requires_egress=True — blocked when CHERENKOV_EGRESS=internal.

Closes: #453
"""
from __future__ import annotations

import json
import os
import re
import time

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.substrate.provider import ModelProvider, ProviderCapabilities

# Pricing (USD per 1M tokens, approximate as of 2025)
_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
    "claude-opus-4-8": {"input": 15.00, "output": 75.00},
}

_DEFAULT_GENERATION_MODEL = "claude-sonnet-4-6"
_DEFAULT_HEALING_MODEL = "claude-haiku-4-5-20251001"


def _cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    tier = _PRICING.get(model, {"input": 3.00, "output": 15.00})
    return (input_tokens * tier["input"] + output_tokens * tier["output"]) / 1_000_000


class AnthropicProvider(ModelProvider):
    """Anthropic Claude provider for BYOK enterprise deployments.

    Env vars:
      ANTHROPIC_API_KEY            — required
      CHERENKOV_ANTHROPIC_MODEL    — override generation model (default claude-sonnet-4-6)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model or os.getenv(
            "CHERENKOV_ANTHROPIC_MODEL", _DEFAULT_GENERATION_MODEL
        )

    def _get_client(self):
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc
        return anthropic.Anthropic(api_key=self.api_key)

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        model = (
            os.getenv("CHERENKOV_ANTHROPIC_HEALING_MODEL", _DEFAULT_HEALING_MODEL)
            if request.capability_tier == "small"
            else self.model
        )
        system = "You are an expert API conformance QA assistant."
        user_prompt = request.task
        if request.output_schema:
            user_prompt += (
                f"\n\nRespond with JSON matching this schema:\n"
                f"{json.dumps(request.output_schema, indent=2)}"
            )

        client = self._get_client()
        t0 = time.time()
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        latency_ms = int((time.time() - t0) * 1000)

        raw = message.content[0].text if message.content else ""

        # Extract JSON when schema expected
        if request.output_schema:
            raw = _extract_json(raw)

        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        cost = _cost_usd(model, input_tokens, output_tokens)

        return ReasoningResult(
            content=raw,
            provider="anthropic",
            model=model,
            cost_usd=cost,
            latency_ms=latency_ms,
            cached=False,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            capability_tiers=["small", "deep"],
            requires_egress=True,
            provider_name="anthropic",
        )


def _extract_json(text: str) -> str:
    """Pull the first JSON object or array out of the model response."""
    text = text.strip()
    # Strip markdown fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fenced:
        return fenced.group(1).strip()
    # Direct JSON
    start = next((i for i, c in enumerate(text) if c in "{["), None)
    if start is not None:
        return text[start:]
    return text
