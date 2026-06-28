"""
test_egress_policy.py — Comprehensive tests for egress policy enforcement (Issue #34).

Tests the sovereignty dial: egress=none|internal|any with property-driven provider checks.
"""

import unittest
import os
from unittest.mock import patch, MagicMock

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.errors import EgressError
from cherenkov.core.settings import get_settings
from cherenkov.substrate.router import SubstrateRouter
from cherenkov.substrate.provider import ProviderCapabilities


def _make_mock_provider(
    name: str,
    requires_egress: bool = False,
    succeed: bool = True,
    result_content: str = '{"ok": true}',
) -> MagicMock:
    """Helper to create mock providers with specific capabilities."""
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


class TestEgressPolicy(unittest.TestCase):
    """Comprehensive tests for egress policy enforcement."""

    def setUp(self):
        self.router = SubstrateRouter(run_id="test-egress")
        self._retry_patcher = patch(
            "cherenkov.substrate.router.with_retry",
            side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs),
        )
        self._retry_patcher.start()

    def tearDown(self):
        self._retry_patcher.stop()

    def test_default_egress_policy_is_internal(self):
        """AC4: Verify default policy is 'internal' when env var is unset."""
        # This test runs in a fresh process state
        self.assertEqual(get_settings().EGRESS, "internal")

    def test_egress_value_defaults_to_internal(self):
        """get_settings().EGRESS defaults to internal when CHERENKOV_EGRESS is not set."""
        self.assertEqual(get_settings().EGRESS, "internal")

    @patch("cherenkov.substrate.router.provider_for_tier")
    def test_egress_none_blocks_external_provider(self, mock_provider_for_tier):
        """AC1: egress=none blocks ALL providers that declare requires_egress=True."""
        external_provider = _make_mock_provider("openai", requires_egress=True)
        mock_provider_for_tier.return_value = external_provider

        with patch.object(get_settings(), "EGRESS", "none"):
            request = ReasoningRequest(task="test", capability_tier="small")

            with self.assertRaises(EgressError) as ctx:
                self.router.route(request)

            # Verify the error message and that generate() was never called
            self.assertIn("EGRESS policy is 'none'", str(ctx.exception))
            self.assertIn("requires egress", str(ctx.exception))
            external_provider.generate.assert_not_called()

    @patch("cherenkov.substrate.router.provider_for_tier")
    def test_egress_none_allows_local_provider(self, mock_provider_for_tier):
        """AC1: egress=none allows local providers (requires_egress=False)."""
        local_provider = _make_mock_provider("ollama", requires_egress=False)
        mock_provider_for_tier.return_value = local_provider

        with patch.object(get_settings(), "EGRESS", "none"):
            request = ReasoningRequest(task="test", capability_tier="small")
            result = self.router.route(request)

            self.assertEqual(result.provider, "ollama")
            local_provider.generate.assert_called_once()

    @patch("cherenkov.substrate.router.provider_for_tier")
    def test_egress_internal_allows_local_provider(self, mock_provider_for_tier):
        """AC2: egress=internal (default) allows local providers."""
        local_provider = _make_mock_provider("ollama", requires_egress=False)
        mock_provider_for_tier.return_value = local_provider

        # Default policy is "internal", no need to patch
        request = ReasoningRequest(task="test", capability_tier="small")
        result = self.router.route(request)

        self.assertEqual(result.provider, "ollama")
        local_provider.generate.assert_called_once()

    @patch("cherenkov.substrate.router.provider_for_tier")
    def test_egress_internal_blocks_external_provider(self, mock_provider_for_tier):
        """AC2: egress=internal blocks external providers."""
        external_provider = _make_mock_provider("openai", requires_egress=True)
        mock_provider_for_tier.return_value = external_provider

        request = ReasoningRequest(task="test", capability_tier="small")

        with self.assertRaises(EgressError) as ctx:
            self.router.route(request)

        self.assertIn("EGRESS policy is 'internal'", str(ctx.exception))
        self.assertIn("only local providers allowed", str(ctx.exception))
        external_provider.generate.assert_not_called()

    @patch("cherenkov.substrate.router.provider_for_tier")
    def test_egress_any_allows_external_provider(self, mock_provider_for_tier):
        """AC3: egress=any allows external providers through."""
        external_provider = _make_mock_provider("openai", requires_egress=True)
        mock_provider_for_tier.return_value = external_provider

        with patch.object(get_settings(), "EGRESS", "any"):
            request = ReasoningRequest(task="test", capability_tier="small")
            result = self.router.route(request)

            self.assertEqual(result.provider, "openai")
            external_provider.generate.assert_called_once()

    @patch.object(get_settings(), "FALLBACK_ENABLED", True)
    @patch.object(get_settings(), "FALLBACK_PROVIDER", "openai")
    @patch("cherenkov.substrate.router.provider_for_tier")
    @patch("cherenkov.substrate.router.get_provider")
    def test_fallback_egress_enforcement_internal_policy(
        self, mock_get_provider, mock_provider_for_tier
    ):
        """AC4: Policy is enforced for fallback provider on spillover under internal policy."""
        # Primary provider (local) fails, fallback (external) should be blocked
        failing_local = _make_mock_provider(
            "ollama", requires_egress=False, succeed=False
        )
        external_fallback = _make_mock_provider("openai", requires_egress=True)

        mock_provider_for_tier.return_value = failing_local

        def get_provider_side_effect(name: str):
            if name == "openai":
                return external_fallback
            return failing_local

        mock_get_provider.side_effect = get_provider_side_effect

        request = ReasoningRequest(task="test", capability_tier="small")

        with self.assertRaises(EgressError) as ctx:
            self.router.route(request)

        # Verify primary failed and fallback was attempted but blocked by egress
        failing_local.generate.assert_called_once()
        external_fallback.generate.assert_not_called()
        self.assertIn("EGRESS policy is 'internal'", str(ctx.exception))

    @patch.object(get_settings(), "FALLBACK_ENABLED", True)
    @patch.object(get_settings(), "FALLBACK_PROVIDER", "openai")
    @patch.object(get_settings(), "EGRESS", "any")
    @patch("cherenkov.substrate.router.provider_for_tier")
    @patch("cherenkov.substrate.router.get_provider")
    def test_fallback_egress_enforcement_any_policy(
        self, mock_get_provider, mock_provider_for_tier
    ):
        """AC4: Policy is enforced for fallback provider on spillover under any policy."""
        # Primary provider (local) fails, fallback (external) should succeed under 'any'
        failing_local = _make_mock_provider(
            "ollama", requires_egress=False, succeed=False
        )
        external_fallback = _make_mock_provider("openai", requires_egress=True)

        mock_provider_for_tier.return_value = failing_local

        def get_provider_side_effect(name: str):
            if name == "openai":
                return external_fallback
            return failing_local

        mock_get_provider.side_effect = get_provider_side_effect

        request = ReasoningRequest(task="test", capability_tier="small")
        result = self.router.route(request)

        # Verify primary failed and fallback succeeded
        failing_local.generate.assert_called_once()
        external_fallback.generate.assert_called_once()
        self.assertEqual(result.provider, "openai")

    @patch.object(get_settings(), "FALLBACK_ENABLED", True)
    @patch.object(get_settings(), "FALLBACK_PROVIDER", "openai")
    @patch.object(get_settings(), "EGRESS", "none")
    @patch("cherenkov.substrate.router.provider_for_tier")
    @patch("cherenkov.substrate.router.get_provider")
    def test_fallback_egress_enforcement_none_policy(
        self, mock_get_provider, mock_provider_for_tier
    ):
        """AC4: Policy is enforced for fallback provider on spillover under none policy."""
        # Both primary (external) and fallback (external) should be blocked under 'none'
        failing_external = _make_mock_provider(
            "anthropic", requires_egress=True, succeed=False
        )
        external_fallback = _make_mock_provider("openai", requires_egress=True)

        mock_provider_for_tier.return_value = failing_external

        def get_provider_side_effect(name: str):
            if name == "openai":
                return external_fallback
            return failing_external

        mock_get_provider.side_effect = get_provider_side_effect

        request = ReasoningRequest(task="test", capability_tier="small")

        with self.assertRaises(EgressError) as ctx:
            self.router.route(request)

        # Verify primary was blocked by egress before generate() was called
        failing_external.generate.assert_not_called()
        external_fallback.generate.assert_not_called()
        self.assertIn("EGRESS policy is 'none'", str(ctx.exception))

    def test_property_driven_check_no_hardcoded_names(self):
        """Verify the implementation uses property-driven checks, not hardcoded provider names."""
        # This is a meta-test to verify our implementation
        # Get the directory where this test file is located
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # The router.py file should be in cherenkov/substrate/router.py relative to project root
        router_path = os.path.join(project_root, "cherenkov", "substrate", "router.py")
        with open(router_path, "r") as f:
            router_code = f.read()

        # Should not contain hardcoded provider name checks
        self.assertNotIn('("ollama",)', router_code)
        self.assertNotIn('not in ("ollama",', router_code)
        self.assertNotIn('provider_name == "ollama"', router_code)

        # Should use requires_egress property
        self.assertIn("requires_egress", router_code)
        self.assertIn("_enforce_egress", router_code)


if __name__ == "__main__":
    unittest.main()
