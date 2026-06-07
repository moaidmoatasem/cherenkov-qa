#!/usr/bin/env python3
"""
smoke_test_perf.py — E2E performance validation and load exporter test for CHERENKOV.
Proves generation of standard local k6 script files and graceful execution report.
"""
import os
import subprocess
import time
import sys

from cherenkov.execution.k6_runner import K6Runner

def start_target_server():
    """Starts the mock range FastAPI server."""
    print("Starting Target API Server...")
    cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../target"))
    proc = subprocess.Popen(
        [".venv/bin/uvicorn", "target_api:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # Wait for startup
    return proc

def main():
    print("=======================================================")
    print("      CHERENKOV TRACK B PERFORMANCE LOAD SMOKE TEST")
    print("=======================================================\n")

    # Clean existing k6 script if any
    k6_file = "stub/generated_tests/k6_perf.js"
    if os.path.exists(k6_file):
        print(f"Cleaning existing k6 script at {k6_file}...")
        os.remove(k6_file)

    server_proc = None
    try:
        # 1. Spin target server
        server_proc = start_target_server()

        # 2. Instantiate K6 Runner
        runner = K6Runner(run_id="perf_smoke")

        # 3. Export script and run validation
        print("\nRunning k6 load test validation...")
        res = runner.run_k6_validation("http://127.0.0.1:8000")

        # 4. Verify results
        assert res["status"] in ("success", "exported", "degraded"), f"Load exporter run failed: {res.get('message', '')}"
        
        # Verify script written to disk successfully
        assert os.path.exists(k6_file), "k6 script file was not written to disk."
        print(f"✓ k6 Performance script generated successfully: {k6_file}")

        # Check file contents to ensure correct payload mapping
        with open(k6_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "http.post" in content, "Generated script is missing HTTP POST execution call."
        assert "thresholds" in content, "Generated script is missing performance thresholds."
        print("✓ Performance script parameters verified.")

        print(f"\nResult: {res['message']}")
        if "instructions" in res:
            print(f"Instructions: {res['instructions']}")

        print("\n=======================================================")
        print("    CHERENKOV PERFORMANCE VALIDATION TESTS PASSED!")
        print("=======================================================")
        sys.exit(0)

    except Exception as e:
        print(f"\n🛑 Performance Smoke Test Failed: {e}")
        sys.exit(1)

    finally:
        # Clean up target server process
        if server_proc:
            print("\nShutting down Target API Server...")
            server_proc.terminate()
            server_proc.wait()

if __name__ == "__main__":
    main()
