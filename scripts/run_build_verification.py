#!/usr/bin/env python3
"""
Executes full build & test verification commands in WSL:
- pytest on python test suite
- npm run compile & npm run lint in vscode/
- cargo check in desktop/src-tauri/
- standalone CherenkovTool test script
- standalone MCP stub tools test script
"""

import os
import subprocess
import sys

def print_flush(msg: str) -> None:
    """Print message and immediately flush stdout.

    Args:
        msg: Message string to print.

    Returns:
        None.
    """
    print(msg)
    sys.stdout.flush()

def run_cmd(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Execute command process with augmented PATH environment.

    Args:
        cmd: List of command arguments.
        cwd: Optional working directory string.

    Returns:
        Tuple containing return code integer, stdout string, and stderr string.
    """
    print_flush(f"Executing: {' '.join(cmd)} (cwd={cwd or '.'})")
    env = os.environ.copy()
    home = os.path.expanduser("~")
    user_paths = [
        os.path.join(home, ".local", "bin"),
        os.path.join(home, ".cargo", "bin"),
        os.path.join(home, ".nvm", "versions", "node", "v20.18.0", "bin"),
        os.path.join(home, ".local", "opt", "go", "bin"),
    ]
    env["PATH"] = ":".join(user_paths) + ":" + env.get("PATH", "")
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
        print_flush(f"Exit Code: {proc.returncode}")
        if proc.stdout:
            print_flush("--- STDOUT ---")
            print_flush(proc.stdout[:2000])
        if proc.stderr:
            print_flush("--- STDERR ---")
            print_flush(proc.stderr[:2000])
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as exc:
        print_flush(f"Execution Exception: {exc}")
        return 1, "", str(exc)

def main() -> int:
    """Run build verification across Python, Go, and Tauri targets.

    Returns:
        Exit code integer (0 if all targets build successfully, 1 otherwise).
    """
    repo_root = "/home/moaid/cherenkov-qa"
    results = {}

    print_flush("=== STARTING FULL BUILD & TEST VERIFICATION ===")

    # 1. Pytest suite
    code, out, err = run_cmd(
        ["python3", "-m", "pytest", "tests/test_jira_exporter.py", "tests/test_perf_integration.py", "tests/test_mena_compliance.py", "tests/standalone/test_langchain_tool.py", "tests/standalone/test_mcp.py"],
        cwd=repo_root
    )
    results["pytest"] = (code == 0)

    # 2. Standalone CherenkovTool verification
    code, out, err = run_cmd(
        ["python3", "scripts/verify_cherenkov_tool_standalone.py"],
        cwd=repo_root
    )
    results["standalone_cherenkov_tool"] = (code == 0)

    # 3. Standalone MCP stub tools verification
    code, out, err = run_cmd(
        ["python3", "scripts/verify_mcp_stub_tools_standalone.py"],
        cwd=repo_root
    )
    results["standalone_mcp_tools"] = (code == 0)

    # 4. VSCode npm run compile
    code, out, err = run_cmd(
        ["npm", "run", "compile"],
        cwd=os.path.join(repo_root, "vscode")
    )
    results["npm_compile"] = (code == 0)

    # 5. VSCode npm run lint
    code, out, err = run_cmd(
        ["npm", "run", "lint"],
        cwd=os.path.join(repo_root, "vscode")
    )
    results["npm_lint"] = (code == 0)

    # 6. Tauri Desktop cargo check
    code, out, err = run_cmd(
        ["cargo", "check"],
        cwd=os.path.join(repo_root, "desktop", "src-tauri")
    )
    results["cargo_check"] = (code == 0)

    # Summary
    print_flush("\n=== VERIFICATION SUMMARY ===")
    all_passed = True
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print_flush(f"  {name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print_flush("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        return 0
    else:
        print_flush("\nSOME VERIFICATION CHECKS FAILED.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
