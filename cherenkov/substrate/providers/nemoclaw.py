"""
CHERENKOV substrate/providers/nemoclaw.py — NVIDIA NemoClaw provider.

NemoClaw is NVIDIA's open-source stack that runs Nemotron models locally through
the OpenShell runtime.  All inference is on-device (requires_egress=False).
OpenShell adds sandboxing, network/filesystem isolation, and policy approval for
any external access — making it suitable for sensitive conformance workloads.

Default model mapping:
  small  → nemotron-nano-4b    (fast, low VRAM, long-running agents)
  deep   → nemotron-super-49b  (highest accuracy; use for planning / review gates)
  vision → nemotron-vlm-4b     (multimodal; visual regression oracle)
"""

from __future__ import annotations

import json
import time

from cherenkov.core.settings import get_settings
from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.ai.interface import InferenceClient
from cherenkov.substrate.provider import ProviderCapabilities


class NemoClawProvider:
    """NVIDIA NemoClaw substrate provider.

    Wraps NemoClawInferenceClient and routes tier-based requests to the
    appropriate Nemotron model.  Vision requests are forwarded to the
    nemotron-vlm model when the capability tier is "vision".
    """

    requires_egress: bool = False
    provider_name: str = "nemoclaw"

    def __init__(self, client: InferenceClient | None = None) -> None:
        if client is None:
            from cherenkov.ai.nemoclaw_client import NemoClawInferenceClient

            client = NemoClawInferenceClient()
        self.client = client

    def _model_for_tier(self, tier: str) -> str:
        if tier == "small":
            return get_settings().NEMOCLAW_SMALL_MODEL
        if tier == "vision":
            return get_settings().NEMOCLAW_VISION_MODEL
        return get_settings().NEMOCLAW_DEEP_MODEL

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        system_prompt = (
            "You are a logical QA AI assistant specializing in API conformance testing."
        )
        user_prompt = request.task
        model = self._model_for_tier(request.capability_tier)

        t0 = time.time()

        if (
            request.capability_tier == "vision"
            and request.output_schema
            and "image_path" in request.output_schema
        ):
            import base64
            import pathlib

            image_bytes = pathlib.Path(request.output_schema["image_path"]).read_bytes()
            image_data = base64.b64encode(image_bytes).decode()
            content = self.client.complete_vision(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                image_data=image_data,
                model=model,
            )
        elif request.output_schema:
            user_prompt += (
                f"\n\nPlease output JSON matching this schema: "
                f"{json.dumps(request.output_schema)}"
            )
            content = self.client.complete_json(  # type: ignore
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                run_id=request.task[:32] if request.task else None,
            )
        else:
            content = self.client.complete_code(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                run_id=request.task[:32] if request.task else None,
            )

        latency_ms = int((time.time() - t0) * 1000)

        return ReasoningResult(
            content=content,
            provider=self.provider_name,
            model=model,
            cost_usd=0.0,
            latency_ms=latency_ms,
            cached=False,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            capability_tiers=["small", "deep", "vision"],
            requires_egress=False,
            provider_name=self.provider_name,
        )
