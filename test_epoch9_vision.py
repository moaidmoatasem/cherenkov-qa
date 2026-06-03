"""
test_epoch9_vision.py — Unit tests for Epoch 9 Vision Perception (Issue #90).
Tests: VLMProvider, VisualOracle, VisualHealer, VisionConfirmPilot, substrate vision tier.
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import json

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.config import Config
from cherenkov.core.config_loader import KNOWN_KEYS, PROFILE_DEFAULTS, BUILTIN_DEFAULTS
from cherenkov.substrate.provider import provider_for_tier, get_vlm_provider, ProviderCapabilities
from cherenkov.substrate.vlm_provider import VLMProvider, VLMResult
from cherenkov.oracle.visual_oracle import VisualOracle, classify_visual_change, VisualChangeKind
from cherenkov.healing.visual_heal import VisualHealer
from cherenkov.stages.vision_confirm import VisionConfirmPilot
from cherenkov.core.contracts import (
    VisualReport, VisualGateResult, Verdict, Status, StageMeta, StageError,
    Claim, Provenance, ProvenanceType,
)


def _make_claim(category="screenshot", subject="visual"):
    return Claim(
        id="test",
        category=category,
        subject=subject,
        value={},
        provenance=Provenance(source_type=ProvenanceType.SPEC, source_uri="test"),
    )


class TestVisionTierConfig(unittest.TestCase):
    """Test that [substrate.tiers.vision] is properly registered in config."""

    def test_vision_tier_in_known_keys(self):
        self.assertIn("substrate.tiers.vision.provider", KNOWN_KEYS)
        self.assertIn("substrate.tiers.vision.model", KNOWN_KEYS)

    def test_vision_tier_in_laptop_profile(self):
        self.assertIn("substrate.tiers.vision.provider", PROFILE_DEFAULTS["laptop"])
        self.assertIn("substrate.tiers.vision.model", PROFILE_DEFAULTS["laptop"])

    def test_vision_tier_in_frontier_cloud_profile(self):
        self.assertIn("substrate.tiers.vision.provider", PROFILE_DEFAULTS["frontier-cloud"])
        self.assertIn("substrate.tiers.vision.model", PROFILE_DEFAULTS["frontier-cloud"])

    def test_vision_tier_in_builtin_defaults(self):
        self.assertIn("substrate.tiers.vision.provider", BUILTIN_DEFAULTS)
        self.assertIn("substrate.tiers.vision.model", BUILTIN_DEFAULTS)

    def test_vision_tier_env_vars_exist(self):
        self.assertTrue(hasattr(Config, "TIER_VISION_PROVIDER"))
        self.assertTrue(hasattr(Config, "TIER_VISION_MODEL"))


class TestVLMProvider(unittest.TestCase):
    """Test VLMProvider functionality."""

    def setUp(self):
        self.ollama_vlm = VLMProvider()
        self.mock_client = MagicMock()

    def test_provider_capabilities_advertise_vision(self):
        caps = self.ollama_vlm.capabilities()
        self.assertIn("vision", caps.capability_tiers)
        self.assertEqual(caps.provider_name, "ollama")
        self.assertFalse(caps.requires_egress)

    def test_ollama_vlm_requires_no_egress(self):
        caps = self.ollama_vlm.capabilities()
        self.assertFalse(caps.requires_egress)

    @patch("cherenkov.substrate.vlm_provider._encode_image")
    def test_generate_with_image(self, mock_encode):
        mock_encode.return_value = "base64_fake_image_data"
        client = MagicMock()
        client.complete_vision.return_value = "The screenshot shows a login form with email and password fields."
        vlm = VLMProvider(client=client)

        request = ReasoningRequest(
            task="What does this screenshot show?",
            output_schema={"image_path": "/fake/path/screenshot.png"},
            capability_tier="vision",
        )
        result = vlm.generate(request)

        self.assertIn("login form", str(result.content))
        client.complete_vision.assert_called_once()
        mock_encode.assert_called_once_with("/fake/path/screenshot.png")

    def test_generate_without_image_uses_complete_code(self):
        client = MagicMock()
        client.complete_code.return_value = "print('hello')"
        vlm = VLMProvider(client=client)

        request = ReasoningRequest(
            task="write hello world",
            capability_tier="vision",
        )
        result = vlm.generate(request)

        self.assertEqual(result.content, "print('hello')")
        client.complete_code.assert_called_once()

    def test_generate_respects_vision_model_config(self):
        client = MagicMock()
        client.complete_code.return_value = "ok"
        vlm = VLMProvider(client=client)
        request = ReasoningRequest(task="hi", capability_tier="vision")
        result = vlm.generate(request)
        self.assertEqual(result.provider, "ollama")

    def test_provider_for_tier_vision(self):
        vlm = provider_for_tier("vision")
        self.assertIsInstance(vlm, VLMProvider)

    def test_get_vlm_provider_default(self):
        vlm = get_vlm_provider()
        self.assertIsInstance(vlm, VLMProvider)


class TestVisualOracle(unittest.TestCase):
    """Test the Semantic Visual Oracle."""

    def setUp(self):
        self.oracle = VisualOracle()

    def test_skips_non_visual_claims(self):
        claim = _make_claim(category="endpoint", subject="GET /users")
        result = self.oracle.evaluate(claim)
        self.assertTrue(result.is_correct)
        self.assertEqual(result.confidence, 0.5)

    @patch("cherenkov.oracle.visual_oracle.route")
    def test_anomaly_classification(self, mock_route):
        mock_route.return_value = ReasoningResult(
            content={
                "description": "Broken layout - elements overlapping",
                "kind": "anomaly",
                "confidence": 0.85,
                "explanation": "Header and content sections overlap by 200px",
                "elements_found": ["header", "content"],
                "anomalies": ["header overlap"],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )

        claim = _make_claim(category="screenshot", subject="visual")
        result = self.oracle.evaluate(claim, actual_path="/fake/screen.png")

        self.assertFalse(result.is_correct)
        self.assertGreater(result.confidence, 0.8)

    @patch("cherenkov.oracle.visual_oracle.route")
    def test_harmless_shift_classification(self, mock_route):
        mock_route.return_value = ReasoningResult(
            content={
                "description": "Same layout, slight anti-aliasing difference",
                "kind": "harmless_shift",
                "confidence": 0.9,
                "explanation": "Only pixel-level noise from font rendering",
                "elements_found": ["button"],
                "anomalies": [],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )

        claim = _make_claim(category="screenshot", subject="visual")
        result = self.oracle.evaluate(claim, actual_path="/fake/screen.png")

        self.assertTrue(result.is_correct)

    @patch("cherenkov.oracle.visual_oracle.route")
    def test_redesign_classification(self, mock_route):
        mock_route.return_value = ReasoningResult(
            content={
                "description": "Complete layout restyle with new colour scheme",
                "kind": "redesign",
                "confidence": 0.95,
                "explanation": "Intentional redesign - colours, fonts, and spacing all changed consistently",
                "elements_found": ["navbar", "footer"],
                "anomalies": [],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )

        claim = _make_claim(category="screenshot", subject="visual")
        result = self.oracle.evaluate(claim, actual_path="/fake/screen.png")

        self.assertFalse(result.is_correct)
        self.assertIn("redesign", result.detail.lower())


class TestVisualHealer(unittest.TestCase):
    """Test the Visual Healer (suggest-only)."""

    def setUp(self):
        self.healer = VisualHealer(run_id="test")

    def test_auto_approve_no_healing(self):
        report = VisualReport(
            scenario_id="test_slice",
            gates=[VisualGateResult(gate="pixel_diff", passed=True)],
            verdict=Verdict.AUTO_APPROVE,
            status=Status.OK,
            metadata=StageMeta(stage="visual", duration_ms=10),
        )
        suggestion = self.healer.suggest_heal(report)
        self.assertIn("No healing needed", suggestion)

    def test_no_pixel_diff_gate(self):
        report = VisualReport(
            scenario_id="test",
            gates=[],
            verdict=Verdict.REGENERATE,
            status=Status.FAILED,
            errors=[StageError(code="VISUAL_MISMATCH", detail="failed")],
            metadata=StageMeta(stage="visual", duration_ms=10),
        )
        suggestion = self.healer.suggest_heal(report)
        self.assertIn("No pixel_diff gate", suggestion)

    def test_healing_is_suggest_only_no_files_modified(self):
        report = VisualReport(
            scenario_id="test",
            gates=[VisualGateResult(gate="pixel_diff", passed=False, diff_pixels=500)],
            verdict=Verdict.HITL,
            status=Status.FAILED,
            metadata=StageMeta(stage="visual", duration_ms=10),
        )
        suggestion = self.healer.suggest_heal(report)
        self.assertIn("SUGGESTION", suggestion)
        self.assertIn("No files were modified", suggestion)


class TestVisionConfirmPilot(unittest.TestCase):
    """Test the Vision-Confirm Pilot (anti-click-hallucination)."""

    def setUp(self):
        self.pilot = VisionConfirmPilot(run_id="test")

    @patch("cherenkov.stages.vision_confirm.route")
    def test_element_confirmed(self, mock_route):
        mock_route.return_value = ReasoningResult(
            content={
                "element_visible": True,
                "confidence": 0.92,
                "what_you_see": "A blue submit button labeled 'Sign In'",
                "alternative_selectors": [],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )

        result = self.pilot.confirm_element(
            screenshot_path="/fake/screen.png",
            element_selector="#submit-btn",
            element_text="Sign In",
        )

        self.assertTrue(result["confirmed"])
        self.assertFalse(result["hallucination_risk"])

    @patch("cherenkov.stages.vision_confirm.route")
    def test_element_not_found(self, mock_route):
        mock_route.return_value = ReasoningResult(
            content={
                "element_visible": False,
                "confidence": 0.85,
                "what_you_see": "Empty space where the button should be",
                "alternative_selectors": [".signin-link"],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )

        result = self.pilot.confirm_element(
            screenshot_path="/fake/screen.png",
            element_selector="#submit-btn",
        )

        self.assertFalse(result["confirmed"])
        self.assertTrue(result["hallucination_risk"])
        self.assertIn("NOT confirmed", result["suggestion"])

    @patch("cherenkov.stages.vision_confirm.route")
    def test_low_confidence_triggers_hallucination_warning(self, mock_route):
        mock_route.return_value = ReasoningResult(
            content={
                "element_visible": True,
                "confidence": 0.45,
                "what_you_see": "Something that might be a button",
                "alternative_selectors": ["#real-btn"],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )

        result = self.pilot.confirm_element(
            screenshot_path="/fake/screen.png",
            element_selector="#submit-btn",
        )

        self.assertTrue(result["confirmed"])
        self.assertTrue(result["hallucination_risk"])


class TestVisionTierProviderForTier(unittest.TestCase):
    """Test that provider_for_tier handles the 'vision' tier."""

    def test_provider_for_tier_vision_returns_vlm(self):
        vlm = provider_for_tier("vision")
        from cherenkov.substrate.vlm_provider import VLMProvider
        self.assertIsInstance(vlm, VLMProvider)

    def test_provider_for_tier_vision_capabilities(self):
        vlm = provider_for_tier("vision")
        caps = vlm.capabilities()
        self.assertIn("vision", caps.capability_tiers)


if __name__ == "__main__":
    unittest.main()
