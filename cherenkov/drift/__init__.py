"""cherenkov/drift — Phase 12/13: Drift Reconciliation + L2 Maker/Checker."""

from cherenkov.drift.checker import check_proposal, is_meaningful_assertion
from cherenkov.drift.detect import DriftFinding, DriftKind, detect_findings
from cherenkov.drift.fingerprint import Fingerprint, fingerprint_of, similarity
from cherenkov.drift.ledger import DriftLedger
from cherenkov.drift.loop import (
    AutonomyLevel,
    DriftLoop,
    LoopResult,
)
from cherenkov.drift.maker import build_test_skeleton, make_proposal, patch_suite
from cherenkov.drift.models import ReconciliationProposal
from cherenkov.drift.reconcile import (
    DriftReport,
    DriftVerdict,
    GateSignal,
    aggregate,
    reconcile,
)
from cherenkov.drift.snapshot import SpecSuiteSnapshot, canonicalize_spec

__all__ = [
    "AutonomyLevel",
    "DriftFinding",
    "DriftKind",
    "DriftLedger",
    "DriftLoop",
    "DriftReport",
    "DriftVerdict",
    "Fingerprint",
    "GateSignal",
    "LoopResult",
    "ReconciliationProposal",
    "SpecSuiteSnapshot",
    "aggregate",
    "build_test_skeleton",
    "canonicalize_spec",
    "check_proposal",
    "detect_findings",
    "fingerprint_of",
    "is_meaningful_assertion",
    "make_proposal",
    "patch_suite",
    "reconcile",
    "similarity",
]
