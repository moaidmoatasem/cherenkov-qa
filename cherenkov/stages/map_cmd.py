"""
cherenkov/stages/map_cmd.py — E2-6: cherenkov map command.

Build + inspect the Truth Model for a target from all configured sources.
"""

from __future__ import annotations

from datetime import datetime, timezone

from cherenkov.core.truth_model import (
    TruthModel,
    GraphNode,
    NodeType,
    GraphEdge,
    EdgeType,
    Claim as TMClaim,
    Provenance as TMProvenance,
)
from cherenkov.truth.sources.interface import SourceAdapter
from cherenkov.truth.sources.openapi import OpenAPISourceAdapter
from cherenkov.truth.sources.traffic import TrafficSourceAdapter
from cherenkov.truth.sources.db_schema import DBSchemaSourceAdapter


def _to_tm_claim(contract_claim) -> TMClaim:
    """Convert a contracts.Claim to a truth_model.Claim."""
    prov = contract_claim.provenance
    return TMClaim(
        predicate=f"{contract_claim.category}:{contract_claim.subject}",
        value=contract_claim.value,
        provenance=TMProvenance(
            source_id=prov.source_uri,
            source_type=prov.source_type.value,
            source_location=prov.source_uri,
            extracted_at=datetime.now(timezone.utc),
            confidence=1.0,
            detail=prov.details.get("type", ""),
        ),
    )


def _adapter_for_source_type(source_type: str) -> SourceAdapter:
    mapping = {
        "openapi": OpenAPISourceAdapter,
        "traffic": TrafficSourceAdapter,
        "db_schema": DBSchemaSourceAdapter,
    }
    cls = mapping.get(source_type)
    if cls is None:
        raise ValueError(f"Unknown source type: {source_type}")
    return cls()  # type: ignore


def build_truth_model(sources: dict[str, list[str]]) -> TruthModel:
    """Build a TruthModel from configured sources.

    Args:
        sources: Mapping of source_type -> list of source URIs.
                 E.g. {"openapi": ["./spec.yaml"], "traffic": ["./capture.har"]}
    """
    tm = TruthModel()

    for source_type, uris in sources.items():
        adapter = _adapter_for_source_type(source_type)
        for uri in uris:
            source_id = f"{source_type}:{uri}"
            source_node = GraphNode(
                id=source_id,
                type=NodeType.SOURCE,
                label=f"{source_type}: {uri}",
                properties={"source_type": source_type, "uri": uri},
            )
            tm.add_node(source_node)

            try:
                claims = adapter.discover_claims(uri)
            except FileNotFoundError:
                source_node.properties["error"] = f"File not found: {uri}"
                continue
            except Exception as e:
                source_node.properties["error"] = str(e)
                continue

            for claim in claims:
                node_id = f"{source_type}_{claim.id}"
                node_type = NodeType.ENDPOINT
                if claim.category in ("table", "column", "constraint"):
                    node_type = NodeType.CONSTRAINT
                elif claim.category in (
                    "observed_status",
                    "observed_latency",
                    "observed_headers",
                    "observed_request_body",
                ):
                    node_type = NodeType.ENDPOINT

                tm_claim = _to_tm_claim(claim)
                claim_node = GraphNode(
                    id=node_id,
                    type=node_type,
                    label=claim.subject,
                    properties={"category": claim.category},
                    claims=[tm_claim],
                )
                tm.add_node(claim_node)

                edge = GraphEdge(
                    id=f"{source_id}_to_{node_id}",
                    source_id=source_id,
                    target_id=node_id,
                    type=EdgeType.DERIVED_FROM,
                )
                tm.add_edge(edge)

    return tm


def render_truth_model(tm: TruthModel, detailed: bool = False) -> str:
    """Render a human-readable summary of the Truth Model."""
    lines = []
    lines.append("=" * 64)
    lines.append("  CHERENKOV Truth Model")
    lines.append("=" * 64)

    sources = tm.get_sources()
    endpoints = tm.get_endpoints()
    constraints = tm.get_constraints()
    shapes = tm.get_shapes()

    lines.append(f"\n  Sources:      {len(sources)}")
    for s in sources:
        err = s.properties.get("error")
        err_tag = f"  [ERROR: {err}]" if err else ""
        lines.append(f"    {s.label}{err_tag}")
        edges_from = tm.get_edges_from(s.id)
        lines.append(f"      Claims: {len(edges_from)}")

    lines.append(f"\n  Endpoints:    {len(endpoints)}")
    if detailed and endpoints:
        for ep in endpoints:
            lines.append(f"    {ep.label}")
            for c in ep.claims:
                lines.append(f"      [{c.predicate}]  = {c.value}")
                lines.append(
                    f"        provenance: {c.provenance.source_type} @ {c.provenance.source_location}"
                )

    lines.append(f"\n  Constraints:  {len(constraints)}")
    if detailed and constraints:
        for cn in constraints:
            lines.append(f"    {cn.label}")
            for c in cn.claims:
                lines.append(f"      [{c.predicate}]  = {c.value}")

    lines.append(f"\n  Shapes:       {len(shapes)}")
    lines.append(f"  Edges:        {len(tm.edges)}")

    lines.append("\n" + "=" * 64)
    return "\n".join(lines)


def run_map(sources: dict[str, list[str]] | None = None, detailed: bool = False) -> int:
    """Execute `cherenkov map`."""
    if sources is None:
        from cherenkov.core.config_loader import load_effective_config

        cfg = load_effective_config()
        sources = {}
        specs = cfg.autodetect_spec()
        if specs:
            sources["openapi"] = specs
        traffic = cfg.get("sources.traffic", [])
        if traffic:
            sources["traffic"] = traffic if isinstance(traffic, list) else [traffic]
        db = cfg.get("sources.db_schema", [])
        if db:
            sources["db_schema"] = db if isinstance(db, list) else [db]

    if not sources or all(len(v) == 0 for v in sources.values()):
        print("No sources configured. Run `cherenkov init` first.")
        return 1

    tm = build_truth_model(sources)
    output = render_truth_model(tm, detailed=detailed)
    print(output)
    return 0
