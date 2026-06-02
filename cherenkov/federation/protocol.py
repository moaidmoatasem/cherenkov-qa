"""E6-1 Truth Protocol"""
from __future__ import annotations
import json
from enum import Enum
from typing import Any, Union
from pydantic import BaseModel, Field
from cherenkov.core.contracts import DivergenceReport
from cherenkov.core.truth_model import GraphEdge, GraphNode

PROTOCOL_VERSION = "1.0.0"

class ProtocolMessageType(str, Enum):
    TRUTH_FRAGMENT = "truth_fragment"
    DIVERGENCE = "divergence"
    ACK = "ack"
    ERROR = "error"

class TruthFragment(BaseModel):
    service_id: str
    protocol_version: str = PROTOCOL_VERSION
    produced_at: str
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    claims: list[dict[str, Any]] = []

class DivergenceEnvelope(BaseModel):
    from_service: str
    to_service: str
    correlation_id: str
    protocol_version: str = PROTOCOL_VERSION
    divergence: DivergenceReport
    signature: str | None = None

class ProtocolMessage(BaseModel):
    type: ProtocolMessageType
    protocol_version: str = PROTOCOL_VERSION
    payload: Union[TruthFragment, DivergenceEnvelope, dict] = {}

def dumps(msg: ProtocolMessage) -> str:
    data = msg.model_dump(mode="json", exclude_none=True)
    return json.dumps(data, sort_keys=True, separators=(",", ":"))

def loads(s: str) -> ProtocolMessage:
    try:
        data = json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object")
    msg_version = data.get("protocol_version")
    if msg_version is None:
        raise ValueError("Missing protocol_version")
    try:
        msg_major = int(msg_version.split(".")[0])
        current_major = int(PROTOCOL_VERSION.split(".")[0])
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid: {msg_version}") from e
    if msg_major != current_major:
        raise ValueError(f"Major version mismatch")
    msg_type = data.get("type")
    if msg_type is None:
        raise ValueError("Missing type")
    try:
        ProtocolMessageType(msg_type)
    except ValueError:
        raise ValueError(f"Unknown message type: {msg_type}") from None
    payload = data.get("payload", {})
    if msg_type == ProtocolMessageType.TRUTH_FRAGMENT.value:
        payload = TruthFragment.model_validate(payload)
    elif msg_type == ProtocolMessageType.DIVERGENCE.value:
        payload = DivergenceEnvelope.model_validate(payload)
    return ProtocolMessage(type=msg_type, protocol_version=msg_version, payload=payload)