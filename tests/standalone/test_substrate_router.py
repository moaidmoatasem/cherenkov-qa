from cherenkov.core.settings import get_settings
"""
test_substrate_router.py — Unit tests for the Substrate Router (Epoch 1).

Tests routing by capability tier + egress policy, and fallback/spillover on failure.
"""

import unittest
from unittest.mock import patch, MagicMock

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.errors import EgressError, AllProvidersFailedError
from cherenkov.substrate.router import SubstrateRouter
from cherenkov.substrate.provider import ProviderCapabilities


def _make_mock_provider(
    name: str,
    requires_egress: bool = False,
    succeed: bool = True,
    result_content: str = '{"ok": true}',
) -> MagicMock:
    provider = MagicMock()
    provider.capabilities.return_value = ProviderCapabilities(
        capability_tiers=["small", "deep"],
        requires_egress=requires_egress,
        provider_name=name,
    )
    if succeed:
        provider.generate.return_value = ReasoningResult(
            content=result_content,
            provider=name,
            model="test-model",
            cost_usd=0.0,
            latency_ms=10,
            cached=False,
        )
    else:
        provider.generate.side_effect = RuntimeError(f"{name} failed")
    return provider


class TestSubstrateRouter(unittest.TestCase):
    def setUp(self):
        self.router = SubstrateRouter(run_id="test-run")

    @patch("cherenkov.substrate.router.provider_for_tier")
    @patch("cherenkov.substrate.router.get_provider")
    def test_routes_to_ollama_for_small_tier(
        self, mock_get_provider, mock_provider_for_tier
    ):
        mock_provider = _make_mock_provider("ollama")
        mock_provider_for_tier.return_value = mock_provider
        mock_get_provider.return_value = mock_provider

        request = ReasoningRequest(
            task="write a test",
            capability_tier="small",
        )
        result = self.router.route(request)

        self.assertEqual(result.provider, "ollama")
        mock_provider_for_tier.assert_called_with("small")

    @patch("cherenkov.substrate.router.provider_for_tier")
    @patch("cherenkov.substrate.router.get_provider")
    def test_routes_to_deep_tier_provider(
        self, mock_get_provider, mock_provider_for_tier
    ):
        mock_provider = _make_mock_provider("ollama")
        mock_provider_for_tier.return_value = mock_provider
        mock_get_provider.return_value = mock_provider

        request = ReasoningRequest(
            task="deep reasoning",
            capability_tier="deep",
        )
        result = self.router.route(request)

        self.assertEqual(result.provider, "ollama")
        mock_provider_for_tier.assert_called_with("deep")

    @patch.object(get_settings(), "EGRESS", "none")
    @patch("cherenkov.substrate.router.provider_for_tier")
    def test_egress_none_blocks_cloud_provider(self, mock_provider_for_tier):
        cloud_provider = _make_mock_provider("openai", requires_egress=True)
        mock_provider_for_tier.return_value = cloud_provider

        request = ReasoningRequest(
            task="call openai",
            capability_tier="small",
        )
        with self.assertRaises(EgressError) as ctx:
            self.router.route(request)
        self.assertIn("EGRESS policy is 'none'", str(ctx.exception))

    @patch.object(get_settings(), "EGRESS", "internal")
    @patch("cherenkov.substrate.router.provider_for_tier")
    def test_egress_internal_blocks_openai(self, mock_provider_for_tier):
        cloud_provider = _make_mock_provider("openai", requires_egress=True)
        mock_provider_for_tier.return_value = cloud_provider

        request = ReasoningRequest(
            task="call openai",
            capability_tier="small",
        )
        with self.assertRaises(EgressError) as ctx:
            self.router.route(request)
        self.assertIn("EGRESS policy is 'internal'", str(ctx.exception))

    @patch.object(get_settings(), "EGRESS", "any")
    @patch("cherenkov.substrate.router.provider_for_tier")
    def test_egress_any_allows_cloud(self, mock_provider_for_tier):
        cloud_provider = _make_mock_provider("openai", requires_egress=True)
        mock_provider_for_tier.return_value = cloud_provider

        request = ReasoningRequest(
            task="call openai",
            capability_tier="small",
        )
        result = self.router.route(request)
        self.assertEqual(result.provider, "openai")

    @patch.object(get_settings(), "FALLBACK_ENABLED", True)
    @patch.object(get_settings(), "FALLBACK_PROVIDER", "openai")
    @patch.object(get_settings(), "EGRESS", "any")
    @patch("cherenkov.substrate.router.provider_for_tier")
    @patch("cherenkov.substrate.router.get_provider")
    def test_fallback_when_primary_fails(
        self, mock_get_provider, mock_provider_for_tier
    ):
        failing_ollama = _make_mock_provider("ollama", succeed=False)
        openai_fallback = _make_mock_provider("openai", requires_egress=True)

        mock_provider_for_tier.return_value = failing_ollama

        def get_provider_side_effect(name: str):
            if name == "openai":
                return openai_fallback
            return failing_ollama

        mock_get_provider.side_effect = get_provider_side_effect

        request = ReasoningRequest(
            task="test fallback",
            capability_tier="small",
        )
        result = self.router.route(request)

        self.assertEqual(result.provider, "openai")
        self.assertEqual(failing_ollama.generate.call_count, 1)
        self.assertEqual(openai_fallback.generate.call_count, 1)

    @patch.object(get_settings(), "FALLBACK_ENABLED", True)
    @patch.object(get_settings(), "FALLBACK_PROVIDER", "ollama")
    @patch("cherenkov.substrate.router.provider_for_tier")
    @patch("cherenkov.substrate.router.get_provider")
    def test_fallback_same_as_primary_raises_error(
        self, mock_get_provider, mock_provider_for_tier
    ):
        failing = _make_mock_provider("ollama", succeed=False)
        mock_provider_for_tier.return_value = failing
        mock_get_provider.return_value = failing

        request = ReasoningRequest(
            task="test same fallback",
            capability_tier="small",
        )
        with self.assertRaises(AllProvidersFailedError):
            self.router.route(request)

    @patch.object(get_settings(), "FALLBACK_ENABLED", False)
    @patch("cherenkov.substrate.router.provider_for_tier")
    def test_no_fallback_when_disabled(self, mock_provider_for_tier):
        failing = _make_mock_provider("ollama", succeed=False)
        mock_provider_for_tier.return_value = failing

        request = ReasoningRequest(
            task="test no fallback",
            capability_tier="small",
        )
        with self.assertRaises(AllProvidersFailedError):
            self.router.route(request)

    @patch.object(get_settings(), "TIER_SMALL_PROVIDER", "openai")
    @patch.object(get_settings(), "EGRESS", "any")
    @patch("cherenkov.substrate.router.provider_for_tier")
    @patch("cherenkov.substrate.router.get_provider")
    def test_switch_provider_by_config_alone(
        self, mock_get_provider, mock_provider_for_tier
    ):
        openai_provider = _make_mock_provider("openai", requires_egress=True)
        mock_provider_for_tier.return_value = openai_provider
        mock_get_provider.return_value = openai_provider

        request = ReasoningRequest(
            task="write a test",
            capability_tier="small",
            output_schema={
                "type": "object",
                "properties": {"code": {"type": "string"}},
            },
        )
        result = self.router.route(request)

        self.assertEqual(result.provider, "openai")
        self.assertEqual(result.model, "test-model")


if __name__ == "__main__":
    unittest.main()
