from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class VLMResult(BaseModel):
    description: str = ""
    classification: str = ""
    confidence: float = 0.0
    raw: str = ""


class VLMProvider:
    provider_name: str = "ollama"

    def __init__(self, provider_name: str = "ollama"):
        self.provider_name = provider_name

    def describe_image(self, image_path: str, prompt: str = "") -> VLMResult:
        from cherenkov.substrate.vlm_provider import VLMProvider as OldVLM

        old = OldVLM()
        raw = old.describe_image(image_path, prompt)  # type: ignore
        return VLMResult(description=raw, raw=raw)

    def compare_images(self, baseline_path: str, actual_path: str) -> dict[str, Any]:
        from cherenkov.substrate.vlm_provider import VLMProvider as OldVLM

        old = OldVLM()
        return old.compare_images(baseline_path, actual_path)  # type: ignore

    def health(self) -> bool:
        return self.provider_name == "ollama"
