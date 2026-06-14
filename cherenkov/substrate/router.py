"""
CHERENKOV substrate/router.py — Epoch 1 Substrate Router.

Picks a provider per request from capability tier + egress policy;
falls back / spills over on failure.
"""

from __future__ import annotations

import time

from cherenkov.core.contracts import ReasoningRequest, ReasoningResult
from cherenkov.core.config import Config
from cherenkov.core.errors import (
    EgressError,
    AllProvidersFailedError,
    CertificationError,
    get_logger,
)
from cherenkov.substrate.provider import provider_for_tier, get_provider
from cherenkov.substrate.certification import ModelCertificationManager


class SubstrateRouter:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("ROUTER", run_id)
        self._certified_tiers: dict[str, bool] = {}
        self._cert_manager = ModelCertificationManager(run_id=run_id)

    def route(self, request: ReasoningRequest) -> ReasoningResult:
        t0 = time.time()

        primary = provider_for_tier(request.capability_tier)
        primary_name = primary.capabilities().provider_name

        # Enforce model certification (E12 Gold-Set gate)
        if (
            Config.CERTIFICATION_ENABLED
            and request.capability_tier not in self._certified_tiers
        ):
            cert_res = self._cert_manager.certify_tier(request.capability_tier, primary)
            if not cert_res.certified:
                raise CertificationError(
                    f"Model certification failed for tier '{request.capability_tier}' on provider '{primary_name}': {cert_res.detail}"
                )
            self._certified_tiers[request.capability_tier] = True

        self._enforce_egress(primary.capabilities().requires_egress, primary_name)

        last_error: Exception | None = None
        try:
            self.log.info(
                "routing to primary",
                provider=primary_name,
                tier=request.capability_tier,
            )
            return primary.generate(request)
        except Exception as e:
            last_error = e
            self.log.warning("primary failed", provider=primary_name, error=str(e))

        if Config.FALLBACK_ENABLED:
            fallback_name = Config.FALLBACK_PROVIDER
            if fallback_name == primary_name:
                self.log.warning(
                    "fallback same as primary, no spillover possible",
                    fallback=fallback_name,
                )
                raise AllProvidersFailedError(
                    f"Primary provider '{primary_name}' failed and "
                    f"fallback is the same provider. Error: {last_error}"
                ) from last_error

            fallback = get_provider(fallback_name)
            self._enforce_egress(fallback.capabilities().requires_egress, fallback_name)
            try:
                self.log.info(
                    "routing to fallback",
                    fallback=fallback_name,
                    tier=request.capability_tier,
                )
                return fallback.generate(request)
            except Exception as e2:
                last_error = e2
                self.log.warning(
                    "fallback also failed", fallback=fallback_name, error=str(e2)
                )

        dt_ms = int((time.time() - t0) * 1000)
        raise AllProvidersFailedError(
            f"All providers failed for tier={request.capability_tier} "
            f"after {dt_ms}ms. Last error: {last_error}"
        ) from last_error

    def _enforce_egress(self, requires_egress: bool, provider_name: str) -> None:
        if not requires_egress:
            return
        policy = Config.EGRESS
        if policy == "none":
            raise EgressError(
                f"Provider '{provider_name}' requires egress but "
                f"EGRESS policy is '{policy}'"
            )
        if policy == "internal":
            raise EgressError(
                f"Provider '{provider_name}' requires egress but "
                f"EGRESS policy is '{policy}' (only local providers allowed)"
            )
        if policy == "github" and provider_name not in ("github",):
            raise EgressError(
                f"Provider '{provider_name}' blocked — 'github' egress policy only "
                "permits the GitHub Models provider."
            )
        # "external" policy allows any egress provider (ollama, openai, anthropic, github)
        # "none" / "internal" are already handled above


_DEFAULT_ROUTER = SubstrateRouter()


def route(request: ReasoningRequest) -> ReasoningResult:
    return _DEFAULT_ROUTER.route(request)
