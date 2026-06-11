"""Tests for E6-1 Truth Protocol (wire format)."""
import json
import pytest
from cherenkov.core.contracts import DivergenceReport, DivergenceClass, Severity, DivergenceEvidence, Status, StageError, StageMeta
from cherenkov.core.truth_model import TruthModel, GraphNode, GraphEdge, NodeType, EdgeType, Claim, Provenance
from cherenkov.federation.protocol import (
    TruthFragment,
    DivergenceEnvelope,
    ProtocolMessage,
    ProtocolMessageType,
    PROTOCOL_VERSION,
    dumps,
    loads,
)

def make_divergence_report():
    """Helper to create a DivergenceReport for testing."""
    return DivergenceReport(
        id="div-1",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="endpoint returns 200",
        claim_b="endpoint returns 400",
        evidence=DivergenceEvidence(
            request_summary="GET /api/test -> 400",
            response_actual={"error": "bad"},
            response_expected={"data": "ok"},
            diff="status mismatch",
        ),
        repro_steps=["step1"],
        severity=Severity.HIGH,
        metadata=StageMeta(stage="witness", schema_version=1),
    )

def test_round_trip_truth_fragment():
    """Test TruthFragment serialization/deserialization."""
    model = TruthModel()
    node = GraphNode(
        id="ep-1",
        type=NodeType.ENDPOINT,
        label="GET /users",
        properties={"method": "GET", "path": "/users"},
    )
    model.add_node(node)
    
    frag = TruthFragment(
        service_id="acme-api",
        produced_at="2026-06-03T01:00:00Z",
        nodes=[node],
    )
    
    # Serialize to JSON
    msg = ProtocolMessage(
        type=ProtocolMessageType.TRUTH_FRAGMENT,
        payload=frag,
    )
    serialized = dumps(msg)
    assert isinstance(serialized, str)
    assert "acme-api" in serialized
    
    # Deserialize
    restored = loads(serialized)
    assert restored.type == ProtocolMessageType.TRUTH_FRAGMENT
    assert restored.payload.service_id == "acme-api"
    assert restored.payload.produced_at == "2026-06-03T01:00:00Z"

def test_round_trip_divergence_envelope():
    """Test DivergenceEnvelope serialization/deserialization."""
    div_report = make_divergence_report()
    envelope = DivergenceEnvelope(
        from_service="detector-1",
        to_service="acme-api",
        correlation_id="corr-123",
        divergence=div_report,
    )
    
    msg = ProtocolMessage(
        type=ProtocolMessageType.DIVERGENCE,
        payload=envelope,
    )
    serialized = dumps(msg)
    assert "detector-1" in serialized
    assert "corr-123" in serialized
    
    restored = loads(serialized)
    assert restored.type == ProtocolMessageType.DIVERGENCE
    assert restored.payload.from_service == "detector-1"
    assert restored.payload.divergence.id == "div-1"

def test_unknown_message_type():
    """Test rejection of unknown message type."""
    bad_json = json.dumps({
        "type": "unknown_message",
        "protocol_version": "1.0.0",
        "payload": {}
    })
    with pytest.raises(ValueError, match="Unknown"):
        loads(bad_json)

def test_missing_protocol_version():
    """Test rejection when protocol_version is missing."""
    bad_json = json.dumps({
        "type": "truth_fragment",
        "payload": {}
    })
    with pytest.raises(ValueError, match="Missing protocol_version"):
        loads(bad_json)

def test_major_version_mismatch():
    """Test rejection of incompatible major version."""
    bad_json = json.dumps({
        "type": "truth_fragment",
        "protocol_version": "2.0.0",
        "payload": {}
    })
    with pytest.raises(ValueError, match="Major version"):
        loads(bad_json)

def test_canonical_form():
    """Test that canonical JSON form is deterministic."""
    frag = TruthFragment(
        service_id="test",
        produced_at="2026-06-03T00:00:00Z",
    )
    msg = ProtocolMessage(
        type=ProtocolMessageType.TRUTH_FRAGMENT,
        payload=frag,
    )
    
    # Two instances should produce identical JSON
    json1 = dumps(msg)
    json2 = dumps(msg)
    assert json1 == json2
    
    # Verify sorted keys
    data = json.loads(json1)
    assert list(data.keys()) == sorted(data.keys())

def test_ack_message():
    """Test ACK message (dict payload)."""
    msg = ProtocolMessage(
        type=ProtocolMessageType.ACK,
        payload={"status": "received", "trace_id": "t-1"}
    )
    serialized = dumps(msg)
    restored = loads(serialized)
    assert restored.type == ProtocolMessageType.ACK
    assert restored.payload["status"] == "received"

def test_error_message():
    """Test ERROR message (dict payload)."""
    msg = ProtocolMessage(
        type=ProtocolMessageType.ERROR,
        payload={"code": "validation_error", "message": "Invalid fragment"}
    )
    serialized = dumps(msg)
    restored = loads(serialized)
    assert restored.type == ProtocolMessageType.ERROR
    assert "validation_error" in str(restored.payload)