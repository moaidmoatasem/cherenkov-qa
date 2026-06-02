"""Tests for E6-2 Cross-service contract check."""
import pytest
from cherenkov.core.contracts import DivergenceClass, Severity
from cherenkov.core.truth_model import TruthModel, GraphNode, NodeType, GraphEdge, EdgeType
from cherenkov.federation.protocol import TruthFragment
from cherenkov.federation.cross_check import cross_service_check

def make_endpoint_node(method: str, path: str) -> GraphNode:
    """Helper to create an endpoint node."""
    return GraphNode(
        id=f"ep-{method.lower()}-{path.replace('/', '-')}",
        type=NodeType.ENDPOINT,
        label=f"{method} {path}",
        properties={"method": method, "path": path},
    )

def test_identical_fragments_no_divergence():
    """Identical fragments should return empty divergence list."""
    node = make_endpoint_node("GET", "/users")
    
    frag_a = TruthFragment(
        service_id="api-a",
        produced_at="2026-06-03T00:00:00Z",
        nodes=[node],
    )
    
    frag_b = TruthFragment(
        service_id="api-b",
        produced_at="2026-06-03T00:00:00Z",
        nodes=[node],
    )
    
    divergences = cross_service_check(frag_a, frag_b)
    assert divergences == []

def test_endpoint_missing_in_b():
    """Endpoint present in A but missing in B should yield D5_SPEC_PROD."""
    node_get = make_endpoint_node("GET", "/users")
    node_post = make_endpoint_node("POST", "/users")
    
    frag_a = TruthFragment(
        service_id="api-a",
        produced_at="2026-06-03T00:00:00Z",
        nodes=[node_get, node_post],
    )
    
    # B is missing POST /users
    frag_b = TruthFragment(
        service_id="api-b",
        produced_at="2026-06-03T00:00:00Z",
        nodes=[node_get],
    )
    
    divergences = cross_service_check(frag_a, frag_b)
    assert len(divergences) == 1
    assert divergences[0].divergence_class == DivergenceClass.D5_SPEC_PROD
    assert divergences[0].endpoint == "POST /users"
    assert "missing" in divergences[0].claim_b
    assert divergences[0].severity == Severity.CRITICAL

def test_multiple_endpoints_partial_match():
    """Test detection of multiple endpoint mismatches."""
    node_get = make_endpoint_node("GET", "/users")
    node_post = make_endpoint_node("POST", "/users")
    node_delete = make_endpoint_node("DELETE", "/users/{id}")
    
    frag_a = TruthFragment(
        service_id="api-a",
        produced_at="2026-06-03T00:00:00Z",
        nodes=[node_get, node_post, node_delete],
    )
    
    frag_b = TruthFragment(
        service_id="api-b",
        produced_at="2026-06-03T00:00:00Z",
        nodes=[node_get],  # Only GET
    )
    
    divergences = cross_service_check(frag_a, frag_b)
    assert len(divergences) == 2
    methods = [d.endpoint for d in divergences if d.endpoint]
    assert any("POST" in m for m in methods)
    assert any("DELETE" in m for m in methods)

def test_empty_fragments():
    """Empty fragments should have no divergences."""
    frag_a = TruthFragment(
        service_id="api-a",
        produced_at="2026-06-03T00:00:00Z",
        nodes=[],
    )
    
    frag_b = TruthFragment(
        service_id="api-b",
        produced_at="2026-06-03T00:00:00Z",
        nodes=[],
    )
    
    divergences = cross_service_check(frag_a, frag_b)
    assert divergences == []