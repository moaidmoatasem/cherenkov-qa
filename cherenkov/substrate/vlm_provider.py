"""
CHERENKOV substrate/vlm_provider.py — VLM (Vision Language Model) provider.
Egress-aware vision provider following the ModelProvider Protocol.
Supports local (Ollama with Qwen3-VL etc.) and cloud (OpenAI GPT-4o vision).
"""

from __future__ import annotations

import base64
import json
import time
from pydantic import BaseModel, Field

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.config import Config
from cherenkov.core.errors import get_logger
from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import OllamaInferenceClient


def _encode_image(image_path: str) -> str:
    """Read an image file and return base64-encoded string (no prefix)."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


class VLMProvider:
    """Vision-Language Model provider.

    Supports multimodal prompts with images. Egress-aware: local Ollama
    models can run with egress=none; cloud models require egress=any.
    """

    def __init__(self, client: InferenceClient | None = None):
        self.client = client or OllamaInferenceClient()
        self.log = get_logger("VLM_PROVIDER")

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        """Generate a text response from an image + text prompt.

        The request.task should contain the text prompt.
        If request.output_schema contains an ``image_path`` key, the image
        is loaded from that file path and sent as a vision request.
        Otherwise a plain text completion is used (no image).
        """
        system_prompt = "You are a precise visual analyst."
        user_prompt = request.task

        model = Config.TIER_VISION_MODEL

        image_path = None
        if request.output_schema and "image_path" in request.output_schema:
            image_path = request.output_schema["image_path"]

        t0 = time.time()

        if image_path:
            image_data = _encode_image(image_path)
            content = self.client.complete_vision(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                image_data=image_data,
                model=model,
            )
        else:
            if request.output_schema and "format" in request.output_schema:
                user_prompt += (
                    f"\n\nPlease output JSON matching this schema: "
                    f"{json.dumps(request.output_schema)}"
                )
                content = self.client.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                )
            else:
                content = self.client.complete_code(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                )

        dt_ms = int((time.time() - t0) * 1000)
        provider_name = (
            "ollama" if Config.TIER_VISION_PROVIDER == "ollama" else "openai"
        )

        return ReasoningResult(
            content=content,
            provider=provider_name,
            model=model,
            cost_usd=0.0 if provider_name == "ollama" else 0.01,
            latency_ms=dt_ms,
            cached=False,
        )

    def capabilities(self):
        """Advertise vision capability."""
        from cherenkov.substrate.provider import ProviderCapabilities

        provider_name = Config.TIER_VISION_PROVIDER
        requires_egress = provider_name != "ollama"
        return ProviderCapabilities(
            capability_tiers=["vision"],
            requires_egress=requires_egress,
            provider_name=provider_name,
        )


class VLMResult(BaseModel):
    """Structured result from a VLM analysis."""

    description: str = ""
    elements_found: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    confidence: float = 0.0
