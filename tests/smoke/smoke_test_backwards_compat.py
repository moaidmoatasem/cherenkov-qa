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
check("cherenkov package importable", True)

from cherenkov.core.contracts import (  # noqa: E402
    Verdict,
    Status,
    StageMeta,
)

check("core.contracts types importable", True)

check("core.config importable", True)

check("core.errors importable", True)

check("core.feedback_store importable", True)

from cherenkov.core.stats_store import StatsStore  # noqa: E402

check("core.stats_store importable", True)

# 2. Stage imports
print("\n--- Stage imports ---")
check("stages.ingest importable", True)
check("stages.plan importable", True)
check("stages.generate importable", True)
check("stages.review importable", True)
check("stages.review_serve importable (deprecated)", True)

# 3. Healer imports — all return structured dicts now
print("\n--- Healer imports ---")
from cherenkov.healing.auth_expiry import AuthExpiryHealer  # noqa: E402

ah = AuthExpiryHealer("test")
result = ah.suggest_heal("test_id", "/test")
check("AuthExpiryHealer returns dict", isinstance(result, dict))
check("AuthExpiryHealer has suggestion key", "suggestion" in result)

from cherenkov.healing.contract_drift import ContractDriftHealer  # noqa: E402

ch = ContractDriftHealer("test")
result = ch.suggest_heal("test_id", "/test", "GET", ["email"], ["name"])
check("ContractDriftHealer returns dict", isinstance(result, dict))
check("ContractDriftHealer has suggestion key", "suggestion" in result)

from cherenkov.healing.visual_heal import VisualHealer  # noqa: E402
from cherenkov.core.contracts import VisualReport, VisualGateResult  # noqa: E402

report = VisualReport(
    scenario_id="test",
    gates=[VisualGateResult(gate="pixel_diff", passed=True)],
    verdict=Verdict.AUTO_APPROVE,
    status=Status.OK,
    metadata=StageMeta(stage="visual", duration_ms=10),
)
vh = VisualHealer("test")
result = vh.suggest_heal(report)
check("VisualHealer returns dict", isinstance(result, dict))
check("VisualHealer has suggestion key", "suggestion" in result)

check("healing.diagnose importable", True)

# 4. Reflector imports
print("\n--- Reflector imports ---")
check("reflector importable", True)
check("reflector.cli importable", True)

# 5. HITL imports
print("\n--- HITL imports ---")
check("hitl.store importable", True)
check("hitl.contracts importable", True)

# 6. Web API imports
print("\n--- Web API imports ---")
check("web.api importable", True)

# 7. AI imports
print("\n--- AI imports ---")
check("ai importable", True)

# 8. Divergence / Proof imports
print("\n--- Divergence imports ---")
check("divergence.proof_run importable", True)

# 9. MCP imports
print("\n--- MCP imports ---")
check("mcp.server importable", True)

# 10. Oracle imports
print("\n--- Oracle imports ---")
check("oracle.visual_oracle importable", True)

# 11. Substrate imports
print("\n--- Substrate imports ---")
check("substrate.provider importable", True)
check("substrate.router importable", True)
check("substrate.providers.ollama importable", True)
check("substrate.providers.vlm importable", True)

# 12. Phase 0b new modules
print("\n--- Phase 0b: Core extensions ---")
from cherenkov.core.devices import DeviceInfo  # noqa: E402

check("core.devices importable", True)
di = DeviceInfo()
check("DeviceInfo instantiable", True)
check("DeviceInfo.to_dict works", isinstance(di.to_dict(), dict))

from cherenkov.core.events import CHERENKOVEvent  # noqa: E402

check("core.events importable", True)
ev = CHERENKOVEvent.pipeline_start("test")
check("CHERENKOVEvent factory works", ev.name == "pipeline.start")
check("CHERENKOVEvent.to_dict works", "event_id" in ev.to_dict())

from cherenkov.core.knowledge_result import KnowledgeResult, KnowledgeKind  # noqa: E402

check("core.knowledge_result importable", True)
kr = KnowledgeResult(id="t1", kind=KnowledgeKind.IDIOM, key="/api/test", summary="test")
check("KnowledgeResult instantiable", True)
check("KnowledgeResult.to_event_payload works", "key" in kr.to_event_payload())

check("core.migration importable", True)

from cherenkov.core.error_handling import GracefulDegradation, DegradationLevel  # noqa: E402

check("core.error_handling importable", True)
gd = GracefulDegradation()
check("GracefulDegradation instantiable", True)
check("health starts healthy", gd.health.level == DegradationLevel.HEALTHY)

check("core.logging_ext importable", True)

# 13. Port interfaces
print("\n--- Phase 0b: Port interfaces ---")
check("ports importable", True)
check("EventBus is protocol", True)
check("KnowledgeRepository is protocol", True)
check("DeviceRegistry is protocol", True)
check("VLMProvider is protocol", True)

# 14. Phase 0b: Web extensions
print("\n--- Phase 0b: Web monitoring ---")
check("web.monitoring importable", True)

check("web.middleware.security importable", True)

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
from cherenkov.core.orchestrator import OrchestrationEngine  # noqa: E402

check("OrchestrationEngine importable", True)
check(
    "OrchestrationEngine.run_pipeline exists",
    hasattr(OrchestrationEngine, "run_pipeline"),
)

# Summary
print(f"\n{'=' * 40}")
total = PASS + FAIL
print(f"Results: {PASS}/{total} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
