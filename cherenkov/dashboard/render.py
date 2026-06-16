"""
cherenkov/dashboard/render.py -- CLI-based renderer for Truth Model + divergences. Epoch 5 (E5-4).

Renders the claim graph and open divergences to the terminal from mock/data.
"""

from __future__ import annotations

from cherenkov.core.contracts import (
    Claim,
    DivergenceReport,
    DivergenceClass,
    DivergenceEvidence,
    Severity,
    Status,
    Provenance,
    ProvenanceType,
    StageMeta,
)
from cherenkov.core.truth_model import TruthModel


def render_truth_model(model: TruthModel | None = None) -> str:
    """Render the Truth Model claim graph.

    If no model is provided, renders mock data.
    """
    if model is None:
        return _render_mock_truth_model()

    lines = ["Truth Model -- Claim Graph", "=" * 60]
    endpoints = model.get_endpoints() if hasattr(model, "get_endpoints") else []

    if not endpoints:
        lines.extend(
            [
                "(no endpoints loaded -- run `cherenkov map` to build the Truth Model)",
            ]
        )
    else:
        for ep in endpoints:
            lines.append(f"\n  {ep.method} {ep.path}")
            lines.append(f"  {'-' * (len(ep.method) + len(ep.path) + 2)}")
            claims = (
                model.get_claims_by_endpoint(ep.path, ep.method)
                if hasattr(model, "get_claims_by_endpoint")
                else []
            )
            for claim in claims:
                src = claim.provenance.source_type.value if claim.provenance else "?"
                lines.append(f"    [{src:>8}] {claim.category}: {claim.subject}")

    return "\n".join(lines)


def render_divergences(reports: list[DivergenceReport] | None = None) -> str:
    """Render divergence reports.

    If no reports are provided, renders mock data.
    """
    if reports is None:
        return _render_mock_divergences()

    if not reports:
        return "No open divergences. The Truth Model is consistent across all sources."

    lines = ["Open Divergences", "=" * 60]
    for r in reports:
        lines.append(f"\n  [{r.severity.upper():>8}] {r.divergence_class.value}")
        lines.append(f"  {'-' * 52}")
        lines.append(f"  Endpoint: {r.endpoint or 'N/A'}")
        lines.append(f"  Claim A:  {r.claim_a}")
        lines.append(f"  Claim B:  {r.claim_b}")
        if r.evidence:
            lines.append(f"  Evidence: {r.evidence.request_summary}")

    return "\n".join(lines)


def render_dashboard(
    model: TruthModel | None = None, reports: list[DivergenceReport] | None = None
) -> str:
    """Render the full dashboard: Truth Model + divergences."""
    parts = [
        "+" + "=" * 78 + "+",
        "|  CHERENKOV DASHBOARD -- Truth Model + Live Divergences         |",
        "+" + "=" * 78 + "+",
    ]
    parts.append("\n" + render_truth_model(model))
    parts.append("\n" + render_divergences(reports))
    return "\n".join(parts)


def run_dashboard() -> int:
    """Execute the dashboard command.

    Returns exit code (0 = success).
    """
    from cherenkov.governance.kpi import GovernanceCollector

    print(render_dashboard())

    try:
        collector = GovernanceCollector(run_id="dashboard")
        report = collector.collect()
        print("\n" + report.render())
    except Exception as e:
        print(f"\n  (Governance KPIs unavailable: {e})")

    print("\n  Note: Dashboard uses mock data when Truth Model is not loaded.")
    print("  Run `cherenkov map` to build from real sources.")
    return 0


# -- Mock data (defer-first, acceptable per E5-4 acceptance criteria) -----

MOCK_CLAIMS = [
    Claim(
        id="c1",
        category="endpoint",
        subject="POST /users",
        value={"description": "Create a new user"},
        provenance=Provenance(
            source_type=ProvenanceType.SPEC, source_uri="stub/target_spec.json"
        ),
    ),
    Claim(
        id="c2",
        category="request",
        subject="POST /users -> body -> email",
        value={"type": "string", "format": "email"},
        provenance=Provenance(
            source_type=ProvenanceType.SPEC, source_uri="stub/target_spec.json"
        ),
    ),
    Claim(
        id="c3",
        category="request",
        subject="POST /users -> body -> password",
        value={"type": "string", "minLength": 8},
        provenance=Provenance(
            source_type=ProvenanceType.SPEC, source_uri="stub/target_spec.json"
        ),
    ),
    Claim(
        id="c4",
        category="response",
        subject="POST /users -> 201",
        value={"type": "object", "properties": {"id": "integer", "email": "string"}},
        provenance=Provenance(
            source_type=ProvenanceType.SPEC, source_uri="stub/target_spec.json"
        ),
    ),
    Claim(
        id="c5",
        category="response",
        subject="POST /users -> 422",
        value={"description": "Validation error"},
        provenance=Provenance(
            source_type=ProvenanceType.SPEC, source_uri="stub/target_spec.json"
        ),
    ),
    Claim(
        id="c6",
        category="endpoint",
        subject="GET /health",
        value={"description": "Health check endpoint"},
        provenance=Provenance(
            source_type=ProvenanceType.SPEC, source_uri="stub/target_spec.json"
        ),
    ),
    Claim(
        id="c7",
        category="response",
        subject="GET /health -> 200",
        value={"type": "object", "properties": {"status": "string"}},
        provenance=Provenance(
            source_type=ProvenanceType.SPEC, source_uri="stub/target_spec.json"
        ),
    ),
]

MOCK_DIVERGENCES = [
    DivergenceReport(
        id="d1",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="POST /users email field has format:email",
        claim_b="Server accepts any string as email (no format validation)",
        endpoint="POST /users",
        severity=Severity.HIGH,
        evidence=DivergenceEvidence(
            request_summary="POST /users email=not-a-real-email -> 201 Created",
            response_actual="201 Created",
            response_expected="422 Unprocessable Entity",
            diff="Expected 422 but received 201",
        ),
        repro_steps=[
            "Send POST /users with email='not-a-real-email'",
            "Server returns 201 instead of 422",
        ],
        status=Status.OK,
        errors=[],
        metadata=StageMeta(stage="divergence", model=None, tokens=0, duration_ms=0),
    ),
    DivergenceReport(
        id="d2",
        divergence_class=DivergenceClass.D5_SPEC_PROD,
        claim_a="GET /v2/users is defined in spec",
        claim_b="Endpoint returns 404 Not Found on production",
        endpoint="GET /v2/users",
        severity=Severity.CRITICAL,
        evidence=DivergenceEvidence(
            request_summary="GET /v2/users -> 404 Not Found",
            response_actual="404 Not Found",
            response_expected="200 OK",
            diff="Endpoint returns 404 but spec defines it",
        ),
        repro_steps=[
            "GET /v2/users against production",
            "Returns 404 although spec defines it",
        ],
        status=Status.OK,
        errors=[],
        metadata=StageMeta(stage="divergence", model=None, tokens=0, duration_ms=0),
    ),
]


def _render_mock_truth_model() -> str:
    lines = [
        "Truth Model -- Claim Graph (mock data)",
        "=" * 60,
    ]
    for claim in MOCK_CLAIMS:
        src = claim.provenance.source_type.value
        lines.append(f"  [{src:>8}] {claim.category}: {claim.subject}")
    return "\n".join(lines)


def _render_mock_divergences() -> str:
    lines = ["Open Divergences (mock data)", "=" * 60]
    for r in MOCK_DIVERGENCES:
        lines.append(f"\n  [{r.severity.upper():>8}] {r.divergence_class.value}")
        lines.append(f"  {'-' * 52}")
        lines.append(f"  Endpoint: {r.endpoint or 'N/A'}")
        lines.append(f"  Claim A:  {r.claim_a}")
        lines.append(f"  Claim B:  {r.claim_b}")
        if r.evidence:
            lines.append(f"  Evidence: {r.evidence.request_summary}")
    return "\n".join(lines)
