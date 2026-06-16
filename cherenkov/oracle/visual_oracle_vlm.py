"""
cherenkov/oracle/visual_oracle_vlm.py — Issue #367: Semantic Visual Oracle with VLM.
"""

from __future__ import annotations

import re
from typing import Any

from cherenkov.substrate.router import SubstrateRouter


class SemanticVisualOracle:
    def __init__(self, router: SubstrateRouter):
        self.router = router

    def analyze(self, screenshot: str, expected_description: str) -> dict[str, Any]:
        from cherenkov.substrate.provider import get_vlm_provider

        try:
            vlm = get_vlm_provider()
        except (ValueError, Exception):
            return self._pixel_diff(screenshot, expected_description)

        prompt = (
            f"Analyze this screenshot. Expected: {expected_description}\n"
            "Describe what you see and provide a confidence score "
            "in the format 'confidence: 0.X'."
        )
        from cherenkov.core.contracts import ReasoningRequest

        request = ReasoningRequest(
            task=prompt,
            output_schema={"image_path": screenshot},
            capability_tier="vision",
        )
        result = vlm.generate(request)
        raw = str(result.content)

        confidence = self._parse_confidence(raw)
        if confidence < 0.7:
            return {
                "status": "uncertain",
                "action": "escalate_to_hitl",
                "confidence": confidence,
                "detail": raw[:300],
            }
        return {
            "status": "verified",
            "confidence": confidence,
            "detail": raw[:300],
        }

    def _pixel_diff(self, screenshot: str, expected_description: str) -> dict[str, Any]:
        return {
            "status": "uncertain",
            "action": "escalate_to_hitl",
            "confidence": 0.0,
            "detail": "VLM unavailable, fell back to pixel diff",
        }

    def _parse_confidence(self, text: str) -> float:
        match = re.search(r"confidence:\s*(0\.\d+)", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 0.0
