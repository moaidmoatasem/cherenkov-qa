#!/usr/bin/env python3
"""
smoke_test_healing_advanced.py — Advanced Healing integration smoke test.
Proves stateful sequence classification and transient flaky retry diagnostics.
"""

import sys

from cherenkov.healing.diagnose import Diagnoser, FailureClass


def run_advanced_healing_smoke_tests():
    print("=======================================================")
    print("    CHERENKOV TRACK B ADVANCED HEALING SMOKE TEST")
    print("=======================================================\n")

    diagnoser = Diagnoser(run_id="heal_advanced_smoke")

    # 1. Verify Stateful Sequence Classification (404 Not Found)
    print("Pass 1: Verifying Stateful Sequence Classification...")
    result_seq = diagnoser.diagnose_failure(
        scenario_id="delete_user_nonexistent",
        current_status=404,
        current_body={"error": "User profile not found"},
        test_name="delete nonexistent user",
    )
    assert (
        result_seq.failure_class == FailureClass.STATE_SEQUENCE
    ), "Failed to classify state sequence issue."
    print(
        "✓ Stateful sequence classification verified (404 mapped to STATE_SEQUENCE).\n"
    )

    # 2. Verify Flaky Retry Classification (FLAKY_SUCCESS)
    print("Pass 2: Verifying Flaky Retry Classification...")
    run_count = 0

    def mock_flaky_test():
        nonlocal run_count
        run_count += 1
        return run_count > 1  # Fails first, passes on second run (retry 1)

    result_flake = diagnoser.verify_flake_status(mock_flaky_test, max_retries=2)
    assert (
        result_flake == FailureClass.FLAKY_SUCCESS
    ), "Failed to diagnose flaky test pass."
    assert run_count == 2, f"Expected 2 test executions, got {run_count}"
    print("✓ Flaky success retry classification verified (passed on retry).\n")

    # 3. Verify Deterministic Failure Retry Classification (DETERMINISTIC_FAILURE)
    print("Pass 3: Verifying Deterministic Failure Classification...")
    fail_count = 0

    def mock_consistent_fail():
        nonlocal fail_count
        fail_count += 1
        return False  # Consistently fails

    result_fail = diagnoser.verify_flake_status(mock_consistent_fail, max_retries=2)
    assert (
        result_fail == FailureClass.DETERMINISTIC_FAILURE
    ), "Failed to diagnose deterministic failure."
    assert fail_count == 2, f"Expected 2 retry test executions, got {fail_count}"
    print(
        "✓ Deterministic failure retry classification verified (consistently failed).\n"
    )

    print("=======================================================")
    print("   CHERENKOV ADVANCED HEALING SMOKE TESTS PASSED!")
    print("=======================================================")


if __name__ == "__main__":
    try:
        run_advanced_healing_smoke_tests()
        sys.exit(0)
    except Exception as e:
        print(f"\n🛑 Advanced Healing Smoke Test Failed: {e}")
        sys.exit(1)
