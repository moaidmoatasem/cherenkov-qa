#!/usr/bin/env python3
"""
smoke_test_deep_healing.py — E2E deep self-healing isolated sandbox integration test.
Proves workspace replication, LLM-based repair sweeps in sandbox, and unified diff output.
"""

import os
import subprocess
import time
import sys
import shutil
import pytest

from cherenkov.healing.diagnose import Diagnoser


def start_target_server():
    """Starts the mock range FastAPI server."""
    print("Starting Target API Server...")
    cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), "../target"))
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "target_api:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)  # Wait for startup
    return proc


def main():
    print("=======================================================")
    print("      CHERENKOV TRACK B DEEP SELF-HEALING SMOKE TEST")
    print("=======================================================\n")

    # Clean existing generated spec or diff if any
    failing_spec = "stub/generated_tests/failing_assertion.spec.ts"
    healed_diff = ".cherenkov/healed_diffs/failing_assertion.diff"

    if os.path.exists(failing_spec):
        os.remove(failing_spec)
    if os.path.exists(healed_diff):
        os.remove(healed_diff)

    # 1. Create a temporary E2E test file with a deliberate status code assertion failure
    print("Creating temporary E2E test file with deliberate failure...")
    failing_code = """import { test, expect } from '@playwright/test';
import { client } from '../client';

test('create user failing assertion spec', async () => {
  const { response } = await client.POST('/users', {
    body: {
      email: 'deep_healing_test@cherenkov.local',
      password: 'secure_password_123'
    }
  });
  // Deliberate assertion failure: real server returns 201, but we assert 500
  expect(response.status).toBe(500);
});
"""
    os.makedirs(os.path.dirname(failing_spec), exist_ok=True)
    with open(failing_spec, "w", encoding="utf-8") as f:
        f.write(failing_code)

    # Clean up stale sandbox dirs from previous runs
    sandbox_base = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../.cherenkov")
    )
    for d in os.listdir(sandbox_base):
        if d.startswith("sandbox_deep_heal"):
            full = os.path.join(sandbox_base, d)
            shutil.rmtree(full, ignore_errors=True)

    server_proc = None
    try:
        # 2. Spin target server
        server_proc = start_target_server()

        # 3. Instantiate Diagnoser
        diagnoser = Diagnoser(run_id="deep_heal_smoke")

        # 4. Trigger Deep Self-Healing Sandbox Repair
        print("\nTriggering isolated sandbox repair cycle...")
        result = diagnoser.run_sandbox_repair(
            scenario_id="failing_assertion",
            original_test_filename="failing_assertion.spec.ts",
            failure_log="expect(response.status).toBe(500) // Received: 201",
            api_url="http://127.0.0.1:8000",
            max_attempts=3,
        )

        # 5. Verify results
        assert result.get(
            "healed"
        ), f"Deep self-healing sandbox cycle failed: {result.get('message')}"
        print(
            "✓ Sandbox repair completed successfully! Green state achieved in sandbox."
        )

        # Verify unified diff was written to disk
        assert os.path.exists(healed_diff), "Unified diff file was not written to disk."
        print(f"✓ Unified diff generated successfully: {healed_diff}")

        with open(healed_diff, "r", encoding="utf-8") as df:
            diff_content = df.read()
        print("\n--- GENERATED UNIFIED DIFF SUGGESTION ---")
        print(diff_content)
        print("-----------------------------------------\n")

        # Ensure the corrected status (not the original 500) exists inside the diff
        # Check that the ADDED line (+) doesn't contain the original failing assertion
        assert (
            "+  expect(response.status).toBe(500)" not in diff_content
        ), "Unified diff adds the original failing assertion toBe(500)."
        assert (
            "+  expect(response.status).toBe(" in diff_content
        ), "Unified diff did not contain a corrected assertion status in added lines."
        print("✓ Unified diff contains a corrected healed status assertion.")

        # Ensure original E2E test file was untouched (honoring the suggest-only trust rule)
        with open(failing_spec, "r", encoding="utf-8") as f:
            intact_code = f.read()
        assert (
            "toBe(500)" in intact_code
        ), "Suggest-only rule violated: original test file was auto-modified."
        print(
            "✓ Suggest-only trust rule honored: original test file remains untouched."
        )

        print("\n=======================================================")
        print("   CHERENKOV DEEP SELF-HEALING SMOKE TESTS PASSED!")
        print("=======================================================")
        sys.exit(0)

    except Exception as e:
        print(f"\n🛑 Deep Healing Smoke Test Failed: {e}")
        sys.exit(1)

    finally:
        # Clean up temporary test file
        if os.path.exists(failing_spec):
            print("\nCleaning up temporary spec test file...")
            os.remove(failing_spec)

        # Clean up target server process
        if server_proc:
            print("Shutting down Target API Server...")
            server_proc.terminate()
            server_proc.wait()


def _ollama_available() -> bool:
    """Deep healing repairs the spec via the local LLM; probe for a live Ollama."""
    import urllib.request

    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except Exception:
        return False


@pytest.mark.skipif(
    os.name == "nt",
    reason="Windows/WSL UNC path limitations prevent sandbox symlink operations",
)
@pytest.mark.skipif(
    not _ollama_available(),
    reason="Ollama not reachable — sandbox healing needs the local LLM to repair the failing spec",
)
@pytest.mark.xfail(
    reason="Local LLMs are non-deterministic; deep self-healing cycles may not always converge in 3 attempts."
)
def test_legacy_deep_healing():
    try:
        main()
    except SystemExit as e:
        if e.code != 0:
            raise AssertionError(f"Test failed with exit code {e.code}")
