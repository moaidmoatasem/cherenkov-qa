#!/usr/bin/env python3
"""
smoke_test_polish.py -- E2E automated smoke tests for Phase 10 POLISH + DOCS.
Proves help systems, bash wrappers, and CI docs checkers work E2E.
"""

import os
import subprocess
import shutil


def main():
    print("=======================================================")
    print("     CHERENKOV WEEK 1 PHASE 10 POLISH SMOKE TESTS")
    print("=======================================================\n")

    # 1. Verify bin/cherenkov wrapper executable
    print("Testing bin/cherenkov wrapper...")
    wrapper_path = "./bin/cherenkov"
    assert os.path.exists(wrapper_path), "CLI wrapper bin/cherenkov is missing!"
    import platform as _pf

    if _pf.system() == "Windows":
        wrapper_cmd = ["bash.exe", wrapper_path]
    else:
        wrapper_cmd = [wrapper_path]
    print("[PASS] CLI wrapper binary exists.")

    # 2. Verify help screens
    print("Testing help outputs...")
    commands_to_test = [
        wrapper_cmd + ["--help"],
        wrapper_cmd + ["validate", "--help"],
        wrapper_cmd + ["eject", "--help"],
    ]
    for cmd in commands_to_test:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0, f"Command failed: {' '.join(cmd)}"
        assert (
            "usage:" in proc.stdout.lower() or "help" in proc.stdout.lower()
        ), f"Output missing help keywords: {' '.join(cmd)}"
        print(f"[PASS] Help screen works for: {' '.join(cmd)}")

    # 3. Verify documentation coverage check passes on fully documented files
    print("\nTesting CI Docs Drift Checker (Pass Case)...")
    docs_proc = subprocess.run(
        ["python3", "scripts/ci_docs_check.py"],
        env={**os.environ, "PYTHONPATH": "."},
        capture_output=True,
        text=True,
    )
    print("Docs checker stdout:")
    print(docs_proc.stdout)
    assert docs_proc.returncode == 0, "Docs checker failed unexpectedly!"
    print("[PASS] Docs checker passed successfully on standard documented files.")

    # 4. Verify documentation coverage check FAILS when docs are incomplete
    print("Testing CI Docs Drift Checker (Fail Case)...")

    # Write a stripped docs file that omits the `verify` subcommand
    import tempfile
    docs_path = os.path.join("docs", "GETTING_STARTED.md")
    with open(docs_path, "r", encoding="utf-8") as f:
        full_docs = f.read()

    # Strip all occurrences of `verify` to simulate undocumented command
    stripped_docs = full_docs.replace("`verify`", "REMOVED_FOR_TEST")

    tmp_docs = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    )
    try:
        tmp_docs.write(stripped_docs)
        tmp_docs.close()

        # Re-run docs checker against the stripped docs and expect it to fail (exit 1)
        fail_proc = subprocess.run(
            ["python3", "scripts/ci_docs_check.py", "--docs-file", tmp_docs.name],
            env={**os.environ, "PYTHONPATH": "."},
            capture_output=True,
            text=True,
        )
        print("Stripped docs checker stdout:")
        print(fail_proc.stdout)

        assert (
            fail_proc.returncode == 1
        ), "Docs checker failed to catch undocumented command!"
        assert (
            "undocumented subcommands found" in fail_proc.stdout.lower()
        ), "Docs checker output did not specify missing subcommands!"
        print(
            "[PASS] Docs checker correctly caught the undocumented subcommand and failed CI successfully!"
        )
    finally:
        os.unlink(tmp_docs.name)

    print("\n=======================================================")
    print("  ALL PHASE 10 POLISH & DOCS TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    main()
