#!/usr/bin/env python3
"""
smoke_test.py — E2E contract, retry, and skeleton integration tests for CHERENKOV.
Proves happy path execution and deliberate contract boundary failure safety.
"""
from cherenkov.core.orchestrator import OrchestrationEngine


def run_happy_path():
    print("=== PASS 1: E2E Happy Path (Stubbed Stages) ===")
    engine = OrchestrationEngine(run_id="happy")
    success = engine.run_pipeline("stripe_spec.json")
    assert success, "Happy path execution failed."
    print("✓ E2E Happy Path verification: PASS\n")


def run_failure_path():
    print("=== PASS 2: E2E Contract Boundary Failure & Retry Ladder ===")
    print("Simulating a malformed stage output inside INGEST...")
    
    # We set error_threshold = 1 so the circuit breaker trips immediately on retry ladder exhaust
    engine = OrchestrationEngine(run_id="failure", error_threshold=1)
    
    # Running pipeline simulating a malformed INGEST stage
    success = engine.run_pipeline("stripe_spec.json", simulate_fail_stage="INGEST")
    
    # The pipeline must abort gracefully (trip the circuit breaker) and return False,
    # rather than crashing with a raw python stack trace!
    assert not success, "Pipeline did not abort as expected under tripped circuit breaker."
    assert engine.breaker.tripped, "Circuit breaker failed to trip after failure limit was reached."
    assert engine.breaker.error_count == 1, f"Expected 1 failure on circuit breaker, got {engine.breaker.error_count}"
    print("✓ E2E Failure Path & Retry Ladder verification: PASS\n")


def main():
    print("=======================================================")
    print("     CHERENKOV WEEK 1 SKELETON E2E SMOKE TESTS")
    print("=======================================================\n")
    
    run_happy_path()
    run_failure_path()
    
    print("=======================================================")
    print("  ALL SKELETON E2E VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    main()
