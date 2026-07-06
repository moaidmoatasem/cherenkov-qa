#!/usr/bin/env python3
"""
ci_docs_check.py -- validates that all Click CLI subcommands have corresponding
documentation sections in docs/GETTING_STARTED.md.
"""

from __future__ import annotations

import argparse
import os
import sys

# Make the checker self-sufficient regardless of invocation cwd.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def get_click_subcommands() -> list[str]:
    """Return the sorted list of registered Click CLI subcommand names."""
    from cherenkov.cli.core import _register_commands, cli
    _register_commands()
    return sorted(cli.commands.keys())


def main():
    parser = argparse.ArgumentParser(description="CI docs drift checker")
    parser.add_argument(
        "--docs-file",
        default=None,
        help="Path to the docs file to check (default: docs/GETTING_STARTED.md)",
    )
    args = parser.parse_args()

    print("=======================================================")
    print("     CHERENKOV CI DOCUMENTATION DRIFT CHECKER")
    print("=======================================================\n")

    if args.docs_file:
        docs_file = os.path.abspath(args.docs_file)
    else:
        docs_file = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../docs/GETTING_STARTED.md")
        )

    if not os.path.exists(docs_file):
        print(f"[FAIL] Error: docs file is missing at: {docs_file}")
        sys.exit(1)

    with open(docs_file, "r", encoding="utf-8") as f:
        docs_content = f.read()

    subcommands = get_click_subcommands()
    print(f"Detected subcommands from Click CLI: {subcommands}")

    # Assert every subcommand is explicitly documented
    missing_docs = []
    for cmd in subcommands:
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
