"""cherenkov/drift — Phase 12/13: Drift Reconciliation + L2 Maker/Checker."""

from cherenkov.drift.snapshot import SpecSuiteSnapshot, canonicalize_spec
from cherenkov.drift.fingerprint import Fingerprint, fingerprint_of, similarity
from cherenkov.drift.detect import DriftKind, DriftFinding, detect_findings
from cherenkov.drift.reconcile import (
    GateSignal,
    DriftVerdict,
    aggregate,
    DriftReport,
    reconcile,
)
from cherenkov.drift.ledger import DriftLedger
from cherenkov.drift.loop import (
    AutonomyLevel,
    DriftLoop,
    LoopResult,
    ReconciliationProposal,
)
from cherenkov.drift.maker import make_proposal, build_test_skeleton, patch_suite
from cherenkov.drift.checker import check_proposal, is_meaningful_assertion

__all__ = [
    "SpecSuiteSnapshot",
    "canonicalize_spec",
    "Fingerprint",
    "fingerprint_of",
    "similarity",
    "DriftKind",
    "DriftFinding",
    "detect_findings",
    "GateSignal",
    "DriftVerdict",
    "aggregate",
    "DriftReport",
    "reconcile",
    "DriftLedger",
    "AutonomyLevel",
    "DriftLoop",
    "LoopResult",
    "ReconciliationProposal",
    "make_proposal",
    "build_test_skeleton",
    "patch_suite",
    "check_proposal",
    "is_meaningful_assertion",
]
