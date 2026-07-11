"""cherenkov/drift/models.py — Shared dataclasses for the drift package.

Extracted from loop.py to break the circular import between loop.py and
maker.py/checker.py (both import ReconciliationProposal, loop.py imports them).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cherenkov.drift.detect import DriftFinding, DriftKind


@dataclass
class ReconciliationProposal:
    """A maker-generated proposal for a single drifted operation."""

    operation_id: str
    drift_kind: DriftKind
    action: str               # human-readable description of proposed change
    patch: dict[str, Any] = field(default_factory=dict)  # structured diff (Phase 13)
    verified: bool = False     # set True after checker pass
