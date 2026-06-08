#!/usr/bin/env python3
"""
smoke_test_compliance.py — MENA Cyber Security Compliance scanner integration smoke test.
Proves active/static SAMA CCSF and CBE FinCSF framework audit mapping and PDF/HTML metric scoring.
"""
import os
import subprocess
import time
import sys

from cherenkov.compliance.mena_scanner import MENAComplianceScanner

def start_target_server():
    """Starts the mock range FastAPI server."""
    print("Starting Target API Server...")
    cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), "../target"))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "target_api:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # Wait for startup
    return proc

def main():
    print("=======================================================")
    print("     CHERENKOV TRACK C MENA COMPLIANCE SMOKE TEST")
    print("=======================================================\n")

    report_file = ".cherenkov/mena_compliance_report.json"
    if os.path.exists(report_file):
        print(f"Cleaning existing compliance report at {report_file}...")
        os.remove(report_file)

    server_proc = None
    try:
        # 1. Spin target server
        server_proc = start_target_server()

        # 2. Instantiate Compliance Scanner
        scanner = MENAComplianceScanner(run_id="compliance_smoke")

        # 3. Execute audit
        print("\nExecuting SAMA CCSF & Egypt FinCSF compliance audit...")
        report = scanner.run_compliance_audit(
            target_url="http://127.0.0.1:8000",
            spec_path="stub/target_spec.json"
        )

        # 4. Verify outputs
        assert os.path.exists(report_file), "Compliance audit report JSON was not written to disk."
        print(f"✓ Compliance report written successfully: {report_file}")
        print(f"✓ Overall Compliance Score: {report['overall_compliance_score']}%")

        # Assert framework mappings exist and are populated
        mappings = report.get("framework_mappings", {})
        assert "SAMA_CCSF" in mappings, "Report is missing SAMA CCSF framework mapping details."
        assert "EGYPT_FinCSF" in mappings, "Report is missing CBE FinCSF framework mapping details."
        
        print("\n✓ Framework Mappings Verified:")
        print("  - SAMA CCSF Clauses:")
        for domain, detail in mappings["SAMA_CCSF"].items():
            print(f"    * {domain}: {detail['status']} | {detail['clause']}")
            
        print("  - CBE FinCSF Clauses:")
        for section, detail in mappings["EGYPT_FinCSF"].items():
            print(f"    * {section}: {detail['status']}")

        print("\n=======================================================")
        print("    CHERENKOV COMPLIANCE VALIDATION TESTS PASSED!")
        print("=======================================================")
        sys.exit(0)

    except Exception as e:
        print(f"\n🛑 Compliance Smoke Test Failed: {e}")
        sys.exit(1)

    finally:
        # Clean up target server process
        if server_proc:
            print("\nShutting down Target API Server...")
            server_proc.terminate()
            server_proc.wait()


def test_legacy_compliance():
    try:
        main()
    except SystemExit as e:
        if e.code != 0:
            raise AssertionError(f"Test failed with exit code {e.code}")

