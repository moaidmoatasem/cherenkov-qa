"""Tests for cherenkov/federation/protocol.py — Truth Protocol wire format."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceReport,
    Severity,
    StageMeta,
)
from cherenkov.core.truth_model import Claim, GraphNode, NodeType, Provenance
from cherenkov.federation.protocol import (
    PROTOCOL_VERSION,
    DivergenceEnvelope,
    ProtocolMessage,
    ProtocolMessageType,
    TruthFragment,
    dumps,
    loads,
)


def _provenance() -> Provenance:
    return Provenance(
        source_id="spec-1",
        source_type="openapi_spec",
        source_location="petstore.json",
        extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _node(node_id: str = "n1", **properties) -> GraphNode:
    return GraphNode(
        id=node_id,
        type=NodeType.ENDPOINT,
        label="GET /pets",
        properties=properties or {"method": "GET", "path": "/pets"},
        claims=[Claim(predicate="returns_status", value=200, provenance=_provenance())],
    )


def _divergence(report_id: str = "div-1") -> DivergenceReport:
    return DivergenceReport(
        id=report_id,
        divergence_class=DivergenceClass.D5_SPEC_PROD,
        claim_a="spec says 200",
        claim_b="prod returns 500",
        evidence=DivergenceEvidence(
            request_summary="GET /pets",
            response_actual="500",
            response_expected="200",
            diff="status differs",
        ),
        repro_steps=["call GET /pets"],
        severity=Severity.HIGH,
        metadata=StageMeta(stage="cross_check", schema_version=1),
    )


# ── defaults ───────────────────────────────────────────────────────────────────


class TestDefaults:
    def test_fragment_defaults_to_current_protocol_version(self):
        frag = TruthFragment(service_id="svc-a", produced_at="2026-01-01T00:00:00Z")
        assert frag.protocol_version == PROTOCOL_VERSION
        assert frag.nodes == []
        assert frag.edges == []
        assert frag.claims == []

    def test_envelope_defaults(self):
        env = DivergenceEnvelope(
            from_service="a",
            to_service="b",
            correlation_id="c1",
            divergence=_divergence(),
        )
        assert env.protocol_version == PROTOCOL_VERSION
        assert env.signature is None

    def test_message_defaults_to_empty_payload(self):
        msg = ProtocolMessage(type=ProtocolMessageType.ACK)
        assert msg.payload == {}
        assert msg.protocol_version == PROTOCOL_VERSION


# ── dumps ──────────────────────────────────────────────────────────────────────


class TestDumps:
    def test_output_is_compact_and_key_sorted(self):
        msg = ProtocolMessage(type=ProtocolMessageType.ACK, payload={"b": 1, "a": 2})
        raw = dumps(msg)
        assert ", " not in raw and '": ' not in raw
        assert raw.index('"payload"') < raw.index('"protocol_version"') < raw.index('"type"')

    def test_dumps_is_deterministic(self):
        a = ProtocolMessage(type=ProtocolMessageType.ACK, payload={"x": 1, "y": 2})
        b = ProtocolMessage(type=ProtocolMessageType.ACK, payload={"y": 2, "x": 1})
        assert dumps(a) == dumps(b)

    def test_none_fields_are_excluded(self):
        env = DivergenceEnvelope(
            from_service="a", to_service="b", correlation_id="c1", divergence=_divergence()
        )
        msg = ProtocolMessage(type=ProtocolMessageType.DIVERGENCE, payload=env)
        assert "signature" not in json.loads(dumps(msg))["payload"]


# ── loads ──────────────────────────────────────────────────────────────────────


class TestLoads:
    def test_round_trips_a_truth_fragment(self):
        frag = TruthFragment(
            service_id="svc-a", produced_at="2026-01-01T00:00:00Z", nodes=[_node()]
        )
        msg = loads(dumps(ProtocolMessage(type=ProtocolMessageType.TRUTH_FRAGMENT, payload=frag)))
        assert msg.type == ProtocolMessageType.TRUTH_FRAGMENT
        assert isinstance(msg.payload, TruthFragment)
        assert msg.payload.service_id == "svc-a"
        assert msg.payload.nodes[0].properties["path"] == "/pets"

    def test_round_trips_a_divergence_envelope(self):
        env = DivergenceEnvelope(
            from_service="a", to_service="b", correlation_id="c1", divergence=_divergence()
        )
        msg = loads(dumps(ProtocolMessage(type=ProtocolMessageType.DIVERGENCE, payload=env)))
        assert isinstance(msg.payload, DivergenceEnvelope)
        assert msg.payload.divergence.severity == Severity.HIGH

    def test_ack_payload_stays_a_plain_dict(self):
        raw = dumps(ProtocolMessage(type=ProtocolMessageType.ACK, payload={"seq": 3}))
        msg = loads(raw)
        assert msg.payload == {"seq": 3}

    def test_minor_version_difference_is_accepted(self):
        raw = json.dumps({"type": "ack", "protocol_version": "1.9.3", "payload": {}})
        assert loads(raw).protocol_version == "1.9.3"

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("{not json", "Invalid JSON"),
            ("[1, 2, 3]", "Message must be a JSON object"),
            ('{"type": "ack"}', "Missing protocol_version"),
            ('{"protocol_version": "x.y.z", "type": "ack"}', "Invalid"),
            ('{"protocol_version": "2.0.0", "type": "ack"}', "Major version mismatch"),
            ('{"protocol_version": "1.0.0"}', "Missing type"),
            ('{"protocol_version": "1.0.0", "type": "nope"}', "Unknown message type"),
        ],
    )
    def test_rejects_malformed_messages(self, raw, expected):
        with pytest.raises(ValueError, match=expected):
            loads(raw)
