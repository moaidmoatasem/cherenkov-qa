#!/usr/bin/env python3
"""Dashboard E2E smoke test — 11 API endpoint assertions."""
import os, sys, time, subprocess, requests, shutil

def main():
    print("Starting dashboard server on port 8080...")
    self_dir = os.path.dirname(os.path.abspath(__file__))
    wrapper = os.path.join(os.path.dirname(os.path.dirname(self_dir)), "scripts", "start_dashboard_api.py")
    out_f = open("dashboard_startup.log", "w", encoding="utf-8")
    err_f = open("dashboard_startup.err", "w", encoding="utf-8")
    dashboard_proc = subprocess.Popen(["python3", wrapper, "--port", "8080"], stdout=out_f, stderr=err_f)

    healthy = False
    base_url = "http://127.0.0.1:8080"
    for attempt in range(30):
        try:
            resp = requests.get(f"{base_url}/api/v1/health", timeout=15)
            if resp.status_code == 200:
                healthy = True
                print(f"up (attempt {attempt+1})")
                break
        except Exception:
            time.sleep(1.0)
    out_f.close()
    err_f.close()

    if not healthy:
        print("FAIL: server not healthy")
        if os.path.exists("dashboard_startup.log"):
            with open("dashboard_startup.log") as f: print(f.read())
        if os.path.exists("dashboard_startup.err"):
            with open("dashboard_startup.err") as f: print(f.read())
        dashboard_proc.terminate(); return 1

    results = []
    def check(name, ok):
        tag = "[PASS]" if ok else "[FAIL]"
        print(f"{tag} {name}")
        results.append(ok)

    try:
        r = requests.get(f"{base_url}/api/v1/health", timeout=15)
        d = r.json()
        check("GET /health (200)", r.status_code == 200 and d.get("status") == "online" and "device" in d and "gen_model" in d)

        r = requests.get(f"{base_url}/api/v1/tests", timeout=15)
        tests = r.json()
        check("GET /tests (200 list)", r.status_code == 200 and isinstance(tests, list))

        r = requests.post(f"{base_url}/api/v1/review/approve", json={"scenario_id":"happy_path","reason":"ok"}, timeout=15)
        check("POST /review/approve (200)", r.status_code == 200 and r.json().get("status") == "approved")

        r = requests.post(f"{base_url}/api/v1/ingest", timeout=15)
        check("POST /ingest (400 no input)", r.status_code == 400)

        r = requests.post(f"{base_url}/api/v1/review/reject", json={"scenario_id":"dummy","reason":"test"}, timeout=15)
        check("POST /review/reject (200)", r.status_code == 200 and r.json().get("status") == "rejected")

        r = requests.post(f"{base_url}/api/v1/review/edit", json={"scenario_id":"dummy"}, timeout=15)
        check("POST /review/edit (400 no code)", r.status_code == 400)

        r = requests.post(f"{base_url}/api/v1/review/edit", json={"scenario_id":"edit_test","test_code":"test('x', () => {});"}, timeout=15)
        check("POST /review/edit (200 saved)", r.status_code == 200 and r.json().get("status") == "saved")

        r = requests.post(f"{base_url}/api/v1/run", json={"spec_path":"/nonexistent/spec.json"}, timeout=15)
        check("POST /run (404 missing)", r.status_code == 404)

        r = requests.post(f"{base_url}/api/v1/eject", json={"output_path": os.path.abspath("temp_eject_out")}, timeout=15)
        check("POST /eject (200)", r.status_code == 200 and r.json().get("status") == "ejected")
        if os.path.exists("temp_eject_out"):
            shutil.rmtree("temp_eject_out")

    except Exception as e:
        print(f"FAIL: {e}")
        dashboard_proc.terminate(); dashboard_proc.wait(); return 1
    finally:
        dashboard_proc.terminate(); dashboard_proc.wait()

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} assertions passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
