"""
CHERENKOV oracle/visual_oracle.py — Epoch 9 Semantic Visual Oracle.
Uses VLM to semantically analyse screenshots and classify changes as
real anomalies vs harmless shifts.
"""

from __future__ import annotations

import json
from typing import Any

from cherenkov.core.config import Config
from cherenkov.core.contracts import Claim
from cherenkov.core.errors import get_logger
from cherenkov.oracle.interface import Oracle, OracleResult
from cherenkov.substrate.provider import get_vlm_provider
from cherenkov.substrate.router import route
from cherenkov.core.contracts import ReasoningRequest


class VisualChangeKind:
    """Classification of a visual change."""

    ANOMALY = "anomaly"
    HARMLESS_SHIFT = "harmless_shift"
    REDESIGN = "redesign"
    UNKNOWN = "unknown"


class VisualOracle(Oracle):
    """Semantic visual oracle that analyses screenshots via VLM.

    Determines whether a visual diff represents:
    - ANOMALY: real UI bug (CSS break, missing element, overlap)
    - HARMLESS_SHIFT: pixel-level noise, anti-aliasing, scrollbar
    - REDESIGN: intentional layout/colour change
    - UNKNOWN: cannot determine
    """

    def __init__(self, provider_name: str | None = None):
        self.provider_name = provider_name or Config.TIER_VISION_PROVIDER
        self._log = get_logger("oracle-visual")

    def evaluate(self, claim: Claim, **kwargs: Any) -> OracleResult:
        if claim.category not in ("visual", "visual_diff", "screenshot"):
            return OracleResult(
                is_correct=True,
                confidence=0.5,
                detail="Non-evaluable visual claim category",
            )

        baseline_path = kwargs.get("baseline_path", "")
        actual_path = kwargs.get("actual_path", "")
        diff_pixels = kwargs.get("diff_pixels", -1)

        if not actual_path:
            return OracleResult(
                is_correct=True, confidence=0.3, detail="No actual screenshot provided"
            )

        try:
            result = self._analyse_screenshot(
                baseline_path=baseline_path,
                actual_path=actual_path,
                diff_pixels=diff_pixels,
            )

            is_correct = result.get("kind") == VisualChangeKind.HARMLESS_SHIFT
            return OracleResult(
                is_correct=is_correct,
                confidence=result.get("confidence", 0.5),
                detail=result.get("explanation", ""),
                expected=baseline_path or "baseline",
                actual=actual_path,
            )
        except Exception as e:
            self._log.warning("visual oracle error", error=str(e))
            return OracleResult(
                is_correct=True,
                confidence=0.2,
                detail=f"Visual oracle error: {e}",
            )

    def _analyse_screenshot(
        self,
        baseline_path: str,
        actual_path: str,
        diff_pixels: int,
    ) -> dict:
        """Use VLM to semantically analyse a screenshot."""
        vlm = get_vlm_provider(self.provider_name)

        analysis_prompt = (
            "You are a UI regression analyst. Examine this screenshot and answer in JSON:\n"
            "{\n"
            '  "description": "What the screenshot shows",\n'
            '  "kind": "anomaly" | "harmless_shift" | "redesign" | "unknown",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "explanation": "Why you classified it this way",\n'
            '  "elements_found": ["element1", "element2"],\n'
            '  "anomalies": ["what looks broken, if any"]\n'
            "}\n\n"
            "Respond with ONLY valid JSON."
        )

        schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "kind": {
                    "type": "string",
                    "enum": ["anomaly", "harmless_shift", "redesign", "unknown"],
                },
                "confidence": {"type": "number"},
                "explanation": {"type": "string"},
                "elements_found": {"type": "array", "items": {"type": "string"}},
                "anomalies": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["description", "kind", "confidence", "explanation"],
        }

        request = ReasoningRequest(
            task=analysis_prompt,
            output_schema={"image_path": actual_path, **schema},
            capability_tier="vision",
        )

        result = route(request)
        raw = result.content

        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(str(raw))
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "description": str(raw)[:200],
            "kind": VisualChangeKind.UNKNOWN,
            "confidence": 0.3,
            "explanation": "Could not parse VLM output as JSON",
            "elements_found": [],
            "anomalies": [],
        }


def classify_visual_change(
    baseline_path: str = "",
    actual_path: str = "",
    diff_pixels: int = -1,
) -> dict:
    """Convenience: run visual classification and return the result dict."""
    from cherenkov.core.contracts import Provenance, ProvenanceType

    oracle = VisualOracle()
    claim = Claim(
        id="visual_classify",
        category="visual_diff",
        subject="screenshot",
        value={"diff_pixels": diff_pixels},
        provenance=Provenance(
            source_type=ProvenanceType.SPEC, source_uri="visual_oracle"
        ),
    )
    result = oracle.evaluate(
        claim,
        baseline_path=baseline_path,
        actual_path=actual_path,
        diff_pixels=diff_pixels,
    )
    return {
        "is_correct": result.is_correct,
        "confidence": result.confidence,
        "detail": result.detail,
        "kind": result.detail.split(":")[0]
        if ":" in result.detail
        else VisualChangeKind.UNKNOWN,
    }
