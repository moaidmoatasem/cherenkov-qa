"""`cherenkov check` — git-ref baselines, auto-detection, exit codes, formats."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from cherenkov.cli.commands.check_cmd import COMMENT_MARKER, check_cmd

DEMO = Path(__file__).parents[2] / "demos" / "catch-the-ai-cheating"
GOOD, WEAKENED, DELETED = (DEMO / n for n in ("suite_good.py", "suite_cheat_weakened.py", "suite_cheat_deleted.py"))


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=repo, check=True,
                   capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A git repo whose HEAD~1 has the honest suite in tests/."""
    _git(tmp_path, "init", "-q")
    (tmp_path / "tests").mkdir()
    shutil.copy(GOOD, tmp_path / "tests" / "test_api.py")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "honest")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _cheat(repo: Path, source: Path) -> None:
    shutil.copy(source, repo / "tests" / "test_api.py")
    _git(repo, "commit", "-q", "-am", "agent edit")


def _run(*args: str):
    return CliRunner().invoke(check_cmd, list(args))


def test_weakened_assertion_vs_git_ref_fails_with_exit_1(repo):
    _cheat(repo, WEAKENED)
    result = _run("--baseline", "HEAD~1")
    assert result.exit_code == 1, result.output
    assert "WEAKENED" in result.output


def test_deleted_test_vs_git_ref_fails(repo):
    _cheat(repo, DELETED)
    result = _run("tests", "--baseline", "HEAD~1")
    assert result.exit_code == 1
    assert "DELETED" in result.output


def test_unchanged_suite_passes_and_states_scope(repo):
    (repo / "README").write_text("x")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "docs")
    result = _run("--baseline", "HEAD~1")
    assert result.exit_code == 0, result.output
    assert "PASS (2/3 checks)" in result.output
    assert "HALLUCINATED" in result.output  # listed under NOT_CHECKED: no --spec


def test_no_baseline_is_honest_about_what_ran(repo):
    result = _run()
    assert result.exit_code == 0
    assert "NOT_CHECKED" in result.output and "WEAKENED" in result.output


def test_path_baseline_still_works(repo, tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    shutil.copy(GOOD, base / "test_api.py")
    _cheat(repo, WEAKENED)
    assert _run("tests", "--baseline", str(base)).exit_code == 1


def test_bad_ref_is_a_usage_error(repo):
    result = _run("--baseline", "no-such-ref-xyz")
    assert result.exit_code == 2
    assert "neither an existing path nor a git ref" in result.output


def test_missing_tests_dir_is_a_usage_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = _run()
    assert result.exit_code == 2
    assert "No tests path given" in result.output


def test_json_format(repo):
    _cheat(repo, WEAKENED)
    result = _run("--baseline", "HEAD~1", "--format", "json")
    data = json.loads(result.output)
    assert result.exit_code == 1 and data["clean"] is False
    assert data["baseline"] == "HEAD~1" and {"WEAKENED", "DELETED"} <= set(data["checks_run"])


def test_md_format_is_a_sticky_comment_body(repo):
    _cheat(repo, WEAKENED)
    result = _run("--baseline", "HEAD~1", "--format", "md", "--output", str(repo / "c.md"))
    assert result.exit_code == 1
    assert result.output.startswith(COMMENT_MARKER)
    assert "**FAIL**" in result.output and "`WEAKENED`" in result.output
    assert (repo / "c.md").read_text().startswith(COMMENT_MARKER)


def test_check_is_registered_with_the_cli():
    from cherenkov.cli.core import _register_commands, cli
    _register_commands()
    assert "check" in cli.commands and "check-suite" in cli.commands
