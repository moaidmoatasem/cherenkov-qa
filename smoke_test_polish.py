#!/usr/bin/env python3
"""
smoke_test_polish.py — E2E automated smoke tests for Phase 10 POLISH + DOCS.
Proves help systems, bash wrappers, and CI docs checkers work E2E.
"""
import os
import sys
import subprocess
import shutil

def main():
    print("=======================================================")
    print("     CHERENKOV WEEK 1 PHASE 10 POLISH SMOKE TESTS")
    print("=======================================================\n")

    # Defensive auto-restore: if a previous run was aborted/crashed
    src_py = "cherenkov.py"
    backup_py = "cherenkov.py.bak"
    if os.path.exists(backup_py):
        print("⚠️ Warning: cherenkov.py.bak found from a previous aborted run. Auto-restoring...")
        shutil.copy2(backup_py, src_py)
        os.remove(backup_py)

    # 1. Verify bin/cherenkov wrapper executable
    print("Testing bin/cherenkov wrapper...")
    wrapper_path = "./bin/cherenkov"
    assert os.path.exists(wrapper_path), "CLI wrapper bin/cherenkov is missing!"
    print("✓ CLI wrapper binary exists.")

    # 2. Verify help screens
    print("Testing help outputs...")
    commands_to_test = [
        [wrapper_path, "--help"],
        [wrapper_path, "validate", "--help"],
        [wrapper_path, "eject", "--help"]
    ]
    for cmd in commands_to_test:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        assert proc.returncode == 0, f"Command failed: {' '.join(cmd)}"
        assert "usage:" in proc.stdout.lower() or "help" in proc.stdout.lower(), f"Output missing help keywords: {' '.join(cmd)}"
        print(f"✓ Help screen works for: {' '.join(cmd)}")

    # 3. Verify documentation coverage check passes on fully documented files
    print("\nTesting CI Docs Drift Checker (Pass Case)...")
    docs_proc = subprocess.run(
        ["python3", "scripts/ci_docs_check.py"],
        env={**os.environ, "PYTHONPATH": "."},
        capture_output=True,
        text=True
    )
    print("Docs checker stdout:")
    print(docs_proc.stdout)
    assert docs_proc.returncode == 0, "Docs checker failed unexpectedly!"
    print("✓ Docs checker passed successfully on standard documented files.")

    # 4. Verify documentation coverage check FAILS on undocumented commands
    print("Testing CI Docs Drift Checker (Fail Case)...")
    
    # Backup cherenkov.py
    src_py = "cherenkov.py"
    backup_py = "cherenkov.py.bak"
    shutil.copy2(src_py, backup_py)

    try:
        # Inject an undocumented mock subcommand into get_parser()
        with open(src_py, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # Find where eject subparser is defined and inject mockcmd there
        injection_index = -1
        for idx, line in enumerate(lines):
            if 'subparsers.add_parser("eject"' in line:
                injection_index = idx
                break
                
        assert injection_index != -1, "Failed to find injection target inside cherenkov.py"
        
        # Inject undocumented choice parser
        lines.insert(injection_index, '    mock_parser = subparsers.add_parser("mockcmd", help="Mock Undocumented Command")\n')
        
        with open(src_py, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
        print("Injected undocumented choice 'mockcmd' into cherenkov.py.")

        # Re-run docs checker and expect it to fail (code 1)
        fail_proc = subprocess.run(
            ["python3", "scripts/ci_docs_check.py"],
            env={**os.environ, "PYTHONPATH": "."},
            capture_output=True,
            text=True
        )
        print("Injected docs checker stdout:")
        print(fail_proc.stdout)
        
        assert fail_proc.returncode == 1, "Docs checker failed to catch undocumented command choice!"
        assert "undocumented subcommands found" in fail_proc.stdout.lower(), "Docs checker output did not specify missing subcommands!"
        print("✓ Docs checker correctly caught the undocumented subcommand and failed CI successfully!")

    finally:
        # Restore backup cherenkov.py
        if os.path.exists(backup_py):
            shutil.copy2(backup_py, src_py)
            os.remove(backup_py)
            print("Restored cherenkov.py cleanly.")

    print("\n=======================================================")
    print("  ALL PHASE 10 POLISH & DOCS TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    main()
