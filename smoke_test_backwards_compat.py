from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

PASS = 0
FAIL = 0

def check(label: str, ok: bool):
    global PASS, FAIL
    if ok:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label}")
        FAIL += 1

print("=== CHERENKOV Backwards Compatibility Smoke Test ===\n")

# 1. Core imports
print("--- Core imports ---")
import cherenkov
check("cherenkov package importable", True)

from cherenkov.core.contracts import (
    Verdict, Status, Scenario, GateResult, StageMeta, StageError,
    IngestOutput, PlanOutput, GenerateOutput, ReviewOutput,
    DivergenceClass, VerdictOutcome, VerdictRecord, Idiom, ReflectorConfig,
)
check("core.contracts types importable", True)

from cherenkov.core.config import Config
check("core.config importable", True)

from cherenkov.core.errors import get_logger, ContractError
check("core.errors importable", True)

from cherenkov.core.feedback_store import FeedbackStore, FeedbackEntry
check("core.feedback_store importable", True)

from cherenkov.core.stats_store import StatsStore
check("core.stats_store importable", True)

# 2. Stage imports
print("\n--- Stage imports ---")
from cherenkov.stages.ingest import IngestStage
check("stages.ingest importable", True)
from cherenkov.stages.plan import PlanStage
check("stages.plan importable", True)
from cherenkov.stages.generate import GenerateStage
check("stages.generate importable", True)
from cherenkov.stages.review import ReviewStage
check("stages.review importable", True)
from cherenkov.stages.review_serve import run_review_server
check("stages.review_serve importable (deprecated)", True)

# 3. Healer imports — all return structured dicts now
print("\n--- Healer imports ---")
from cherenkov.healing.auth_expiry import AuthExpiryHealer
ah = AuthExpiryHealer("test")
result = ah.suggest_heal("test_id", "/test")
check("AuthExpiryHealer returns dict", isinstance(result, dict))
check("AuthExpiryHealer has suggestion key", "suggestion" in result)

from cherenkov.healing.contract_drift import ContractDriftHealer
ch = ContractDriftHealer("test")
result = ch.suggest_heal("test_id", "/test", "GET", ["email"], ["name"])
check("ContractDriftHealer returns dict", isinstance(result, dict))
check("ContractDriftHealer has suggestion key", "suggestion" in result)

from cherenkov.healing.visual_heal import VisualHealer
from cherenkov.core.contracts import VisualReport, VisualGateResult, Verdict, Status, StageMeta
report = VisualReport(
    scenario_id="test",
    gates=[VisualGateResult(gate="pixel_diff", passed=True)],
    verdict=Verdict.AUTO_APPROVE, status=Status.OK,
    metadata=StageMeta(stage="visual", duration_ms=10),
)
vh = VisualHealer("test")
result = vh.suggest_heal(report)
check("VisualHealer returns dict", isinstance(result, dict))
check("VisualHealer has suggestion key", "suggestion" in result)

from cherenkov.healing.diagnose import Diagnoser, FailureClass, DiagnosisResult
check("healing.diagnose importable", True)

# 4. Reflector imports
print("\n--- Reflector imports ---")
from cherenkov.reflector import Reflector, VerdictStore
check("reflector importable", True)
from cherenkov.reflector.cli import build_report, main as reflector_cli
check("reflector.cli importable", True)

# 5. HITL imports
print("\n--- HITL imports ---")
from cherenkov.hitl.store import HitlQueue
check("hitl.store importable", True)
from cherenkov.hitl.contracts import HitlItem, HitlStatus, HitlEnvelope
check("hitl.contracts importable", True)

# 6. Web API imports
print("\n--- Web API imports ---")
from cherenkov.web.api import app, get_queue
check("web.api importable", True)

# 7. AI imports
print("\n--- AI imports ---")
from cherenkov.ai import get_accounting_report, get_cache_stats
check("ai importable", True)

# 8. Divergence / Proof imports
print("\n--- Divergence imports ---")
from cherenkov.divergence.proof_run import run_proof
check("divergence.proof_run importable", True)

# 9. MCP imports
print("\n--- MCP imports ---")
from cherenkov.mcp.server import run_mcp_server
check("mcp.server importable", True)

# 10. Oracle imports
print("\n--- Oracle imports ---")
from cherenkov.oracle.visual_oracle import VisualOracle, VisualChangeKind
check("oracle.visual_oracle importable", True)

# 11. Substrate imports
print("\n--- Substrate imports ---")
from cherenkov.substrate.provider import get_vlm_provider
check("substrate.provider importable", True)
from cherenkov.substrate.router import route
check("substrate.router importable", True)

# 12. StatsStore backwards compat
print("\n--- StatsStore API ---")
ss = StatsStore()
check("StatsStore instantiable", True)
check("StatsStore.record_run exists", hasattr(ss, "record_run"))
check("StatsStore.snapshot exists", hasattr(ss, "snapshot"))
check("StatsStore.get_recent_runs exists", hasattr(ss, "get_recent_runs"))
check("StatsStore.get_run_summary exists", hasattr(ss, "get_run_summary"))

# 13. OrchesrationEngine backwards compat
print("\n--- OrchestrationEngine ---")
from cherenkov.core.orchestrator import OrchestrationEngine
check("OrchestrationEngine importable", True)
check("OrchestrationEngine.run_pipeline exists", hasattr(OrchestrationEngine, "run_pipeline"))

# Summary
print(f"\n{'=' * 40}")
total = PASS + FAIL
print(f"Results: {PASS}/{total} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
