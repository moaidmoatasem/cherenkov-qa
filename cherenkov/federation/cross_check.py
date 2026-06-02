"""E6-2 Cross-service contract check."""
from cherenkov.core.contracts import (
    DivergenceReport, DivergenceClass, Severity, DivergenceEvidence, StageMeta
)
from cherenkov.federation.protocol import TruthFragment

def cross_service_check(a: TruthFragment, b: TruthFragment) -> list[DivergenceReport]:
    """Compare two Truth fragments and detect cross-service breaks."""
    divergences = []
    
    endpoints_a = {(n.properties.get("method"), n.properties.get("path")): n 
                   for n in a.nodes if n.properties.get("method")}
    endpoints_b = {(n.properties.get("method"), n.properties.get("path")): n 
                   for n in b.nodes if n.properties.get("method")}
    
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
                )
            )
    
    return divergences