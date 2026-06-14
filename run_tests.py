#!/usr/bin/env python3
"""
Test runner that works from the current directory context.

Runs the Epoch 1 unit tests plus the standalone smoke tests. Smoke tests are
executed as isolated subprocesses (not via ``exec``) so that classes/functions
defined at their module level resolve correctly, and so a crash in one does not
abort the others.
"""

import sys
import subprocess
import unittest

# Add current directory to Python path
sys.path.insert(0, ".")

PASS = "[PASS]"
FAIL = "[FAIL]"


def run_unit_tests():
    """Run unit tests using unittest directly."""
    print("Running unit tests...")

    try:
        from test_substrate_router import TestSubstrateRouter
        from test_egress_policy import TestEgressPolicy

        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        suite.addTests(loader.loadTestsFromTestCase(TestSubstrateRouter))
        suite.addTests(loader.loadTestsFromTestCase(TestEgressPolicy))

        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()
    except Exception as e:
        print(f"Error running unit tests: {e}")
        return False


def run_smoke_tests():
    """Run smoke tests as isolated subprocesses."""
    print("\nRunning smoke tests...")

    smoke_tests = [
        "smoke_test_provider.py",
        "smoke_test_cache.py",
    ]

    all_passed = True
    for smoke_test in smoke_tests:
        print(f"\n=== Running {smoke_test} ===")
        proc = subprocess.run(
            [sys.executable, smoke_test],
            capture_output=True,
            text=True,
        )
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.returncode == 0:
            print(f"{PASS} {smoke_test} passed")
        else:
            if proc.stderr:
                print(proc.stderr, end="")
            print(f"{FAIL} {smoke_test} failed (exit {proc.returncode})")
            all_passed = False

    return all_passed


def main():
    print("CHERENKOV Epoch 1 Test Runner")
    print("=" * 50)

    unit_success = run_unit_tests()
    smoke_success = run_smoke_tests()

    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print(f"Unit Tests:  {PASS if unit_success else FAIL}")
    print(f"Smoke Tests: {PASS if smoke_success else FAIL}")

    if unit_success and smoke_success:
        print("\nALL TESTS PASSED! Epoch 1 is ready.")
        return 0
    else:
        print("\nSome tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
