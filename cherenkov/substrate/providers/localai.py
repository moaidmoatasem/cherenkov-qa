from __future__ import annotations

import base64
import json
import logging
from typing import Any

import requests

from cherenkov.core.config import Config

logger = logging.getLogger(__name__)


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


class LocalAIVLMProvider:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.base_url = (base_url or Config.VLM_LOCALAI_URL).rstrip("/")
        self.model = model or Config.VLM_LOCALAI_MODEL

    def describe_image(self, image_path: str, prompt: str = "") -> str:
        image_data = _encode_image(image_path)
        user_prompt = prompt or "Describe this image in detail."
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_data}"},
                        },
                    ],
                }
            ],
            "max_tokens": 512,
        }
        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def compare_images(self, baseline_path: str, actual_path: str) -> dict[str, Any]:
        baseline_b64 = _encode_image(baseline_path)
        actual_b64 = _encode_image(actual_path)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Compare these two images. "
                                "Describe the visual differences and classify the kind of change. "
                                "Output JSON with keys: description, kind (ANOMALY|HARMLESS_SHIFT|REDESIGN|UNKNOWN), confidence (0-1)"
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{baseline_b64}"
                            },
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{actual_b64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 512,
        }
        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except (json.JSONDecodeError, KeyError, IndexError):
            return {
                "description": content,
                "kind": "UNKNOWN",
                "confidence": 0.0,
            }

    def health(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/readyz", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False
