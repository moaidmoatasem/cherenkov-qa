#!/usr/bin/env python3
"""
smoke_test_visual.py — E2E smoke for Phase B1 Visual Regression capability layer.

Proves:
  Pass 1: 'cherenkov visual' initializes a baseline cleanly (auto-init, no failure).
  Pass 2: 'cherenkov visual' passes comparison against the just-written baseline.
  D7:     User-owned files under stub/generated_tests/ are NOT auto-modified.
          The visual stage's own scratchpad spec (prefix 'visual_') is the
          runner's domain — same pattern Track A uses for any test run.

Authority: v3.1 + delta. Track A surface, optional B1 visual layer.
"""

import os
import time
import shutil
import subprocess
import requests

REPO = os.path.dirname(os.path.abspath(__file__))
VISUAL_SCRATCHPAD_PREFIX = "visual_"
BASELINE_DIRS = [
    os.path.join(REPO, "stub", "visual_baselines"),
    os.path.join(
        REPO, "stub", "generated_tests", "visual_cli_default.spec.ts-snapshots"
    ),
]
SCRATCHPAD_SPEC = os.path.join(
    REPO, "stub", "generated_tests", "visual_cli_default.spec.ts"
)


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
                print(f"Target API healthy (attempt {attempt+1}).")
                return proc
        except Exception:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("Target API failed to start in time.")


def _snapshot_user_tests() -> dict:
    """mtimes of USER files under stub/generated_tests/, skipping visual scratchpad."""
    base = os.path.join(REPO, "stub", "generated_tests")
    snap = {}
    if not os.path.exists(base):
        return snap
    for root, _dirs, files in os.walk(base):
        rel_root = os.path.relpath(root, base)
        if rel_root.startswith(VISUAL_SCRATCHPAD_PREFIX):
            continue
        for f in files:
            if f.startswith(VISUAL_SCRATCHPAD_PREFIX):
                continue
            p = os.path.join(root, f)
            try:
                snap[p] = os.path.getmtime(p)
            except OSError:
                pass
    return snap


def _assert_no_user_tests_modified(before: dict, after: dict):
    new = set(after) - set(before)
    removed = set(before) - set(after)
    changed = [p for p in (set(before) & set(after)) if before[p] != after[p]]
    if new or removed or changed:
        raise AssertionError(
            f"D7 violation — user files in stub/generated_tests/ mutated.\nnew={sorted(new)} removed={sorted(removed)} changed={sorted(changed)}"
        )


def _run_visual():
    return subprocess.run(
        ["./bin/cherenkov", "visual", "--target", "http://127.0.0.1:8000"],
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": "."},
        capture_output=True,
        text=True,
    )


def _cleanup():
    for d in BASELINE_DIRS:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
    if os.path.exists(SCRATCHPAD_SPEC):
        os.remove(SCRATCHPAD_SPEC)


def main():
    print("=" * 55)
    print("  CHERENKOV PHASE B1 VISUAL REGRESSION SMOKE")
    print("=" * 55 + "\n")

    _cleanup()
    proc = _start_target()
    try:
        # PASS 1 — baseline auto-initialization
        print("=== PASS 1: Baseline auto-init (no prior baseline) ===")
        before = _snapshot_user_tests()
        r1 = _run_visual()
        print(r1.stdout[-1500:] if r1.stdout else "(no stdout)")
        if r1.returncode != 0:
            print("--- pass 1 stderr ---")
            print(r1.stderr[-1500:])
        assert (
            r1.returncode == 0
        ), f"Pass 1 (baseline init) must exit 0 — got {r1.returncode}"
        _assert_no_user_tests_modified(before, _snapshot_user_tests())
        print("[OK] PASS 1: baseline auto-initialized, user tests untouched.\n")

        # PASS 2 — comparison against just-written baseline
        print("=== PASS 2: Comparison against just-written baseline ===")
        before = _snapshot_user_tests()
        r2 = _run_visual()
        print(r2.stdout[-1500:] if r2.stdout else "(no stdout)")
        if r2.returncode != 0:
            print("--- pass 2 stderr ---")
            print(r2.stderr[-1500:])
        assert (
            r2.returncode == 0
        ), f"Pass 2 (compare) must exit 0 against own baseline — got {r2.returncode}"
        _assert_no_user_tests_modified(before, _snapshot_user_tests())
        print("[OK] PASS 2: comparison GREEN, user tests untouched.\n")

    finally:
        print("Stopping target API server...")
        proc.terminate()
        proc.wait()
        print("Target API stopped cleanly.")
        _cleanup()
        print("Cleanup done (suite re-runnable).")

    print("\n" + "=" * 55)
    print("  ALL VISUAL REGRESSION SMOKE TESTS PASSED!")
    print("=" * 55)


if __name__ == "__main__":
    main()
