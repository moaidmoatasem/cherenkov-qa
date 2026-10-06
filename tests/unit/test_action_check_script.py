"""scripts/action_check.sh — the `mode: check` path of action.yml, run for real."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "action_check.sh"
DEMO = ROOT / "demos" / "catch-the-ai-cheating"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def _git(repo, *a):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "tests").mkdir()
    shutil.copy(DEMO / "suite_good.py", tmp_path / "tests" / "test_api.py")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "honest")
    return tmp_path


def _run(repo, **env):
    # A `cherenkov` shim on PATH so the script runs the code under test.
    shim = repo / ".bin"
    shim.mkdir(exist_ok=True)
    (shim / "cherenkov").write_text(f'#!/bin/sh\nexec "{sys.executable}" -m cherenkov "$@"\n')
    (shim / "cherenkov").chmod(0o755)
    e = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}", "PYTHONPATH": str(ROOT),
         "GITHUB_OUTPUT": str(repo / "out.txt"), "GITHUB_STEP_SUMMARY": str(repo / "sum.md"),
         "INPUT_OUTPUT_PATH": str(repo / "c.md"), **env}
    e.pop("GITHUB_TOKEN", None)
    return subprocess.run(["bash", str(SCRIPT)], cwd=repo, env=e, capture_output=True, text=True)


def test_violation_fails_writes_summary_and_outputs(repo):
    shutil.copy(DEMO / "suite_cheat_weakened.py", repo / "tests" / "test_api.py")
    _git(repo, "commit", "-q", "-am", "agent")
    r = _run(repo, INPUT_BASELINE="HEAD~1", INPUT_FAIL_ON_DRIFT="true")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "<!-- cherenkov-check -->" in (repo / "sum.md").read_text()
    out = (repo / "out.txt").read_text()
    assert "drift-detected=true" in out and "violations=3" in out


def test_fail_on_drift_false_reports_but_passes(repo):
    shutil.copy(DEMO / "suite_cheat_weakened.py", repo / "tests" / "test_api.py")
    _git(repo, "commit", "-q", "-am", "agent")
    assert _run(repo, INPUT_BASELINE="HEAD~1", INPUT_FAIL_ON_DRIFT="false").returncode == 0


def test_clean_change_passes(repo):
    (repo / "README").write_text("x")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "docs")
    r = _run(repo, INPUT_BASELINE="HEAD~1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "drift-detected=false" in (repo / "out.txt").read_text()


def test_missing_baseline_is_a_usage_error(repo):
    r = _run(repo)
    assert r.returncode == 2 and "needs a baseline" in r.stderr
