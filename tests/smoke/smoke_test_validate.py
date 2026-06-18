#!/usr/bin/env python3
"""
smoke_test_validate.py — automated integration test E2E verifying Phase 8 validation CLI reports.
"""

import os
import sys
import time
import subprocess
import requests
import hashlib


def _to_wsl_path(windows_path: str) -> str:
    """Convert a \\\\wsl.localhost\\<distro>\\foo\\bar path to a WSL Linux path (/foo/bar)."""
    parts = windows_path.replace("/", "\\").split("\\")
    # parts: ['', '', 'wsl.localhost', '<distro>', 'home', 'moaid', ...]
    linux_parts = parts[4:]
    return "/" + "/".join(linux_parts)


def _start_target_api():
    """Start the target API and return (proc_or_none, base_url)."""
    target_dir = os.path.abspath("target")
    if sys.platform == "win32" and (
        target_dir.startswith("\\\\") or target_dir.startswith("//")
    ):
        linux_target = _to_wsl_path(target_dir)
        subprocess.run(
            [
                "wsl.exe",
                "-e",
                "bash",
                "-c",
                "tmux kill-session -t ck_target 2>/dev/null; echo done",
            ],
            capture_output=True,
            timeout=10,
        )
        subprocess.Popen(
            [
                "wsl.exe",
                "-e",
                "bash",
                "-c",
                "tmux new-session -d -s ck_target "
                f"'cd {linux_target} && "
                "uvicorn target_api:app --host 0.0.0.0 --port 8000'",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            wsl_ip = subprocess.run(
                ["wsl.exe", "-e", "bash", "-c", "hostname -I | cut -d' ' -f1"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
        except Exception:
            wsl_ip = "localhost"
        return None, f"http://{wsl_ip}:8000"
    # Free port 8000 of any stale/orphaned listener before binding, so a leftover
    # process from an interrupted run can't make this look like a tool failure.
    subprocess.run(["fuser", "-k", "8000/tcp"], capture_output=True, timeout=5)
    proc = subprocess.Popen(
        ["uvicorn", "target_api:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=target_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc, "http://localhost:8000"


def _stop_target_api(proc):
    """Stop the target API."""
    if proc is not None:
        proc.terminate()
        proc.wait()
    else:
        subprocess.run(
            [
                "wsl.exe",
                "-e",
                "bash",
                "-c",
                "tmux kill-session -t ck_target 2>/dev/null; echo done",
            ],
            timeout=5,
        )


def main():
    print("=======================================================")
    print("     CHERENKOV WEEK 1 PHASE 8 VALIDATE SMOKE TESTS")
    print("=======================================================\n")

    # 1. Start the target API in standard mode on port 8000
    print("Starting target API on port 8000...")
    proc, base_url = _start_target_api()

    # 2. Block until target API is healthy
    healthy = False
    health_url = f"{base_url}/health"
    for attempt in range(30):
        try:
            resp = requests.get(health_url, timeout=2)
            if resp.status_code == 200:
                healthy = True
                print(f"Target API is healthy and online (attempt {attempt+1}).")
                break
        except Exception:
            time.sleep(1)

    if not healthy:
        print("Error: Target API failed to start in time.")
        _stop_target_api(proc)
        return

    # 3. Ensure git tree is clean for generated_tests so the suggest-only constraint check works
    print("Restoring and cleaning stub/generated_tests to pristine state...")
    subprocess.run(
        ["git", "restore", "stub/generated_tests/"],
        cwd=os.path.abspath("."),
        check=False,
    )
    subprocess.run(
        ["git", "clean", "-fd", "stub/generated_tests/"],
        cwd=os.path.abspath("."),
        check=False,
    )

    def _get_tests_hash():
        tests_dir = os.path.abspath("stub/generated_tests")
        h = hashlib.sha256()
        if os.path.exists(tests_dir):
            for f in sorted(os.listdir(tests_dir)):
                if f.endswith(".spec.ts"):
                    with open(os.path.join(tests_dir, f), "rb") as file:
                        h.update(file.read())
        return h.hexdigest()

    print("Calculating pre-run hash of generated_tests...")
    pre_hash = _get_tests_hash()

    # 4. Execute cherenkov_validate.py against target API
    print("Executing validation subcommand CLI against target API...")
    try:
        val_proc = subprocess.run(
            ["python3", "cherenkov.py", "validate", "--target", base_url],
            env={**os.environ, "PYTHONPATH": "."},
            capture_output=True,
            text=True,
            check=True,
        )
        stdout = val_proc.stdout

        print("\n--- CLI TIGHTENING REPORT OUTPUT ---")
        print(stdout)
        print("------------------------------------\n")

        # 4. Assert report details
        assert (
            "consider -> expect(data.email).toBe('test@example.com')" in stdout
        ), "Missing suggested string value assertion!"
        assert (
            "consider -> expect(data.email).toBe(body.email)" in stdout
        ), "Missing suggested payload match assertion!"
        print(
            "[OK] Successfully verified value tightening suggestions for /users POST happy_path endpoint."
        )

        assert (
            "password_too_short [FAILED]" in stdout
        ), "Failed to capture password_too_short spec conformance drift!"
        print(
            "[OK] Successfully verified spec-to-implementation conformance failure (RED) report."
        )

        assert (
            "zero test files were auto-modified by validation" in stdout
        ), "Suggest-only trust constraint violated (test files were modified)!"

        post_hash = _get_tests_hash()
        assert (
            pre_hash == post_hash
        ), f"Hash-guard regression: test files were modified on disk! Pre: {pre_hash}, Post: {post_hash}"
        print(
            "[OK] Successfully verified suggest-only sandbox constraint assertion (no files modified, hashes match)."
        )

    except subprocess.CalledProcessError as e:
        print(f"Validation CLI execution failed: {e}")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        raise e
    finally:
        # 5. Clean up Target API background task
        print("Stopping target API server...")
        _stop_target_api(proc)
        print("Target API stopped cleanly.")

    print("\n=======================================================")
    print("  ALL VALIDATE SUBCOMMAND SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    main()
