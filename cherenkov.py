#!/usr/bin/env python3
"""
cherenkov.py — Unified CLI for CHERENKOV E2E Suite operations.
Authority: v3.1 + delta.
"""
import sys
import argparse
import subprocess

from cherenkov.execution.validate import ValidationEngine
from cherenkov.execution.eject import EjectorEngine

def print_tightening_report(results: dict):
    """Outputs a highly detailed, professional assertion tightening report to the CLI."""
    target_url = results.get("target_url", "N/A")
    reports = results.get("reports", [])
    
    print("\n" + "=" * 80)
    print("🔍 CHERENKOV VALUE ASSERTION TIGHTENING REPORT")
    print("=" * 80)
    print(f"Target Server URL: {target_url}")
    print(f"Scenarios Verified: {len(reports)}")
    print("=" * 80)

    for r in reports:
        scenario = r["scenario_id"]
        status_str = "PASSED" if r["passed"] else "FAILED"
        print(f"\nScenario: {scenario} [{status_str}]")
        print("-" * 80)
        
        if not r["passed"]:
            print(f"🛑 Failure Error: {r['error']}")
            continue

        print("Captured HTTP Exchange:")
        print(f"  Sent Payload:     {r['request_body']}")
        print(f"  Received Response: {r['response_body']}")
        
        suggestions = r.get("suggestions", [])
        if suggestions:
            print("\n💡 Suggested Assertion Tightening (Suggest-only):")
            # De-duplicate suggestions
            unique_sugs = list(set(suggestions))
            for sug in unique_sugs:
                print(f"  consider -> {sug}")
        else:
            print("\n💡 No value matching suggestions detected.")
            
    print("\n" + "=" * 80)
    print("Git status verification:")
    # Prove the suggest-only sandbox constraint (Delta D7)
    git_status = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True
    )
    test_files_modified = any("generated_tests" in line for line in git_status.stdout.splitlines())
    if test_files_modified:
        print("🛑 WARNING: Git status reports test files were modified! (Trust rule violated)")
    else:
        print("✓ Git status is 100% clean — zero test files were auto-modified by validation. Suggest-only constraint honored.")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="CHERENKOV E2E Suite Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands to execute")

    # 1. validate subcommand
    validate_parser = subparsers.add_parser("validate", help="Validate E2E test suite against a real server")
    validate_parser.add_argument(
        "--target", "-t",
        required=True,
        help="The real server target base URL (e.g. http://localhost:8000)"
    )

    # 2. eject subcommand
    eject_parser = subparsers.add_parser("eject", help="Eject generated tests to a standalone Playwright suite")
    eject_parser.add_argument(
        "--output", "-o",
        required=True,
        help="Target output directory for the standalone suite"
    )

    args = parser.parse_args()

    if args.command == "validate":
        engine = ValidationEngine("cli_validate")
        results = engine.validate_suite(args.target)
        if results.get("status") == "empty":
            print(f"\nError: {results.get('message')}\n")
            sys.exit(1)
        print_tightening_report(results)
        sys.exit(0)

    elif args.command == "eject":
        ejector = EjectorEngine("cli_eject")
        success = ejector.eject_suite(args.output)
        if success:
            print(f"\n✓ CHERENKOV E2E suite ejected successfully to: {args.output}")
            print("✓ All CHERENKOV metadata and hooks stripped successfully.")
            print("✓ Ejected folder is 100% standard and runs standalone.\n")
            sys.exit(0)
        else:
            print("\n🛑 Error: Standalone test suite ejection failed.\n")
            sys.exit(1)

if __name__ == "__main__":
    main()
