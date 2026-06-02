"""
Truth Model — semantic graph of claims about the target system.

E2-2: endpoints, shapes, constraints, provenance per claim.
Serialisable via Pydantic v2 model_dump_json / model_validate_json.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    ENDPOINT = "endpoint"
    SHAPE = "shape"
    CONSTRAINT = "constraint"
    SOURCE = "source"


class EdgeType(str, Enum):
    HAS_SHAPE = "has_shape"
    HAS_CONSTRAINT = "has_constraint"
    HAS_PARAMETER = "has_parameter"
    HAS_REQUEST_BODY = "has_request_body"
    HAS_RESPONSE = "has_response"
    HAS_PROPERTY = "has_property"
    REFERENCED_BY = "referenced_by"
    DERIVED_FROM = "derived_from"


class Provenance(BaseModel):
    source_id: str = Field(description="ID of the source node")
    source_type: str = Field(description="Type of source (openapi_spec, traffic_capture, db_schema, etc.)")
    source_location: str = Field(description="File path, URL, or description of where the claim came from")
    extracted_at: datetime = Field(description="When the claim was extracted")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in this claim (0-1)")
    detail: str = Field(default="", description="Human-readable detail about extraction")


class Claim(BaseModel):
    predicate: str = Field(description="What is being claimed (e.g. 'returns_status', 'has_field')")
    value: Any = Field(description="The value of the claim")
    provenance: Provenance = Field(description="Where this claim came from")


class GraphNode(BaseModel):
    id: str = Field(description="Unique node identifier")
    type: NodeType = Field(description="Node type")
    label: str = Field(description="Human-readable label")
    properties: dict[str, Any] = Field(default_factory=dict, description="Arbitrary key-value properties")
    claims: list[Claim] = Field(default_factory=list, description="Claims about this node")


class GraphEdge(BaseModel):
    id: str = Field(description="Unique edge identifier")
    source_id: str = Field(description="Source node ID")
    target_id: str = Field(description="Target node ID")
    type: EdgeType = Field(description="Edge type")
    claims: list[Claim] = Field(default_factory=list, description="Claims represented by this edge")
    properties: dict[str, Any] = Field(default_factory=dict, description="Arbitrary key-value properties")


class TruthModel(BaseModel):
    nodes: dict[str, GraphNode] = Field(default_factory=dict, description="Nodes keyed by ID")
    edges: list[GraphEdge] = Field(default_factory=list, description="Directed edges")
    schema_version: int = Field(default=1, description="Schema version for migration")

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    def get_node(self, node_id: str) -> GraphNode | None:
        return self.nodes.get(node_id)

    def get_edges_from(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.target_id == node_id]

    def get_claims_by_source(self, source_id: str) -> list[tuple[str, Claim]]:
        result: list[tuple[str, Claim]] = []
        for nid, node in self.nodes.items():
            for claim in node.claims:
                if claim.provenance.source_id == source_id:
                    result.append((f"node:{nid}", claim))
        for edge in self.edges:
            for claim in edge.claims:
                if claim.provenance.source_id == source_id:
                    result.append((f"edge:{edge.id}", claim))
        return result

    def get_endpoints(self) -> list[GraphNode]:
        return [n for n in self.nodes.values() if n.type == NodeType.ENDPOINT]

    def get_shapes(self) -> list[GraphNode]:
        return [n for n in self.nodes.values() if n.type == NodeType.SHAPE]

    def get_constraints(self) -> list[GraphNode]:
        return [n for n in self.nodes.values() if n.type == NodeType.CONSTRAINT]

    def get_sources(self) -> list[GraphNode]:
        return [n for n in self.nodes.values() if n.type == NodeType.SOURCE]
