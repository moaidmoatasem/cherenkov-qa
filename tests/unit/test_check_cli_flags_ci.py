"""Tests for the CI-template arm of scripts/check_cli_flags.py.

The guard previously scanned only `docs/` and `skills/`, so every file under
`ci/` was unchecked — which is how `ci/jenkins/vars/cherenkovValidate.groovy`
came to pass `--export-jira`, an option that exists on no CHERENKOV command.

CI files build commands in three different shapes, and a line-oriented regex
only catches the first. These tests pin all three, so the gate cannot quietly
stop covering the shape that actually hid the bug.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "check_cli_flags.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_cli_flags", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def guard():
    return _load()


# ── Invocation shapes ────────────────────────────────────────────────────────


def test_detects_flags_on_a_single_line_invocation(guard):
    text = "  - cherenkov validate --target $URL --spec $SPEC --fail-on-drift --quiet\n"
    found = list(guard._iter_ci_flag_uses(text))
    assert {(c, f) for _, c, f in found} == {
        ("validate", "--target"),
        ("validate", "--spec"),
        ("validate", "--fail-on-drift"),
        ("validate", "--quiet"),
    }


def test_detects_flags_across_a_shell_continuation(guard):
    """action.yml style: the command is on one line, flags trail after a `\\`."""
    text = (
        "        cherenkov validate \\\n"
        '          --spec "x" \\\n'
        '          --target "y" \\\n'
        '          --json-summary /tmp/s.json\n'
    )
    found = [(c, f) for _, c, f in guard._iter_ci_flag_uses(text)]
    assert ("validate", "--json-summary") in found
    assert ("validate", "--target") in found


def test_detects_flags_appended_to_a_command_variable(guard):
    """Jenkins style: `cmd += " --export-jira"` on its own line.

    This is the shape that hid the original bug — the flag never appears on the
    same line as the command.
    """
    text = (
        'def cmd = "cherenkov validate --target ${t} --quiet"\n'
        "if (failOnDrift) {\n"
        '    cmd += " --fail-on-drift"\n'
        "}\n"
        '    cmd += " --export-jira"\n'
    )
    found = [(c, f) for _, c, f in guard._iter_ci_flag_uses(text)]
    assert ("validate", "--export-jira") in found
    assert ("validate", "--fail-on-drift") in found


def test_continuation_does_not_leak_into_unrelated_later_commands(guard):
    """A line without a trailing backslash ends the invocation."""
    text = "cherenkov validate --target x\npip install something --user\n"
    found = [(c, f) for _, c, f in guard._iter_ci_flag_uses(text)]
    assert ("validate", "--user") not in found


def test_package_name_is_not_mistaken_for_a_command(guard):
    """`pip install cherenkov-qa` must not register `qa` as a command."""
    text = "  - pip install cherenkov-qa --quiet\n"
    assert list(guard._iter_ci_flag_uses(text)) == []


def test_path_ending_in_cherenkov_is_not_an_invocation(guard):
    text = "  - mkdir -p test-results/cherenkov\n"
    assert list(guard._iter_ci_flag_uses(text)) == []


# ── File discovery ───────────────────────────────────────────────────────────


def test_ci_files_include_templates_and_action(guard):
    files = {
        os.path.relpath(f, _REPO_ROOT).replace(os.sep, "/")
        for f in guard._ci_files(str(_REPO_ROOT))
    }
    assert "action.yml" in files
    assert "ci/gitlab-ci-template.yml" in files
    assert "ci/circleci/orb.yml" in files
    assert "ci/jenkins/vars/cherenkovValidate.groovy" in files


# ── The regression this closes ───────────────────────────────────────────────


def test_jenkins_template_no_longer_passes_a_nonexistent_flag(guard):
    """`--export-jira` may appear in the explanatory comment, never in the command.

    Asserted through the guard's own parser rather than by grepping the text, so
    the check reflects what actually reaches the CLI.
    """
    groovy = (
        _REPO_ROOT / "ci" / "jenkins" / "vars" / "cherenkovValidate.groovy"
    ).read_text(encoding="utf-8")
    flags = {flag for _, _, flag in guard._iter_ci_flag_uses(groovy)}
    assert "--export-jira" not in flags
    assert "--fail-on-drift" in flags  # parser still sees the real appended flag


def test_jenkins_template_fails_loudly_on_export_jira():
    """Setting exportJira must error with a pointer, not be silently dropped."""
    groovy = (
        _REPO_ROOT / "ci" / "jenkins" / "vars" / "cherenkovValidate.groovy"
    ).read_text(encoding="utf-8")
    assert "config.exportJira" in groovy
    assert "export_jira_ticket" in groovy


def test_jenkins_template_separates_usage_error_from_conformance_failure():
    groovy = (
        _REPO_ROOT / "ci" / "jenkins" / "vars" / "cherenkovValidate.groovy"
    ).read_text(encoding="utf-8")
    assert "returnStatus: true" in groovy
    assert "status == 2" in groovy


def test_guard_passes_on_the_current_tree(guard):
    """End-to-end: the shipped CI templates must all validate."""
    assert guard.main() == 0
