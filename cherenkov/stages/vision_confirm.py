"""
CHERENKOV stages/vision_confirm.py — Epoch 9 Vision-Confirm Pilot.
Pre-click check that uses VLM to verify an element exists in a screenshot
before attempting to interact with it. Kills click-hallucination.
"""
from __future__ import annotations

import json
import time

from cherenkov.core.config import Config
from cherenkov.core.errors import get_logger
from cherenkov.substrate.provider import get_vlm_provider
from cherenkov.substrate.router import route
from cherenkov.core.contracts import ReasoningRequest


class VisionConfirmPilot:
    """Uses VLM to confirm an element exists in a screenshot.

    In the generated Playwright test pipeline, before performing a click(),
    this pilot checks whether the target element is actually visible in the
    current screenshot. If the VLM reports the element is absent, the pilot
    flags a hallucination risk and suggests corrective action.
    """

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("VISION_CONFIRM", run_id)
        self._vlm = get_vlm_provider()

    def confirm_element(
        self,
        screenshot_path: str,
        element_selector: str,
        element_text: str = "",
    ) -> dict:
        """Verify that an element exists in a screenshot.

        Args:
            screenshot_path: Path to the screenshot PNG.
            element_selector: CSS/XPath selector of the target element.
            element_text: Expected text content (optional, for accuracy).

        Returns:
            dict with keys:
              - confirmed (bool): True if element appears present
              - confidence (float): 0.0-1.0
              - description (str): What the VLM sees at the element location
              - hallucination_risk (bool): True if element likely absent
              - suggestion (str): What to do next
        """
        t0 = time.time()

        prompt = (
            "You are a precise UI element detector. Examine this screenshot.\n"
            f"A test wants to interact with: selector='{element_selector}'"
        )
        if element_text:
            prompt += f", text='{element_text}'"

        prompt += (
            "\n\nAnswer in JSON only:\n"
            "{\n"
            '  "element_visible": true/false,\n'
            '  "confidence": 0.0-1.0,\n'
            '  "what_you_see": "Describe what is at that location",\n'
            '  "alternative_selectors": ["suggested", "selectors", "if any"]\n'
            "}"
        )

        schema = {
            "image_path": screenshot_path,
            "type": "object",
            "properties": {
                "element_visible": {"type": "boolean"},
                "confidence": {"type": "number"},
                "what_you_see": {"type": "string"},
                "alternative_selectors": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["element_visible", "confidence", "what_you_see"],
        }

        request = ReasoningRequest(
            task=prompt,
            output_schema=schema,
            capability_tier="vision",
        )

        result = route(request)
        raw = result.content

        parsed = None
        if isinstance(raw, dict):
            parsed = raw
        else:
            try:
                parsed = json.loads(str(raw))
            except (json.JSONDecodeError, TypeError):
                pass

        dt_ms = int((time.time() - t0) * 1000)

        if parsed is None:
            self.log.warning("VLM returned unparseable result", duration_ms=dt_ms)
            return {
                "confirmed": False,
                "confidence": 0.0,
                "description": "Could not parse VLM response",
                "hallucination_risk": True,
                "suggestion": "Manual review recommended — VLM response was unparseable.",
            }

        element_visible = parsed.get("element_visible", False)
        confidence = parsed.get("confidence", 0.0)
        what_you_see = parsed.get("what_you_see", "")
        alternatives = parsed.get("alternative_selectors", [])

        self.log.info(
            "vision confirm result",
            element_visible=element_visible,
            confidence=confidence,
            duration_ms=dt_ms,
        )

        if element_visible and confidence >= 0.6:
            return {
                "confirmed": True,
                "confidence": confidence,
                "description": what_you_see,
                "hallucination_risk": False,
                "suggestion": "Element confirmed — proceed with interaction.",
            }
        elif element_visible and confidence < 0.6:
            return {
                "confirmed": True,
                "confidence": confidence,
                "description": what_you_see,
                "hallucination_risk": True,
                "suggestion": f"Element may be present but low confidence ({confidence:.2f}). "
                              f"Consider using alternative selector: {alternatives[0] if alternatives else element_selector}",
            }
        else:
            suggestion = "Element NOT confirmed in screenshot."
            if alternatives:
                suggestion += f" Try alternative selector: {alternatives[0]}"
            else:
                suggestion += " The element may not be rendered. Check the page state."
            return {
                "confirmed": False,
                "confidence": confidence,
                "description": what_you_see,
                "hallucination_risk": True,
                "suggestion": suggestion,
            }
