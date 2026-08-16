"""Tests for the CI-template arm of scripts/check_cli_flags.py.

The guard was extended to scan `ci/**` and `action.yml` (findings F2/F3 in
docs/CAPABILITY_COVERAGE.md) but shipped without tests. The scanning logic is
subtle in ways that are easy to regress silently:

  * CI files build commands in three different shapes, and the shape that hid
    the original `--export-jira` bug never puts the flag on the same line as
    the command;
  * comments must not parse as invocations — `// assuming cherenkov is
    installed` otherwise reads as a command named "is installed", which made
    the Jenkins file look multi-command and disabled the append check entirely;
  * the append check is deliberately silent on multi-command files, to stay
    free of false positives.

These exercise `main()` end to end against a temporary repo root, so they pin
real behaviour rather than a reimplementation. `_REFERENCE_PATH` is computed at
import time from the real repo, so the reference.md arm still resolves and stays
clean while the CI arm is driven by fixtures.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "check_cli_flags.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_cli_flags_under_test", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def guard():
    return _load()


@pytest.fixture
def run_guard(guard, tmp_path, monkeypatch, capsys):
    """Run the guard with `ci/` fixtures, returning (exit_code, output)."""

    def _run(rel_path: str, content: str):
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        monkeypatch.setattr(guard, "_REPO_ROOT", str(tmp_path))
        code = guard.main()
        return code, capsys.readouterr().out

    return _run


# ── The three shapes these files actually use ────────────────────────────────


def test_catches_bogus_flag_on_a_single_line_invocation(run_guard):
    code, out = run_guard(
        "ci/gitlab.yml",
        "  - cherenkov validate --target $URL --not-a-real-flag\n",
    )
    assert code == 1
    assert "--not-a-real-flag" in out
    assert "ci/gitlab.yml" in out.replace("\\", "/")


def test_catches_bogus_flag_across_a_shell_continuation(run_guard):
    """action.yml spreads one invocation over many lines with trailing `\\`."""
    code, out = run_guard(
        "ci/action-like.yml",
        "        cherenkov validate \\\n"
        '          --spec "x" \\\n'
        "          --totally-invented\n",
    )
    assert code == 1
    assert "--totally-invented" in out


def test_catches_bogus_flag_appended_to_a_command_variable(run_guard):
    """The Jenkins shape — and the one that hid the original bug.

    The flag never appears on the same line as the command, so line-local
    matching cannot attribute it.
    """
    code, out = run_guard(
        "ci/jenkins/vars/x.groovy",
        'def cmd = "cherenkov validate --target ${t} --quiet"\n'
        'cmd += " --export-jira"\n',
    )
    assert code == 1
    assert "--export-jira" in out


# ── False-positive traps present in the real files ───────────────────────────


def test_flag_named_only_inside_a_comment_is_not_reported(run_guard):
    """The repaired Jenkins template documents the removed flag in a comment."""
    code, out = run_guard(
        "ci/jenkins/vars/x.groovy",
        "// exportJira used to append --export-jira, which exists on no command\n"
        '# --also-not-real in a yaml-style comment\n'
        'def cmd = "cherenkov validate --target ${t} --quiet"\n',
    )
    assert code == 0, out


def test_package_install_is_not_parsed_as_an_invocation(run_guard):
    """`pip install cherenkov-qa --quiet` must not attribute --quiet to a command."""
    code, out = run_guard(
        "ci/gitlab.yml",
        "  - pip install cherenkov-qa\n  - pip install something --user\n",
    )
    assert code == 0, out


def test_prose_comment_does_not_parse_as_a_command(run_guard):
    """`// assuming cherenkov is installed` must not read as command 'is'."""
    code, out = run_guard(
        "ci/jenkins/vars/x.groovy",
        "// Execute assuming cherenkov is installed on the agent\n"
        'def cmd = "cherenkov validate --target ${t}"\n',
    )
    assert code == 0, out


def test_valid_flags_pass(run_guard):
    code, out = run_guard(
        "ci/gitlab.yml",
        "  - cherenkov validate --target $URL --spec $SPEC --fail-on-drift --quiet\n",
    )
    assert code == 0, out


def test_append_check_stays_silent_on_multi_command_files(run_guard):
    """A documented tradeoff: appends are only attributable with one command.

    Pinned so the silence stays deliberate rather than becoming an accident.
    """
    code, out = run_guard(
        "ci/multi.groovy",
        'def a = "cherenkov validate --target x"\n'
        'def b = "cherenkov report --format junit"\n'
        'a += " --not-a-real-flag"\n',
    )
    assert code == 0, out


# ── The regression this closes, on the shipped tree ──────────────────────────


def test_jenkins_template_no_longer_appends_the_phantom_flag():
    groovy = (
        _REPO_ROOT / "ci" / "jenkins" / "vars" / "cherenkovValidate.groovy"
    ).read_text(encoding="utf-8")
    for line in groovy.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        assert "--export-jira" not in stripped


def test_jenkins_template_points_at_the_mcp_tool_instead_of_dropping_the_option():
    groovy = (
        _REPO_ROOT / "ci" / "jenkins" / "vars" / "cherenkovValidate.groovy"
    ).read_text(encoding="utf-8")
    assert "exportJira" in groovy
    assert "export_jira_ticket" in groovy


def test_jenkins_template_separates_usage_error_from_conformance_failure():
    groovy = (
        _REPO_ROOT / "ci" / "jenkins" / "vars" / "cherenkovValidate.groovy"
    ).read_text(encoding="utf-8")
    assert "returnStatus: true" in groovy
    assert "== 2" in groovy


def test_guard_passes_on_the_real_tree(guard):
    """End to end on the shipped CI templates, with no fixtures involved."""
    assert guard.main() == 0
