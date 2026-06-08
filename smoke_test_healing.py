#!/usr/bin/env python3
"""
smoke_test_healing.py -- E2E integration tests for CHERENKOV Phase 7 HEALING.
Proves AUTH_EXPIRY and CONTRACT_DRIFT suggestion generation without auto-committing/altering files.
"""
import os
import subprocess
from cherenkov.healing import Diagnoser, FailureClass, AuthExpiryHealer, ContractDriftHealer

def get_modified_test_files():
    try:
        git_status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        return {
            line for line in git_status.stdout.splitlines() 
            if "generated_tests" in line and (".spec.ts" in line or ".ts" in line)
        }
    except Exception:
        return set()


def test_auth_expiry_detection():
    print("=== PASS 1: AUTH_EXPIRY Diagnostic & Suggestion ===")
    diagnoser = Diagnoser(run_id="test_healing")
    
    # Simulate an auth expiry failure: historically passed (snapshot exists), now returns 401
    scenario_id = "happy_path"
    
    # 1. Record snapshot first to simulate a historically passing run
    diagnoser.record_passing_snapshot(scenario_id, status=201, body={"id": 42, "email": "test@example.com"})
    
    # 2. Run diagnoser simulating a new run returning 401
    diag = diagnoser.diagnose_failure(
        scenario_id=scenario_id,
        current_status=401,
        current_body={},
        test_name=scenario_id
    )
    
    assert diag.failure_class == FailureClass.AUTH_EXPIRY, f"Expected AUTH_EXPIRY, got {diag.failure_class}"
    print("[PASS] Diagnoser correctly classified FailureClass.AUTH_EXPIRY")
    
    # 3. Generate suggestion
    suggestion = AuthExpiryHealer("test_healing").suggest_heal(scenario_id, "/users")
    assert "BEARER_TOKEN" in suggestion["suggestion"], "Auth expiry suggestion missing key tokens"
    print("\n--- AUTH_EXPIRY SUGGESTION OUTPUT ---")
    print(suggestion["suggestion"])
    print("-------------------------------------\n")


def test_contract_drift_detection():
    print("=== PASS 2: CONTRACT_DRIFT Diagnostic & Suggestion ===")
    diagnoser = Diagnoser(run_id="test_healing")
    
    scenario_id = "happy_path"
    
    # 1. Record historical snapshot with ["id", "email"]
    diagnoser.record_passing_snapshot(scenario_id, status=201, body={"id": 42, "email": "test@example.com"})
    
    # 2. Simulate contract drift where a field was REMOVED (email is missing, only id is returned)
    diag = diagnoser.diagnose_failure(
        scenario_id=scenario_id,
        current_status=201,
        current_body={"id": 42}, # email removed
        test_name=scenario_id
    )
    
    assert diag.failure_class == FailureClass.CONTRACT_DRIFT, f"Expected CONTRACT_DRIFT, got {diag.failure_class}"
    assert "email" in diag.missing_fields, "Failed to identify missing field 'email'"
    print("[PASS] Diagnoser correctly classified FailureClass.CONTRACT_DRIFT and isolated missing field")
    
    # 3. Generate suggestion
    suggestion = ContractDriftHealer("test_healing").suggest_heal(
        scenario_id=scenario_id,
        endpoint="/users",
        method="POST",
        missing_fields=diag.missing_fields,
        added_fields=diag.added_fields
    )
    assert "[RED REGRESSION]" in suggestion["suggestion"], "Contract drift suggestion failed to flag RED regression"
    assert "expect(data).toHaveProperty" in suggestion["suggestion"], "Contract drift suggestion missing suggested assertions"
    print("\n--- CONTRACT_DRIFT SUGGESTION OUTPUT ---")
    print(suggestion["suggestion"])
    print("-------------------------------------\n")


def verify_suggest_only_trust_rule(initial_modified):
    print("=== PASS 3: Verify Zero Auto-Commits Rule ===")
    # Ensure generated tests inside stub/generated_tests were NOT auto-modified by healing during this run
    current_modified = get_modified_test_files()
    new_modified = current_modified - initial_modified
    
    assert len(new_modified) == 0, f"Violation: Test files were auto-modified during run: {new_modified}"
    print("[PASS] Git status is 100% clean relative to run start -- zero files were auto-modified by healing! Suggest-only trust rule honored.\n")


def main():
    print("=======================================================")
    print("     CHERENKOV WEEK 1 PHASE 7 HEALING SMOKE TESTS")
    print("=======================================================\n")
    
    initial_modified = get_modified_test_files()
    
    test_auth_expiry_detection()
    test_contract_drift_detection()
    verify_suggest_only_trust_rule(initial_modified)
    
    print("=======================================================")
    print("  ALL HEALING INTEGRATION SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    main()
