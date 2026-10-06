"""Core / Assist / Labs: the root `--help` advertises the integrity gate, nothing else."""
from __future__ import annotations

from click.testing import CliRunner

from cherenkov.cli import tiers
from cherenkov.cli.core import _register_commands, cli


def _root():
    _register_commands()
    return cli


def test_core_set_is_pinned():
    # Promoting a command to Core is a product decision: change this on purpose.
    assert tiers.CORE == ("check", "demo", "init", "doctor", "validate", "verify")


def test_every_core_and_assist_command_exists():
    names = set(_root().commands)
    assert set(tiers.CORE) <= names
    assert set(tiers.ASSIST) <= names
    assert "labs" in names


def test_help_lists_core_and_assist_but_not_labs():
    out = CliRunner().invoke(_root(), ["--help"]).output
    assert "Core commands:" in out and "Assist commands:" in out
    for name in tiers.CORE:
        assert f"  {name} " in out
    for name in ("federation", "enterprise", "teleport", "train", "brain"):
        assert f"  {name} " not in out, f"{name} is Labs and must not be advertised"
    assert "cherenkov labs" in out


def test_labs_lists_experimental_commands_and_they_still_run():
    runner = CliRunner()
    listing = runner.invoke(_root(), ["labs"]).output
    assert "federation" in listing and "check-stale" in listing
    assert "check " not in listing  # Core is not Labs
    assert runner.invoke(_root(), ["federation", "--help"]).exit_code == 0


def test_labs_names_excludes_core_assist_and_meta():
    labs = set(tiers.labs_names(_root()))
    assert not labs & (set(tiers.CORE) | set(tiers.ASSIST) | set(tiers.META))
