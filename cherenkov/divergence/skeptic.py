"""
CHERENKOV divergence/skeptic.py — E3-1 Skeptic Agent.

Generates divergence hypotheses across the 5-way space (D1–D5) from spec
claims, via the Substrate Router. Never hardcodes a model.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceHypothesis,
    ReasoningRequest,
    Severity,
)
from cherenkov.substrate.router import SubstrateRouter

# JSON Schema the router is asked to return so we can parse it directly.
_HYPOTHESIS_SCHEMA: dict = {
    "type": "object",
    "required": ["hypotheses"],
    "properties": {
        "hypotheses": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "divergence_class",
                    "claim_a",
                    "claim_b",
                    "predicted_evidence",
                    "severity",
                    "repro_steps",
                ],
                "properties": {
                    "divergence_class": {
                        "type": "string",
                        "enum": [c.value for c in DivergenceClass],
                    },
                    "claim_a": {"type": "string"},
                    "claim_b": {"type": "string"},
                    "predicted_evidence": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": [s.value for s in Severity],
                    },
                    "endpoint": {"type": "string"},
                    "repro_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        }
    },
}

_DIVERGENCE_SPACE = """
Five-way divergence space:
  D1_spec_code  — spec claims X; code accepts/returns something different
  D2_code_prod  — code does X in source; prod silently returns Y (env bugs, race conditions)
  D3_ui_spec    — UI/client sends data in a format the spec does not expect
  D4_db_code    — DB enforces a constraint the application code never checks
  D5_spec_prod  — endpoint or shape in the spec no longer exists in production
"""


class SkepticAgent:
    """
    Generates divergence hypotheses from spec claims.

    Uses ReasoningRequest via the Substrate Router — never names a model directly.
    The router decides capability tier → provider by org policy.

    When a Reflector is attached, hypothesise() applies verdict-memory reranking:
    previously rejected hypotheses are suppressed, and patterns matching active
    Idioms are boosted (E7-2).
    """

    def __init__(
        self,
        router: SubstrateRouter | None = None,
        reflector: Any | None = None,
    ) -> None:
        self.router = router or SubstrateRouter("skeptic")
        self.reflector = reflector

    def hypothesise(
        self,
        endpoint: str,
        method: str,
        spec_claims: dict[str, Any],
        context: str = "",
    ) -> list[DivergenceHypothesis]:
        """
        Generate divergence hypotheses for a single endpoint.

        Args:
            endpoint: API path, e.g. "/pet/{petId}"
            method:   HTTP verb, e.g. "GET"
            spec_claims: OpenAPI operation object or any spec fragment
            context:  Optional extra context (traffic observations, known issues)

        Returns:
            List of DivergenceHypothesis, one per plausible divergence found.
            Empty list if the model returns no parseable hypotheses.
        """
        task = self._build_task(endpoint, method, spec_claims, context)
        request = ReasoningRequest(
            task=task,
            output_schema=_HYPOTHESIS_SCHEMA,
            capability_tier="deep",
        )
        result = self.router.route(request)
        hypotheses = self._parse(result.content, endpoint, method)

        if self.reflector is not None and hypotheses:
            hypotheses = self.reflector.rerank(
                hypotheses, endpoint=hypotheses[0].endpoint
            )

        return hypotheses

    def mobile_hypothesize(
        self, app_id: str, screen_name: str, element_id: str
    ) -> dict:
        from cherenkov.agents.pilot import PilotAgent, InMemoryRunner

        runner = InMemoryRunner()
        pilot = PilotAgent(runner)
        intent = f"Verify {element_id} on {screen_name} in {app_id}"
        steps = pilot.run(intent)

        return {
            "app_id": app_id,
            "screen": screen_name,
            "element": element_id,
            "pilot_steps": [vars(s) for s in steps],
            "conclusion": "passed"
            if all(s.status == "done" for s in steps)
            else "failed",
        }

    # ── private ───────────────────────────────────────────────────────────

    def _build_task(
        self,
        endpoint: str,
        method: str,
        spec_claims: dict[str, Any],
        context: str,
    ) -> str:
        spec_json = json.dumps(spec_claims, indent=2)
        ctx_block = f"\nAdditional context:\n{context}" if context else ""
        return (
            f"You are an adversarial QA engineer auditing an API for divergences.\n\n"
            f"{_DIVERGENCE_SPACE}\n"
            f"Target: {method.upper()} {endpoint}\n\n"
            f"OpenAPI spec fragment:\n{spec_json}"
            f"{ctx_block}\n\n"
            "Generate hypotheses for every plausible divergence class.\n"
            "For each hypothesis supply:\n"
            "  claim_a      — what source A asserts (spec, DB schema, etc.)\n"
            "  claim_b      — what source B likely does differently\n"
            "  predicted_evidence — observable HTTP signal if the divergence exists\n"
            "  repro_steps  — minimal ordered steps to verify it\n"
            "  severity     — low|medium|high|critical\n\n"
            "Be adversarial. Assume the spec is incomplete. Surface things humans miss.\n"
            'Return a JSON object with a "hypotheses" array.'
        )

    def _parse(
        self,
        content: str | dict,
        endpoint: str,
        method: str,
    ) -> list[DivergenceHypothesis]:
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                return []

        if not isinstance(content, dict):
            return []

        hypotheses: list[DivergenceHypothesis] = []
        for item in content.get("hypotheses", []):
            try:
                h = DivergenceHypothesis(
                    id=str(uuid.uuid4()),
                    divergence_class=DivergenceClass(item["divergence_class"]),
                    claim_a=item["claim_a"],
                    claim_b=item["claim_b"],
                    predicted_evidence=item["predicted_evidence"],
                    severity=Severity(item.get("severity", "medium")),
                    endpoint=item.get("endpoint") or f"{method.upper()} {endpoint}",
                    repro_steps=item.get("repro_steps", []),
                )
                hypotheses.append(h)
            except (KeyError, ValueError):
                continue

        return hypotheses
