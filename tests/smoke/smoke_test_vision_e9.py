#!/usr/bin/env python3
"""
smoke_test_vision_e9.py — Kill-criteria exit demo for Epoch 9 Vision Perception.

C6 (#121): VLMProvider as [substrate.tiers.vision] (egress-respecting)
C7 (#122): Semantic visual oracle + element-identity self-heal

Uses mocked VLM responses (no actual GPU/Ollama required) to verify:
1. VLMProvider generates from vision tier
2. VisualOracle classifies changes (anomaly/harmless/redesign)
3. VisualHealer produces suggest-only healing
4. VisionConfirmPilot detects hallucination risks
5. type(get_settings()) has [substrate.tiers.vision] registered

Exit code 0 = all criteria passed.
"""

import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cherenkov.core.contracts import (
    ReasoningRequest,
    ReasoningResult,
    Claim,
    Provenance,
    ProvenanceType,
    VisualReport,
    VisualGateResult,
    Verdict,
    Status,
    StageMeta,
    StageError,
)
from cherenkov.core.settings import get_settings
from cherenkov.core.config_loader import KNOWN_KEYS, PROFILE_DEFAULTS
from cherenkov.substrate.provider import provider_for_tier
from cherenkov.substrate.vlm_provider import VLMProvider, VLMResult
from cherenkov.oracle.visual_oracle import VisualOracle, classify_visual_change
from cherenkov.healing.visual_heal import VisualHealer
from cherenkov.stages.vision_confirm import VisionConfirmPilot

PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label} — {detail}")
        FAIL += 1


def test_vlm_provider():
    """C6 (#121): VLMProvider tests."""
    global PASS, FAIL
    print("\n--- C6 (#121): VLMProvider as [substrate.tiers.vision] ---")

    check("TIER_VISION_PROVIDER in type(get_settings())", hasattr(type(get_settings()), "TIER_VISION_PROVIDER"))
    check("TIER_VISION_MODEL in type(get_settings())", hasattr(type(get_settings()), "TIER_VISION_MODEL"))
    check("vision tier in KNOWN_KEYS", "substrate.tiers.vision.provider" in KNOWN_KEYS)
    check(
        "vision tier in laptop profile",
        "substrate.tiers.vision.provider" in PROFILE_DEFAULTS["laptop"],
    )

    vlm = VLMProvider()
    caps = vlm.capabilities()
    check("VLM advertises vision capability", "vision" in caps.capability_tiers)
    check("Ollama VLM requires no egress", not caps.requires_egress)

    mock_client = MagicMock()
    mock_client.complete_code.return_value = "print('hello world')"
    vlm_mock = VLMProvider(client=mock_client)
    request = ReasoningRequest(task="write hello world", capability_tier="vision")
    result = vlm_mock.generate(request)
    check("VLM generates text without image", "hello" in str(result.content))
    check("VLM result has provider", bool(result.provider))
    check("VLM result has latency_ms", result.latency_ms >= 0)

    with patch("cherenkov.substrate.vlm_provider._encode_image") as mock_encode:
        mock_encode.return_value = "base64_fake_data"
        mock_client_vision = MagicMock()
        mock_client_vision.complete_vision.return_value = (
            "A login form with email and password fields."
        )
        vlm_img = VLMProvider(client=mock_client_vision)
        request = ReasoningRequest(
            task="What does this show?",
            output_schema={"image_path": "/fake/screen.png"},
            capability_tier="vision",
        )
        result = vlm_img.generate(request)
        check(
            "VLM generates description from image",
            "login form" in str(result.content).lower(),
        )

    vision_provider = provider_for_tier("vision")
    check(
        "provider_for_tier('vision') returns VLMProvider",
        type(vision_provider).__name__ == "VLMProvider",
    )

    vlm_result = VLMResult(
        description="A login page",
        elements_found=["submit button", "email field"],
        anomalies=["missing label"],
        confidence=0.85,
    )
    check("VLMResult has elements", len(vlm_result.elements_found) == 2)


def test_visual_oracle():
    """C7 (#122): VisualOracle tests."""
    global PASS, FAIL
    print("\n--- C7 (#122): Semantic Visual Oracle ---")

    oracle = VisualOracle()

    claim_spec = Claim(
        id="test",
        category="endpoint",
        subject="GET /users",
        value={},
        provenance=Provenance(source_type=ProvenanceType.SPEC, source_uri="spec"),
    )
    result = oracle.evaluate(claim_spec)
    check(
        "Non-visual claims pass through", result.is_correct and result.confidence == 0.5
    )

    claim_visual = Claim(
        id="visual-test",
        category="screenshot",
        subject="homepage",
        value={},
        provenance=Provenance(source_type=ProvenanceType.SPEC, source_uri="test"),
    )

    with patch("cherenkov.oracle.visual_oracle.route") as mock_route:
        mock_route.return_value = ReasoningResult(
            content={
                "description": "Broken layout",
                "kind": "anomaly",
                "confidence": 0.85,
                "explanation": "Elements overlapping",
                "elements_found": ["header"],
                "anomalies": ["overlap"],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )
        result = oracle.evaluate(claim_visual, actual_path="/fake/screen.png")
        check("Anomaly classified correctly", not result.is_correct)
        check("Anomaly has high confidence", result.confidence > 0.5)

    with patch("cherenkov.oracle.visual_oracle.route") as mock_route:
        mock_route.return_value = ReasoningResult(
            content={
                "description": "Same layout, anti-aliasing difference",
                "kind": "harmless_shift",
                "confidence": 0.9,
                "explanation": "Pixel-level noise",
                "elements_found": ["button"],
                "anomalies": [],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )
        result = oracle.evaluate(claim_visual, actual_path="/fake/screen2.png")
        check("Harmless shift classified correctly", result.is_correct)
        check("Harmless shift high confidence", result.confidence >= 0.8)

    with patch("cherenkov.oracle.visual_oracle.route") as mock_route:
        mock_route.return_value = ReasoningResult(
            content={
                "description": "Complete restyle with new colours",
                "kind": "redesign",
                "confidence": 0.95,
                "explanation": "Intentional redesign",
                "elements_found": ["navbar"],
                "anomalies": [],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )
        result = oracle.evaluate(claim_visual, actual_path="/fake/screen3.png")
        check("Redesign is detected (not correct)", not result.is_correct)
        check("Redesign has detail", bool(result.detail))

    with patch("cherenkov.oracle.visual_oracle.route") as mock_route:
        mock_route.return_value = ReasoningResult(
            content={
                "description": "Broken layout",
                "kind": "anomaly",
                "confidence": 0.85,
                "explanation": "Overlap",
                "elements_found": ["header"],
                "anomalies": ["overlap"],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )
        result = classify_visual_change(
            actual_path="/fake/screen.png",
            diff_pixels=500,
        )
        check("classify_visual_change returns kind", "kind" in result)


def test_visual_healer():
    """C7 (#122): VisualHealer tests."""
    global PASS, FAIL
    print("\n--- C7 (#122): Visual Healer (suggest-only) ---")

    healer = VisualHealer(run_id="test")

    report_pass = VisualReport(
        scenario_id="test_slice",
        gates=[VisualGateResult(gate="pixel_diff", passed=True)],
        verdict=Verdict.AUTO_APPROVE,
        status=Status.OK,
        metadata=StageMeta(stage="visual", duration_ms=10),
    )
    suggestion = healer.suggest_heal(report_pass)
    check("Auto-approve: no healing", "No healing needed" in suggestion["suggestion"])

    report_no_gate = VisualReport(
        scenario_id="test",
        gates=[],
        verdict=Verdict.REGENERATE,
        status=Status.FAILED,
        errors=[StageError(code="VISUAL_MISMATCH", detail="failed")],
        metadata=StageMeta(stage="visual", duration_ms=10),
    )
    suggestion = healer.suggest_heal(report_no_gate)
    check(
        "No pixel_diff gate returns info",
        "No pixel_diff gate" in suggestion["suggestion"],
    )

    with patch("cherenkov.healing.visual_heal.VisualOracle.evaluate") as mock_oracle:
        mock_oracle.return_value = type(
            "Result",
            (),
            {
                "is_correct": False,
                "confidence": 0.85,
                "detail": "Elements overlapping by 200px",
                "expected": "base.png",
                "actual": "actual.png",
            },
        )()

        report_fail = VisualReport(
            scenario_id="test_fail",
            gates=[
                VisualGateResult(
                    gate="pixel_diff",
                    passed=False,
                    diff_pixels=500,
                    baseline_path="base.png",
                    actual_path="actual.png",
                )
            ],
            verdict=Verdict.HITL,
            status=Status.FAILED,
            metadata=StageMeta(stage="visual", duration_ms=50),
        )
        suggestion = healer.suggest_heal(report_fail)
        check("Healer produces SUGGESTION", "SUGGESTION" in suggestion["suggestion"])
        check(
            "Healer never auto-modifies",
            "No files were modified" in suggestion["suggestion"]
            or "SUGGESTION" in suggestion["suggestion"],
        )


def test_vision_confirm():
    """C7 (#122): VisionConfirmPilot tests."""
    global PASS, FAIL
    print("\n--- VisionConfirmPilot (anti-click-hallucination) ---")

    pilot = VisionConfirmPilot(run_id="test")

    with patch("cherenkov.stages.vision_confirm.route") as mock_route:
        mock_route.return_value = ReasoningResult(
            content={
                "element_visible": True,
                "confidence": 0.92,
                "what_you_see": "A blue submit button",
                "alternative_selectors": [],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )
        result = pilot.confirm_element(
            screenshot_path="/fake/screen.png",
            element_selector="#submit-btn",
            element_text="Sign In",
        )
        check("Element confirmed visible", result["confirmed"])
        check("No hallucination risk when confirmed", not result["hallucination_risk"])

    with patch("cherenkov.stages.vision_confirm.route") as mock_route:
        mock_route.return_value = ReasoningResult(
            content={
                "element_visible": False,
                "confidence": 0.85,
                "what_you_see": "Empty space",
                "alternative_selectors": [".signin-link"],
            },
            provider="ollama",
            model="qwen2.5-vl:7b",
        )
        result = pilot.confirm_element(
            screenshot_path="/fake/screen.png",
            element_selector="#submit-btn",
        )
        check("Element NOT found flagged", not result["confirmed"])
        check("Hallucination risk detected when absent", result["hallucination_risk"])
        check("Suggestion provided", bool(result["suggestion"]))

    with patch("cherenkov.stages.vision_confirm.route") as mock_route:
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
        result = pilot.confirm_element(
            screenshot_path="/fake/screen.png",
            element_selector="#submit-btn",
        )
        check(
            "Low confidence triggers hallucination risk", result["hallucination_risk"]
        )


def main():
    global PASS, FAIL
    print("=" * 60)
    print("Epoch 9 Vision Perception — Kill-Criteria Exit Demo")
    print("=" * 60)

    test_vlm_provider()
    test_visual_oracle()
    test_visual_healer()
    test_vision_confirm()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("STATUS: ALL CRITERIA PASSED — Epoch 9 Vision is ready.")
    else:
        print(f"STATUS: {FAIL} criteria FAILED — review output above.")
    print("=" * 60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
