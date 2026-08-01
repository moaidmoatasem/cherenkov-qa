#!/usr/bin/env python3
"""
ci_docs_check.py -- programmatically validates that all CLI subcommands have corresponding documentation sections.
"""

from __future__ import annotations

import os
import sys

# Make the checker self-sufficient regardless of invocation cwd: ensure the
# repo root (parent of scripts/) is importable so `cherenkov.*` resolves even
# when run as `python3 scripts/ci_docs_check.py` without PYTHONPATH set.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def load_cherenkov_cli_commands():
    """Collect top-level command names from the canonical Click CLI."""
    from cherenkov.cli.core import _register_commands, cli

    _register_commands()
    return sorted(cli.commands.keys())


def main():
    print("=======================================================")
    print("     CHERENKOV CI DOCUMENTATION DRIFT CHECKER")
    print("=======================================================\n")

    docs_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../docs/GETTING_STARTED.md")
    )
    if not os.path.exists(docs_file):
        print(f"[FAIL] Error: GETTING_STARTED.md is missing at: {docs_file}")
        sys.exit(1)

    with open(docs_file, encoding="utf-8") as f:
        docs_content = f.read()

    # Collect command names from the canonical CLI entry point
    subcommands = load_cherenkov_cli_commands()

    print(f"Detected subcommands from Click CLI: {subcommands}")

    # Assert every subcommand is explicitly documented in the GETTING_STARTED.md
    missing_docs = []
    for cmd in subcommands:
        # Check if the command name appears in a backtick-quoted context inside the docs
        if f"`{cmd}`" not in docs_content:
            missing_docs.append(cmd)

    if missing_docs:
        print(
            f"\n[FAIL] Error: Documentation drift detected! Undocumented subcommands found: {missing_docs}"
        )
        print("Please add documentation sections in docs/GETTING_STARTED.md.")
        sys.exit(1)

    print(
        "\n[PASS] SUCCESS: All CLI subcommands are programmatically fully documented inside docs/GETTING_STARTED.md!"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
