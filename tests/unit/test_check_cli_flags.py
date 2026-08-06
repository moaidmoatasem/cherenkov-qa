"""tests/unit/test_check_cli_flags.py — CLI-flag docs parity checker.

Verifies scripts/check_cli_flags.py:
- `_iter_doc_flags` parses `--flag` tokens from a `**Flags:**` table, including
  tokens that carry a value or alternate placeholder inside the backticks.
- `_real_flags_by_command` flattens the Click CLI into {command: {long flags}},
  rolling subcommand flags up into their group key, and includes secondary
  options (so `--no-repair` beside `--repair` counts as existing).
- The committed docs-site CLI reference has no documented flag that is missing
  from the real CLI (the gate the CI job enforces stays green).

D7 invariant: this test only *checks* docs-vs-CLI agreement; it never edits docs.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from cherenkov.cli.core import _register_commands, cli

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_PATH = REPO_ROOT / "scripts" / "check_cli_flags.py"

_spec = importlib.util.spec_from_file_location("check_cli_flags", _SCRIPTS_PATH)
check_flags = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(check_flags)


def test_iter_doc_flags_extracts_flags_with_value_placeholders():
    content = """# t

### `validate`

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--spec FILE` | Yes | spec |
| `--format [json|text]` | No | format |
| `--max-probes N` | No | probes |
| `--json` | No | json |

### `other`
"""
    by_cmd = dict(check_flags._iter_doc_flags(content))
    assert "--spec" in by_cmd["validate"]
    assert "--format" in by_cmd["validate"]  # value placeholder inside backticks
    assert "--max-probes" in by_cmd["validate"]
    assert "--json" in by_cmd["validate"]


def test_real_flags_includes_secondary_opts_and_rolls_up():
    _register_commands()
    real = check_flags._real_flags_by_command(cli)
    # generate documents --repair/--no-repair; --no-repair is a secondary opt.
    assert "--no-repair" in real["generate"]
    # A group's bare key is the union of its subcommand flags.
    guardian = real.get("guardian", set())
    assert guardian  # must have at least the subcommand flags rolled up
    assert "--spec" in guardian or "--base-url" in guardian


def test_secondary_opts_are_treated_as_existing():
    _register_commands()
    # The reference documents `--repair` / `--no-repair` for generate.
    real = check_flags._real_flags_by_command(cli)
    assert "--repair" in real["generate"]
    assert "--no-repair" in real["generate"]


def test_committed_reference_gate_is_green():
    """The whole point: `python scripts/check_cli_flags.py` returns 0."""
    reference = REPO_ROOT / "docs-site" / "docs" / "cli" / "reference.md"
    content = reference.read_text(encoding="utf-8")
    _register_commands()
    real = check_flags._real_flags_by_command(cli)
    for command, flags in check_flags._iter_doc_flags(content):
        if not flags:
            continue
        if "<" in command:
            continue
        real_opts = real.get(command, set())
        assert command in real, f"{command} documented but not in CLI"
        assert real_opts, f"{command} has no real flags but documents {flags}"
        for flag in flags:
            assert flag in real_opts, (
                f"[{command}] documented `{flag}` is not a real CLI option "
                f"(has: {sorted(real_opts)})"
            )
