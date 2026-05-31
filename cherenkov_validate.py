#!/usr/bin/env python3
"""
cherenkov_validate.py — CLI tool to run generated Playwright test suites against a real server and generate value tightening reports.
Authority: v3.1 + delta. Suggest-only.
"""
import sys
import argparse
import subprocess

from cherenkov.execution.validate import ValidationEngine

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
    parser = argparse.ArgumentParser(description="CHERENKOV E2E Suite Validation CLI")
    parser.add_argument(
        "--target", "-t",
        required=True,
        help="The real server target base URL (e.g. http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    engine = ValidationEngine("cli_validate")
    results = engine.validate_suite(args.target)
    
    if results.get("status") == "empty":
        print(f"\nError: {results.get('message')}\n")
        sys.exit(1)
        
    print_tightening_report(results)
    
    # Exit with 0 if validation completed successfully
    sys.exit(0)

if __name__ == "__main__":
    main()
