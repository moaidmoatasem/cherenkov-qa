#!/usr/bin/env python3
"""
smoke_test_diagnostics.py — AI Diagnostics Synthesis Stage integration smoke test.
Proves dynamic RAG incident mapping and structured root-cause synthesis.
"""
import os
import sys

from cherenkov.ai.rag_index import RAGIndex
from cherenkov.stages.diagnostics_stage import DiagnosticsStage

def run_diagnostics_smoke_tests():
    print("=======================================================")
    print("    CHERENKOV TRACK C AI DIAGNOSTICS SMOKE TEST")
    print("=======================================================\n")

    # Ensure RAG store has historical incidents so RAG correlation is active
    rag = RAGIndex(run_id="diagnose_smoke")
    rag.add_incident(
        incident_id="inc_001",
        scenario_id="create_user_400",
        failure_class="CONTRACT_DRIFT",
        error_message="Expected property 'id' missing from response"
    )

    # 1. Initialize Diagnostics Stage
    print("\nPass 1: Initializing Diagnostics Synthesis Stage...")
    stage = DiagnosticsStage(run_id="diagnose_smoke")
    
    # 2. Run synthesis pipeline
    print("Pass 2: Executing RAG-augmented LLM synthesis run...")
    output = stage.run(
        scenario_id="create_user_mismatch",
        failure_class="CONTRACT_DRIFT",
        error_message="Response payload is missing the expected 'id' property"
    )

    # 3. Assert outputs
    assert output.scenario_id == "create_user_mismatch", "Failed to preserve scenario ID."
    assert output.failure_class == "CONTRACT_DRIFT", "Failed to preserve failure class."
    assert output.similar_cases_found > 0, "RAG correlation failed to find similar incidents."
    
    print("\n✓ Diagnostics Output Synthesized Successfully:")
    print(f"  - Failure Class:       {output.failure_class}")
    print(f"  - RAG Cases Correlated: {output.similar_cases_found}")
    print(f"  - Formulated Hypothesis: {output.hypothesis}")
    print("  - Actionable Resolution Steps:")
    for step in output.resolution_steps:
        print(f"    * {step}")

    print("\n=======================================================")
    print("     CHERENKOV AI DIAGNOSTICS SMOKE TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    try:
        run_diagnostics_smoke_tests()
        sys.exit(0)
    except Exception as e:
        print(f"\n🛑 Diagnostics Smoke Test Failed: {e}")
        sys.exit(1)
