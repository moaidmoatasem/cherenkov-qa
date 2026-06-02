#!/usr/bin/env python3
"""
Test runner that works from the current directory context.
"""
import sys
import os
import subprocess
import unittest

# Add current directory to Python path
sys.path.insert(0, '.')

def run_unit_tests():
    """Run unit tests using unittest directly."""
    print("Running unit tests...")

    # Import test modules
    try:
        from test_substrate_router import TestSubstrateRouter
        from test_egress_policy import TestEgressPolicy

        # Create test suite
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        # Add all tests from both test classes
        suite.addTests(loader.loadTestsFromTestCase(TestSubstrateRouter))
        suite.addTests(loader.loadTestsFromTestCase(TestEgressPolicy))

        # Run the tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        return result.wasSuccessful()
    except Exception as e:
        print(f"Error running unit tests: {e}")
        return False

def run_smoke_tests():
    """Run smoke tests directly."""
    print("\nRunning smoke tests...")

    smoke_tests = [
        'smoke_test_provider.py',
        'smoke_test_cache.py'
    ]

    all_passed = True
    for smoke_test in smoke_tests:
        try:
            print(f"\n=== Running {smoke_test} ===")
            # Execute the smoke test file directly
            with open(smoke_test, 'r') as f:
                exec(f.read())
            print(f"✅ {smoke_test} passed")
        except Exception as e:
            print(f"❌ {smoke_test} failed: {e}")
            all_passed = False

    return all_passed

def main():
    print("CHERENKOV Epoch 1 Test Runner")
    print("=" * 50)

    # Run unit tests
    unit_success = run_unit_tests()

    # Run smoke tests
    smoke_success = run_smoke_tests()

    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print(f"Unit Tests: {'✅ PASS' if unit_success else '❌ FAIL'}")
    print(f"Smoke Tests: {'✅ PASS' if smoke_success else '❌ FAIL'}")

    if unit_success and smoke_success:
        print("\n🎉 ALL TESTS PASSED! Epoch 1 is ready.")
        return 0
    else:
        print("\n💥 Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())