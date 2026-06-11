#!/usr/bin/env python3
"""
smoke_test_visual.py — E2E Visual testing integration test for CHERENKOV.
Proves snapshot baseline initialization and layout validation checks.
"""
import os
import subprocess
import time
import sys
import shutil
import pytest

from cherenkov.execution.visual_diff import VisualDiffEngine

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
    print("      CHERENKOV TRACK B VISUAL TESTING SMOKE TEST")
    print("=======================================================\n")

    # Clean existing snapshots to verify fresh initialization
    snapshots_dir = "stub/generated_tests/visual_regression_baseline_ui.spec.ts-snapshots"
    if os.path.exists(snapshots_dir):
        print(f"Cleaning existing snapshots at {snapshots_dir}...")
        shutil.rmtree(snapshots_dir)

    server_proc = None
    try:
        # 1. Spin target server
        server_proc = start_target_server()

        # 3. Instantiate Visual Engine
        visual_engine = VisualDiffEngine(run_id="visual_smoke")

        # 4. First run: should initialize snapshots baseline
        print("\nPass 1: Running visual validation (Expected: Baseline initialization)...")
        res1 = visual_engine.run_visual_validation("http://127.0.0.1:8000/")
        assert res1["passed"], f"Baseline initialization failed: {res1.get('error_output', '')}"
        print("✓ Baseline initialized cleanly.")

        # Confirm snapshot files were written to disk
        assert os.path.exists(snapshots_dir), "Snapshot baseline directory was not created."
        snapshot_files = os.listdir(snapshots_dir)
        assert len(snapshot_files) > 0, "No baseline snapshot images were captured."
        print(f"✓ Snapshot baseline written: {snapshot_files}")

        # 5. Second run: should compare and pass
        print("\nPass 2: Running visual validation (Expected: Comparison Pass)...")
        res2 = visual_engine.run_visual_validation("http://127.0.0.1:8000/")
        assert res2["passed"], f"Visual comparison failed: {res2.get('error_output', '')}"
        print("✓ Visual verification comparison PASSED.")

        print("\n=======================================================")
        print("     CHERENKOV VISUAL INTEGRATION TESTS PASSED!")
        print("=======================================================")
        sys.exit(0)

    except Exception as e:
        print(f"\n🛑 Visual Smoke Test Failed: {e}")
        sys.exit(1)

    finally:
        # Clean up target server process
        if server_proc:
            print("\nShutting down Target API Server...")
            server_proc.terminate()
            server_proc.wait()


VISUAL_SPEC = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../stub/generated_tests/visual_regression_baseline_ui.spec.ts"
))


@pytest.mark.skipif(os.name == "nt", reason="Windows CMD does not support UNC paths as current directory")
@pytest.mark.skipif(not os.path.exists(VISUAL_SPEC), reason="visual_regression_baseline_ui.spec.ts not generated — run the visual pipeline first (VisualDiffEngine consumes, never creates, this spec)")
def test_legacy_visual():
    try:
        main()
    except SystemExit as e:
        if e.code != 0:
            raise AssertionError(f"Test failed with exit code {e.code}")

