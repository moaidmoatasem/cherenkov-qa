#!/usr/bin/env python3
"""
smoke_test_perf.py — E2E smoke for Phase B2 Perf Baseline capability layer.

Proves:
  - cherenkov perf invokes cleanly against a live target API
  - SQLite baseline DB is created and gets at least one new row
  - k6-missing path is tolerated (HITL verdict, exit 0)
  - User-owned files under stub/generated_tests/ are NOT auto-modified
    (D7 scoped to non-k6_perf.js files — k6 script is runner scratchpad)

Authority: v3.1 + delta. Track A surface, optional B2 perf layer.
"""

import os
import sqlite3
import time
import subprocess
import requests

REPO = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(REPO, ".cherenkov", "perf_metrics.db")
K6_SCRATCHPAD = os.path.join(REPO, "stub", "generated_tests", "k6_perf.js")


def _start_target():
    print("Starting target API on port 8000...")
    target_dir = os.path.abspath(os.path.join(REPO, "target"))
    proc = subprocess.Popen(
        [
            ".venv/bin/uvicorn",
            "target_api:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=target_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for attempt in range(20):
        try:
            r = requests.get("http://127.0.0.1:8000/health", timeout=1)
            if r.status_code == 200:
                print("Target API healthy (attempt " + str(attempt + 1) + ").")
                return proc
        except Exception:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("Target API failed to start in time.")


def _snapshot_user_tests():
    base = os.path.join(REPO, "stub", "generated_tests")
    snap = {}
    if not os.path.exists(base):
        return snap
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f == "k6_perf.js":
                continue  # runner scratchpad — not a user-owned file
            p = os.path.join(root, f)
            try:
                snap[p] = os.path.getmtime(p)
            except OSError:
                pass
    return snap


def _row_count():
    if not os.path.exists(DB_PATH):
        return 0
    conn = sqlite3.connect(DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM perf_metrics").fetchone()[0]
    conn.close()
    return n


def _run_perf():
    return subprocess.run(
        [
            "./bin/cherenkov",
            "perf",
            "--target",
            "http://127.0.0.1:8000",
            "--endpoint",
            "/health",
            "--method",
            "GET",
            "--vus",
            "2",
            "--duration",
            "2",
        ],
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": "."},
        capture_output=True,
        text=True,
    )


def _cleanup():
    if os.path.exists(K6_SCRATCHPAD):
        os.remove(K6_SCRATCHPAD)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def main():
    print("=======================================================")
    print("     CHERENKOV PHASE B2 PERF BASELINE SMOKE")
    print("=======================================================\n")

    _cleanup()
    proc = _start_target()
    try:
        rows_before = _row_count()
        user_before = _snapshot_user_tests()

        result = _run_perf()
        print(result.stdout[-2000:] if result.stdout else "(no stdout)")
        if result.returncode != 0:
            print("--- stderr ---")
            print(result.stderr[-1500:])
        # HITL (k6 missing or initializing) is acceptable; non-zero exit only on hard FAIL status
        assert result.returncode == 0, (
            "perf must exit 0 (HITL/initializing OK) — got " + str(result.returncode)
        )

        rows_after = _row_count()
        assert rows_after > rows_before, (
            "Expected at least one new row in perf_metrics.db — got "
            + str(rows_before)
            + " -> "
            + str(rows_after)
        )
        print(
            "[OK] SQLite baseline DB rows: "
            + str(rows_before)
            + " -> "
            + str(rows_after)
        )

        user_after = _snapshot_user_tests()
        new = set(user_after) - set(user_before)
        changed = [
            p
            for p in (set(user_before) & set(user_after))
            if user_before[p] != user_after[p]
        ]
        assert not (new or changed), (
            "D7 violation: user files changed new="
            + str(sorted(new))
            + " changed="
            + str(sorted(changed))
        )
        print("[OK] D7: user-owned files in stub/generated_tests/ untouched.")

        assert os.path.exists(
            K6_SCRATCHPAD
        ), "k6_perf.js scratchpad must be written by the stage"
        print("[OK] k6 script scratchpad written at: " + K6_SCRATCHPAD)

    finally:
        print("Stopping target API server...")
        proc.terminate()
        proc.wait()
        print("Target API stopped cleanly.")
        _cleanup()
        print("Cleanup done (suite re-runnable).")

    print("\n=======================================================")
    print("  ALL PERF BASELINE SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    main()
