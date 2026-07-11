"""
CHERENKOV hitl — the human-review queue (Track-A scope; operationalizes
Verdict.HITL from REVIEW). The persistence + frozen `hitl/v1` envelope that
voice layers (OpenClaw, dashboard) consume. SQLite is the SSOT and the
concurrency gatekeeper.
"""

from cherenkov.hitl.contracts import (
    SCHEMA_VERSION,
    HitlEnvelope,
    HitlError,
    HitlItem,
    HitlStatus,
)
from cherenkov.hitl.store import HitlQueue

__all__ = [
    "SCHEMA_VERSION",
    "HitlEnvelope",
    "HitlError",
    "HitlItem",
    "HitlQueue",
    "HitlStatus",
]
