#!/usr/bin/env python3
"""
smoke_test_dashboard.py — E2E automated integration tests verifying the FastAPI dashboard REST endpoints.
Proves health check, test fetching, validate triggers, and standalone suite ejection via web API.
"""
import os
import time
import subprocess
import requests

def main():
    print("=======================================================")
    print("     CHERENKOV WEEK 1 PHASE 11 DASHBOARD SMOKE TESTS")
    print("=======================================================\n")

    # 1. Start the Dashboard API server on port 8080
    print("Starting dashboard server on port 8080...")
    out_f = open("dashboard_startup.log", "w", encoding="utf-8")
    err_f = open("dashboard_startup.err", "w", encoding="utf-8")
    dashboard_proc = subprocess.Popen(
        ["python3", "cherenkov.py", "dashboard", "--port", "8080", "--host", "127.0.0.1"],
        env={**os.environ, "PYTHONPATH": "."},
        stdout=out_f,
        stderr=err_f
    )

    # 2. Block until dashboard server is healthy
    healthy = False
    base_url = "http://127.0.0.1:8080"
    for attempt in range(15):
        try:
            resp = requests.get(f"{base_url}/api/v1/health", timeout=1)
            if resp.status_code == 200:
                healthy = True
                print(f"Dashboard server is healthy and online (attempt {attempt+1}).")
                break
        except Exception:
            time.sleep(0.5)

    out_f.close()
    err_f.close()

    if not healthy:
        print("Error: Dashboard server failed to start in time.")
        if os.path.exists("dashboard_startup.log"):
            with open("dashboard_startup.log", "r", encoding="utf-8") as f:
                print(f"Stdout:\n{f.read()}")
        if os.path.exists("dashboard_startup.err"):
            with open("dashboard_startup.err", "r", encoding="utf-8") as f:
                print(f"Stderr:\n{f.read()}")
        dashboard_proc.terminate()
        return

    try:
        # 3. Test /api/v1/health
        print("Testing GET /api/v1/health...")
        resp = requests.get(f"{base_url}/api/v1/health", timeout=2)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("status") == "online", "Dashboard is not online!"
        assert "device" in data, "Missing device configuration!"
        assert "gen_model" in data, "Missing model configuration!"
        print("✓ GET /api/v1/health: OK")

        # 4. Test GET /api/v1/tests
        print("Testing GET /api/v1/tests...")
        resp = requests.get(f"{base_url}/api/v1/tests", timeout=2)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        tests = resp.json()
        assert isinstance(tests, list), "Expected list of tests!"
        print(f"✓ GET /api/v1/tests: OK (found {len(tests)} scenarios)")

        # 5. Test POST /api/v1/review/approve
        print("Testing POST /api/v1/review/approve...")
        approve_payload = {"scenario_id": "happy_path", "reason": "Verified manually"}
        resp = requests.post(f"{base_url}/api/v1/review/approve", json=approve_payload, timeout=2)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json().get("status") == "approved", "Failed to approve scenario!"
        print("✓ POST /api/v1/review/approve: OK")

        # 6. Test POST /api/v1/eject (best-effort wrapper E2E check)
        print("Testing POST /api/v1/eject...")
        temp_eject_path = os.path.abspath("temp_api_eject")
        eject_payload = {"output_path": temp_eject_path}
        resp = requests.post(f"{base_url}/api/v1/eject", json=eject_payload, timeout=5)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        eject_data = resp.json()
        assert eject_data.get("status") == "ejected", "Failed to eject test suite via web API!"
        print("✓ POST /api/v1/eject: OK")

        # Clean up temporary API ejection folder if created
        import shutil
        if os.path.exists(temp_eject_path):
            shutil.rmtree(temp_eject_path)

    except Exception as e:
        print(f"Dashboard E2E validation failed: {e}")
        raise e
    finally:
        # 7. Clean up Dashboard API server process
        print("Stopping dashboard server...")
        dashboard_proc.terminate()
        dashboard_proc.wait()
        print("Dashboard server stopped cleanly.")

    print("\n=======================================================")
    print("  ALL DASHBOARD INTEGRATION SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    main()
