"""tests/unit/test_verify_onboarding_transcripts.py — onboarding transcript parity.

Verifies scripts/verify_onboarding_transcripts.py:
- `_iter_bash_blocks` extracts only fenced bash/sh blocks from a session doc.
- `_strip_shell` drops the `$ ` prompt prefix and inline trailing comments.
- `_command_exists` / `_flags_for` resolve a command path against the flattened
  Click CLI (including subcommand paths rolled up to their group).
- `_validate_session` flags a nonexistent command and a nonexistent flag, and
  stays silent for external shell lines (git, npm, docker-compose).
- The committed session docs pass the gate the CI job enforces.

D7 invariant: this test only *checks* docs-vs-CLI agreement; it never edits docs.
"""
from __future__ import annotations

import importlib.util
import os
import textwrap
from pathlib import Path

from cherenkov.cli.core import _register_commands, cli

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_PATH = REPO_ROOT / "scripts" / "verify_onboarding_transcripts.py"

_spec = importlib.util.spec_from_file_location("verify_onboarding_transcripts", _SCRIPTS_PATH)
verify_x = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(verify_x)


def _write_tmp_session(tmp_path: Path, body: str) -> str:
    p = tmp_path / "session_a_zero_to_hero.md"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return str(p)


def test_iter_bash_blocks_only_yields_bash_fences(tmp_path: Path):
    path = _write_tmp_session(
        tmp_path,
        """\
        # S

        ```bash
        ./bin/cherenkov init
        ```

        ```text
        ./bin/cherenkov not-a-bash-block
        ```

        ```sh
        ./bin/cherenkov doctor
        ```
        """,
    )
    blocks = list(verify_x._iter_bash_blocks(path))
    assert len(blocks) == 2
    assert blocks[0][0] == 3  # start line of the first ```bash block
    assert blocks[0][1] == ["./bin/cherenkov init"]
    assert blocks[1][1] == ["./bin/cherenkov doctor"]


def test_strip_shell_removes_prompt_and_comment():
    assert verify_x._strip_shell("$ ./bin/cherenkov init") == "./bin/cherenkov init"
    assert verify_x._strip_shell("./bin/cherenkov doctor  # verify setup") == "./bin/cherenkov doctor"
    # A `#` inside quotes is not a comment.
    assert verify_x._strip_shell("cherenkov validate --tests 'happy_path' # run") == (
        "cherenkov validate --tests 'happy_path'"
    )


def test_command_exists_resolves_groups_and_subcommands():
    _register_commands()
    real = verify_x._real_flags_by_command(cli)
    # Bare top-level command and a real subcommand path both resolve.
    assert verify_x._command_exists(real, "validate")
    assert verify_x._command_exists(real, "hitl")
    assert verify_x._command_exists(real, "hitl list")
    # A nonexistent command does not.
    assert not verify_x._command_exists(real, "nonexistent-command")


def test_flags_for_includes_rolled_up_subcommand_flags():
    _register_commands()
    real = verify_x._real_flags_by_command(cli)
    opts = verify_x._flags_for(real, "hitl")
    # subcommand flags roll up to the group, so the group's bare key is nonempty
    assert opts


def test_validate_session_catches_bad_command_and_flag(tmp_path: Path):
    _register_commands()
    real = verify_x._real_flags_by_command(cli)
    path = _write_tmp_session(
        tmp_path,
        """\
        # S

        ```bash
        ./bin/cherenkov init
        ./bin/cherenkov nonexistent-command
        ./bin/cherenkov validate --totally-bogus-flag
        git clone https://github.com/example/repo.git
        ```
        """,
    )
    errors = verify_x._validate_session(path, real)
    # The nonexistent command and the bogus flag are both caught; the external
    # git line is not a cherenkov invocation so it is ignored.
    assert any("nonexistent-command" in e for e in errors)
    assert any("--totally-bogus-flag" in e for e in errors)
    assert not any("git clone" in e for e in errors)


def test_committed_session_docs_gate_is_green():
    """The whole point: `python3 scripts/verify_onboarding_transcripts.py` returns 0."""
    sessions = REPO_ROOT / "docs" / "onboarding" / "sessions"
    assert sessions.is_dir()
    _register_commands()
    real = verify_x._real_flags_by_command(cli)
    errors: list[str] = []
    for md in sorted(sessions.glob("session_*.md")):
        errors.extend(verify_x._validate_session(str(md), real))
    assert errors == [], f"onboarding transcript drift:\n" + "\n".join(errors)
