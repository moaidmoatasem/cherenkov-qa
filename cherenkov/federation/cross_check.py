"""E6-2 Cross-service contract check."""

from cherenkov.core.contracts import (
    DivergenceReport,
    DivergenceClass,
    Severity,
    DivergenceEvidence,
    StageMeta,
)
from cherenkov.federation.protocol import TruthFragment

RESPONSE_PROP_PREFIXES = ("response_", "response")


def _response_props(node) -> dict:
    return {
        k: v
        for k, v in node.properties.items()
        if k.lower().startswith(RESPONSE_PROP_PREFIXES)
    }


def _schema_drift(a, b, key, method, path):
    """Detect same endpoint, different response schema."""
    props_a = _response_props(a)
    props_b = _response_props(b)
    if props_a and props_b and props_a != props_b:
        diff_items = []
        all_keys = set(props_a) | set(props_b)
        for k in sorted(all_keys):
            va = props_a.get(k)
            vb = props_b.get(k)
            if va != vb:
                diff_items.append(f"{k}:{va}!={vb}")
        return DivergenceReport(
            id=f"div-schema-{method}-{path.replace('/', '-')}",
            divergence_class=DivergenceClass.D5_SPEC_PROD,
            claim_a=str(props_a),
            claim_b=str(props_b),
            evidence=DivergenceEvidence(
                request_summary=f"{method} {path}",
                response_actual=str(props_b),
                response_expected=str(props_a),
                diff="; ".join(diff_items),
            ),
            repro_steps=["compare response schemas"],
            severity=Severity.HIGH,
            endpoint=f"{method} {path}",
            metadata=StageMeta(stage="cross_check", schema_version=1),
            scope="cross",
        )
    return None


def _invariant_conflict(a, b, key, method, path):
    """Detect same claim predicate, contradictory values."""
    claims_a = {c.predicate: c for c in a.claims}
    claims_b = {c.predicate: c for c in b.claims}
    shared = set(claims_a) & set(claims_b)
    for pred in sorted(shared):
        va = claims_a[pred].value
        vb = claims_b[pred].value
        if va != vb:
            return DivergenceReport(
                id=f"div-invariant-{method}-{path.replace('/', '-')}-{pred}",
                divergence_class=DivergenceClass.D5_SPEC_PROD,
                claim_a=f"{pred}={va}",
                claim_b=f"{pred}={vb}",
                evidence=DivergenceEvidence(
                    request_summary=f"{method} {path}",
                    response_actual=str(vb),
                    response_expected=str(va),
                    diff=f"invariant {pred}: {va} != {vb}",
                ),
                repro_steps=["compare invariants"],
                severity=Severity.CRITICAL,
                endpoint=f"{method} {path}",
                metadata=StageMeta(stage="cross_check", schema_version=1),
                scope="cross",
            )
    return None


def cross_service_check(a: TruthFragment, b: TruthFragment) -> list[DivergenceReport]:
    """Compare two Truth fragments and detect cross-service breaks."""
    divergences = []

    endpoints_a = {
        (n.properties.get("method"), n.properties.get("path")): n
        for n in a.nodes
        if n.properties.get("method")
    }
    endpoints_b = {
        (n.properties.get("method"), n.properties.get("path")): n
        for n in b.nodes
        if n.properties.get("method")
    }

    for key in endpoints_a:
        if key not in endpoints_b:
            method, path = key
            divergences.append(
                DivergenceReport(
                    id="div-missing",
                    divergence_class=DivergenceClass.D5_SPEC_PROD,
                    claim_a="exists in A",
                    claim_b="missing in B",
                    evidence=DivergenceEvidence(
                        request_summary=f"{method} {path}",
                        response_actual="missing",
                        response_expected="exists",
                        diff="endpoint missing",
                    ),
                    repro_steps=["call"],
                    severity=Severity.CRITICAL,
                    endpoint=f"{method} {path}",
                    metadata=StageMeta(stage="cross_check", schema_version=1),
                    scope="cross",
                )
            )
        else:
            node_a = endpoints_a[key]
            node_b = endpoints_b[key]
            method, path = key

            drift = _schema_drift(node_a, node_b, key, method, path)
            if drift:
                divergences.append(drift)

            conflict = _invariant_conflict(node_a, node_b, key, method, path)
            if conflict:
                divergences.append(conflict)

    return divergences
