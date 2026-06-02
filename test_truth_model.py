"""
test_truth_model.py — Unit tests for Truth Model graph schema (E2-2).

Tests node/edge creation, provenance tracking, serialisation round-trip,
and query methods.
"""
import unittest
from datetime import datetime, timezone

from cherenkov.core.truth_model import (
    NodeType,
    EdgeType,
    Provenance,
    Claim,
    GraphNode,
    GraphEdge,
    TruthModel,
)


class TestTruthModel(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
        self.prov = Provenance(
            source_id="source:openapi",
            source_type="openapi_spec",
            source_location="./stripe_spec.json",
            extracted_at=self.now,
            confidence=1.0,
            detail="Parsed operation object",
        )
        self.truth = TruthModel()

    def _add_sample_endpoint(self):
        node = GraphNode(
            id="endpoint:GET:/users",
            type=NodeType.ENDPOINT,
            label="GET /users",
            properties={"path": "/users", "method": "GET"},
            claims=[
                Claim(
                    predicate="returns_status",
                    value=200,
                    provenance=self.prov,
                )
            ],
        )
        self.truth.add_node(node)
        return node

    def _add_sample_shape(self):
        node = GraphNode(
            id="shape:User",
            type=NodeType.SHAPE,
            label="User",
            properties={"type": "object"},
            claims=[
                Claim(
                    predicate="has_field",
                    value="id",
                    provenance=self.prov,
                )
            ],
        )
        self.truth.add_node(node)
        return node

    def _add_sample_source(self):
        node = GraphNode(
            id="source:openapi",
            type=NodeType.SOURCE,
            label="OpenAPI Spec: stripe_spec.json",
            properties={"path": "./stripe_spec.json"},
        )
        self.truth.add_node(node)
        return node

    def test_add_and_get_node(self):
        node = self._add_sample_endpoint()
        got = self.truth.get_node("endpoint:GET:/users")
        self.assertIsNotNone(got)
        self.assertEqual(got.id, node.id)
        self.assertEqual(got.type, NodeType.ENDPOINT)
        self.assertEqual(got.label, "GET /users")

    def test_add_and_get_edge(self):
        self._add_sample_endpoint()
        self._add_sample_shape()
        edge = GraphEdge(
            id="edge:GET:/users:User",
            source_id="endpoint:GET:/users",
            target_id="shape:User",
            type=EdgeType.HAS_RESPONSE,
            claims=[
                Claim(
                    predicate="returns",
                    value="User",
                    provenance=self.prov,
                )
            ],
        )
        self.truth.add_edge(edge)
        self.assertEqual(len(self.truth.edges), 1)

        outgoing = self.truth.get_edges_from("endpoint:GET:/users")
        self.assertEqual(len(outgoing), 1)
        self.assertEqual(outgoing[0].type, EdgeType.HAS_RESPONSE)

        incoming = self.truth.get_edges_to("shape:User")
        self.assertEqual(len(incoming), 1)
        self.assertEqual(incoming[0].source_id, "endpoint:GET:/users")

    def test_node_type_filtering(self):
        self._add_sample_endpoint()
        self._add_sample_shape()
        self._add_sample_source()

        self.assertEqual(len(self.truth.get_endpoints()), 1)
        self.assertEqual(len(self.truth.get_shapes()), 1)
        self.assertEqual(len(self.truth.get_sources()), 1)
        self.assertEqual(len(self.truth.get_constraints()), 0)

    def test_claims_have_provenance(self):
        self._add_sample_endpoint()
        node = self.truth.get_node("endpoint:GET:/users")
        self.assertEqual(len(node.claims), 1)
        claim = node.claims[0]
        self.assertEqual(claim.predicate, "returns_status")
        self.assertEqual(claim.value, 200)
        self.assertEqual(claim.provenance.source_id, "source:openapi")
        self.assertEqual(claim.provenance.source_type, "openapi_spec")
        self.assertEqual(claim.provenance.source_location, "./stripe_spec.json")
        self.assertEqual(claim.provenance.confidence, 1.0)
        self.assertEqual(claim.provenance.detail, "Parsed operation object")

    def test_get_claims_by_source(self):
        self._add_sample_endpoint()
        self._add_sample_shape()
        self._add_sample_source()

        edge = GraphEdge(
            id="edge:test",
            source_id="endpoint:GET:/users",
            target_id="shape:User",
            type=EdgeType.HAS_RESPONSE,
            claims=[
                Claim(
                    predicate="returns",
                    value="User",
                    provenance=self.prov,
                )
            ],
        )
        self.truth.add_edge(edge)

        claims = self.truth.get_claims_by_source("source:openapi")
        self.assertEqual(len(claims), 3)  # 2 node claims + 1 edge claim
        locations = [loc for loc, _ in claims]
        self.assertIn("node:endpoint:GET:/users", locations)
        self.assertIn("node:shape:User", locations)
        self.assertIn("edge:edge:test", locations)

    def test_get_claims_by_source_empty(self):
        claims = self.truth.get_claims_by_source("nonexistent")
        self.assertEqual(claims, [])

    def test_get_node_nonexistent(self):
        self.assertIsNone(self.truth.get_node("nonexistent"))

    def test_serialisation_round_trip(self):
        self._add_sample_endpoint()
        self._add_sample_shape()

        edge = GraphEdge(
            id="edge:GET:/users:User",
            source_id="endpoint:GET:/users",
            target_id="shape:User",
            type=EdgeType.HAS_RESPONSE,
        )
        self.truth.add_edge(edge)

        json_str = self.truth.model_dump_json(indent=2)
        restored = TruthModel.model_validate_json(json_str)

        self.assertEqual(len(restored.nodes), 2)
        self.assertEqual(len(restored.edges), 1)
        self.assertIsNotNone(restored.get_node("endpoint:GET:/users"))
        self.assertIsNotNone(restored.get_node("shape:User"))
        self.assertEqual(restored.edges[0].type, EdgeType.HAS_RESPONSE)

        endpoint = restored.get_node("endpoint:GET:/users")
        self.assertEqual(endpoint.claims[0].value, 200)
        self.assertEqual(endpoint.claims[0].provenance.source_id, "source:openapi")

    def test_serialisation_preserves_datetime(self):
        self._add_sample_endpoint()
        json_str = self.truth.model_dump_json()
        restored = TruthModel.model_validate_json(json_str)
        endpoint = restored.get_node("endpoint:GET:/users")
        restored_dt = endpoint.claims[0].provenance.extracted_at
        self.assertEqual(
            restored_dt.isoformat(),
            self.now.isoformat(),
        )

    def test_empty_truth_model(self):
        tm = TruthModel()
        self.assertEqual(len(tm.nodes), 0)
        self.assertEqual(len(tm.edges), 0)
        self.assertEqual(tm.schema_version, 1)
        self.assertEqual(tm.get_endpoints(), [])
        self.assertEqual(tm.get_shapes(), [])
        self.assertEqual(tm.get_sources(), [])
        self.assertEqual(tm.get_constraints(), [])
        json_str = tm.model_dump_json()
        restored = TruthModel.model_validate_json(json_str)
        self.assertEqual(len(restored.nodes), 0)

    def test_claim_with_none_value(self):
        node = GraphNode(
            id="shape:NullableField",
            type=NodeType.SHAPE,
            label="NullableField",
            claims=[
                Claim(
                    predicate="nullable",
                    value=None,
                    provenance=self.prov,
                )
            ],
        )
        self.truth.add_node(node)
        json_str = self.truth.model_dump_json()
        restored = TruthModel.model_validate_json(json_str)
        claim = restored.get_node("shape:NullableField").claims[0]
        self.assertIsNone(claim.value)

    def test_multiple_claims_same_node(self):
        node = GraphNode(
            id="endpoint:POST:/users",
            type=NodeType.ENDPOINT,
            label="POST /users",
            claims=[
                Claim(predicate="returns_status", value=201, provenance=self.prov),
                Claim(predicate="returns_status", value=400, provenance=self.prov),
                Claim(predicate="has_auth", value=True, provenance=self.prov),
            ],
        )
        self.truth.add_node(node)
        self.assertEqual(len(self.truth.get_node("endpoint:POST:/users").claims), 3)

    def test_edges_from_and_to_empty(self):
        self.assertEqual(self.truth.get_edges_from("nowhere"), [])
        self.assertEqual(self.truth.get_edges_to("nowhere"), [])

    def test_node_properties(self):
        node = GraphNode(
            id="shape:Account",
            type=NodeType.SHAPE,
            label="Account",
            properties={
                "type": "object",
                "required": ["id", "email"],
            },
        )
        self.truth.add_node(node)
        got = self.truth.get_node("shape:Account")
        self.assertEqual(got.properties["type"], "object")
        self.assertIn("email", got.properties["required"])


if __name__ == "__main__":
    unittest.main()
