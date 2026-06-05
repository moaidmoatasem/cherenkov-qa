#!/usr/bin/env python3
"""
smoke_test_validate.py — automated integration test E2E verifying Phase 8 validation CLI reports.
"""
import os
import time
import subprocess
import requests

def main():
    print("=======================================================")
    print("     CHERENKOV WEEK 1 PHASE 8 VALIDATE SMOKE TESTS")
    print("=======================================================\n")

    # 1. Start the target API in standard mode on port 8000
    print("Starting target API on port 8000...")
    target_dir = os.path.abspath("target")
    proc = subprocess.Popen(
        [".venv/bin/uvicorn", "target_api:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=target_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # 2. Block until target API is healthy
    healthy = False
    for attempt in range(15):
        try:
            resp = requests.get("http://localhost:8000/health", timeout=1)
            if resp.status_code == 200:
                healthy = True
                print(f"Target API is healthy and online (attempt {attempt+1}).")
                break
        except Exception:
            time.sleep(0.5)

    if not healthy:
        print("Error: Target API failed to start in time.")
        proc.terminate()
        return

    # 3. Execute cherenkov_validate.py against target API
    print("Executing validation subcommand CLI against target API...")
    try:
        val_proc = subprocess.run(
            ["python3", "cherenkov.py", "validate", "--target", "http://localhost:8000"],
            env={**os.environ, "PYTHONPATH": "."},
            capture_output=True,
            text=True,
            check=True
        )
        stdout = val_proc.stdout
        stderr = val_proc.stderr
        
        print("\n--- CLI TIGHTENING REPORT OUTPUT ---")
        print(stdout)
        print("------------------------------------\n")

        # 4. Assert report details
        assert "consider -> expect(data.email).toBe('test@example.com')" in stdout, "Missing suggested string value assertion!"
        assert "consider -> expect(data.email).toBe(body.email)" in stdout, "Missing suggested payload match assertion!"
        print("✓ Successfully verified value tightening suggestions for /users POST happy_path endpoint.")

        assert "password_too_short [FAILED]" in stdout, "Failed to capture password_too_short spec conformance drift!"
        print("✓ Successfully verified spec-to-implementation conformance failure (RED) report.")

        assert "zero test files were auto-modified by validation" in stdout, "Suggest-only trust constraint check missing!"
        print("✓ Successfully verified suggest-only sandbox constraint assertion (no files modified).")

    except subprocess.CalledProcessError as e:
        print(f"Validation CLI execution failed: {e}")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        raise e
    finally:
        # 5. Clean up Target API background task
        print("Stopping target API server...")
        proc.terminate()
        proc.wait()
        print("Target API stopped cleanly.")

    print("\n=======================================================")
    print("  ALL VALIDATE SUBCOMMAND SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    main()
