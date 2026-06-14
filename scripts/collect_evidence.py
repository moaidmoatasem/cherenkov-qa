#!/usr/bin/env python3
"""
collect_evidence.py — Standalone evidence collector for CHERENKOV Track A smoke tests.

Part of A5 #115: 5-QA validation runbook + evidence collector.

Runs each Track A smoke script via subprocess, captures stdout/stderr,
writes timestamped output files to .cherenkov/evidence/, then prints a
summary report.

Usage:
    python3 scripts/collect_evidence.py               # Run all smokes + save evidence
    python3 scripts/collect_evidence.py --dry-run     # List what would run, no execution
    python3 scripts/collect_evidence.py --smoke eject # Run a single named smoke

Exit codes:
    0 — all smokes passed
    1 — one or more smokes failed (or dry-run showed nothing to run)

Design constraints:
    - NO cherenkov imports. This script runs before venv activation is verified.
    - Subprocess-only: each smoke runs as an isolated child process.
    - Suggest-only (D7): produces reports, never modifies test files.
"""

from __future__ import annotations

import argparse
import os
import sys
import subprocess
import datetime
import textwrap
from pathlib import Path
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Smoke test registry — ordered as the runbook prescribes
# ---------------------------------------------------------------------------

SMOKE_SCRIPTS: list[dict] = [
    {
        "name": "core_pipeline",
        "script": "smoke_test.py",
        "description": "Core E2E orchestration pipeline (happy path + circuit breaker failure)",
        "required": True,
    },
    {
        "name": "hitl_race",
        "script": "smoke_test_hitl_race.py",
        "description": "HITL approval thread-safety / race condition guard",
        "required": True,
    },
    {
        "name": "hitl_concurrency",
        "script": "smoke_test_hitl_concurrency.py",
        "description": "HITL concurrent stream isolation",
        "required": True,
    },
    {
        "name": "hitl_cli",
        "script": "smoke_test_hitl_cli.py",
        "description": "HITL CLI subcommands (list / show / approve / reject)",
        "required": True,
    },
    {
        "name": "eject",
        "script": "smoke_test_eject.py",
        "description": "Anti-lock-in eject command (produces vanilla Playwright suite)",
        "required": True,
    },
    {
        "name": "validate",
        "script": "smoke_test_validate.py",
        "description": "Validate CLI — spec conformance drift detection (422 vs 400 bug)",
        "required": True,
    },
]


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


class SmokeResult(NamedTuple):
    name: str
    script: str
    description: str
    passed: bool
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    evidence_path: str | None  # Path where evidence was saved


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    """Return the repository root (parent of this script's directory)."""
    return Path(__file__).resolve().parent.parent


def evidence_dir(root: Path) -> Path:
    """Return (and create if needed) the .cherenkov/evidence/ directory."""
    d = root / ".cherenkov" / "evidence"
    d.mkdir(parents=True, exist_ok=True)
    return d


def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%S")


def run_smoke(
    smoke: dict,
    root: Path,
    ev_dir: Path,
    ts: str,
    timeout: int = 300,
) -> SmokeResult:
    """Run a single smoke script as a subprocess and save its output."""
    script_path = root / smoke["script"]

    if not script_path.exists():
        return SmokeResult(
            name=smoke["name"],
            script=smoke["script"],
            description=smoke["description"],
            passed=False,
            returncode=-1,
            stdout="",
            stderr=f"Script not found: {script_path}",
            duration_s=0.0,
            evidence_path=None,
        )

    import time

    start = time.monotonic()

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONPATH": str(root)},
        )
        passed = proc.returncode == 0
        stdout = proc.stdout
        stderr = proc.stderr
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        passed = False
        stdout = ""
        stderr = f"Timed out after {timeout}s"
        returncode = -2
    except Exception as exc:  # noqa: BLE001
        passed = False
        stdout = ""
        stderr = f"Exception launching subprocess: {exc}"
        returncode = -3

    duration_s = time.monotonic() - start

    # Write evidence file
    evidence_filename = f"{ts}_{smoke['name']}.txt"
    evidence_path = ev_dir / evidence_filename
    _write_evidence(
        evidence_path, smoke, passed, returncode, stdout, stderr, duration_s
    )

    return SmokeResult(
        name=smoke["name"],
        script=smoke["script"],
        description=smoke["description"],
        passed=passed,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration_s=duration_s,
        evidence_path=str(evidence_path),
    )


def _write_evidence(
    path: Path,
    smoke: dict,
    passed: bool,
    returncode: int,
    stdout: str,
    stderr: str,
    duration_s: float,
) -> None:
    """Write captured output to an evidence file."""
    verdict = "PASS" if passed else "FAIL"
    header = textwrap.dedent(f"""\
        ========================================================
        CHERENKOV Evidence Capture — {smoke['name']}
        ========================================================
        Script      : {smoke['script']}
        Description : {smoke['description']}
        Verdict     : {verdict}
        Return code : {returncode}
        Duration    : {duration_s:.2f}s
        Captured at : {datetime.datetime.now().isoformat()}
        ========================================================

    """)
    stdout_block = (
        f"--- STDOUT ---\n{stdout}\n" if stdout else "--- STDOUT ---\n(empty)\n"
    )
    stderr_block = (
        f"--- STDERR ---\n{stderr}\n" if stderr else "--- STDERR ---\n(empty)\n"
    )
    path.write_text(header + stdout_block + "\n" + stderr_block, encoding="utf-8")


def print_summary(results: list[SmokeResult], ev_dir: Path) -> None:
    """Print the final evidence summary report to stdout."""
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    total = len(results)

    sep = "=" * 60
    print(f"\n{sep}")
    print("  CHERENKOV — Evidence Collector Summary")
    print(sep)
    print(f"  Total smokes : {total}")
    print(f"  Passed       : {len(passed)}")
    print(f"  Failed       : {len(failed)}")
    print(f"  Evidence dir : {ev_dir}")
    print(sep)

    for r in results:
        status = "✓ PASS" if r.passed else "✗ FAIL"
        path_display = Path(r.evidence_path).name if r.evidence_path else "n/a"
        print(f"  {status}  [{r.name:<20}]  {r.duration_s:5.1f}s  → {path_display}")

    print(sep)

    if failed:
        print("\n  FAILED SMOKES:")
        for r in failed:
            print(f"\n  [{r.name}] — return code {r.returncode}")
            if r.stderr:
                # Show first 10 lines of stderr for quick diagnosis
                lines = r.stderr.splitlines()[:10]
                for line in lines:
                    print(f"      {line}")
            if r.evidence_path:
                print(f"      Full output: {r.evidence_path}")
        print()
    else:
        print("\n  ALL SMOKES PASSED — ready for QA reviewer sessions.\n")


def print_dry_run(smokes: list[dict], root: Path) -> None:
    """Print what would be run without executing anything."""
    print("\n[DRY RUN] Evidence collector would execute the following smokes:\n")
    for i, smoke in enumerate(smokes, 1):
        script_path = root / smoke["script"]
        exists_marker = "✓" if script_path.exists() else "✗ (MISSING)"
        print(f"  {i}. {smoke['name']:<20} {exists_marker}")
        print(f"       Script     : {smoke['script']}")
        print(f"       Description: {smoke['description']}")
        print(f"       Required   : {'yes' if smoke['required'] else 'no'}")
        print()
    ev_dir = root / ".cherenkov" / "evidence"
    print(f"  Evidence would be saved to: {ev_dir}/")
    print("  Filename pattern          : <timestamp>_<smoke_name>.txt\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="collect_evidence.py",
        description=(
            "CHERENKOV standalone evidence collector.\n"
            "Runs Track A smoke tests and saves output to .cherenkov/evidence/."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python3 scripts/collect_evidence.py                # Run all smokes
              python3 scripts/collect_evidence.py --dry-run      # Preview only
              python3 scripts/collect_evidence.py --smoke eject  # Single smoke
              python3 scripts/collect_evidence.py --timeout 120  # Shorter timeout
        """),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List smokes that would run without executing them.",
    )
    parser.add_argument(
        "--smoke",
        metavar="NAME",
        help="Run only the named smoke (e.g. eject, validate, core_pipeline).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Per-smoke timeout in seconds (default: 300).",
    )
    parser.add_argument(
        "--no-required-only",
        action="store_true",
        help="Include non-required smokes (if any are ever added).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()

    # Filter smokes
    smokes = SMOKE_SCRIPTS
    if not args.no_required_only:
        smokes = [s for s in smokes if s["required"]]
    if args.smoke:
        matching = [s for s in smokes if s["name"] == args.smoke]
        if not matching:
            available = ", ".join(s["name"] for s in SMOKE_SCRIPTS)
            print(
                f"Error: unknown smoke name '{args.smoke}'. Available: {available}",
                file=sys.stderr,
            )
            return 1
        smokes = matching

    if args.dry_run:
        print_dry_run(smokes, root)
        return 0

    # Validate working directory
    if not (root / "cherenkov.py").exists() and not (root / "cherenkov").is_dir():
        print(
            f"Error: script must be run from the cherenkov-qa repo root.\n"
            f"Detected root: {root}\n"
            f"Hint: run `python3 scripts/collect_evidence.py` from the repo root.",
            file=sys.stderr,
        )
        return 1

    ev_dir = evidence_dir(root)
    ts = timestamp()

    print(f"\nCHERENKOV Evidence Collector — {datetime.datetime.now().isoformat()}")
    print(f"Repo root    : {root}")
    print(f"Evidence dir : {ev_dir}")
    print(f"Running {len(smokes)} smoke(s)...\n")

    results: list[SmokeResult] = []
    for smoke in smokes:
        print(f"  → [{smoke['name']}] {smoke['description']}")
        result = run_smoke(smoke, root, ev_dir, ts, timeout=args.timeout)
        status = "PASS" if result.passed else "FAIL"
        print(
            f"    {status}  ({result.duration_s:.1f}s)  evidence: {Path(result.evidence_path).name if result.evidence_path else 'n/a'}"
        )
        results.append(result)

    print_summary(results, ev_dir)

    all_passed = all(r.passed for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
