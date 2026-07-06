#!/usr/bin/env python3
"""
ci_docs_check.py -- programmatically validates that all argparse subcommands have corresponding documentation sections.
"""

from __future__ import annotations

import importlib.util
import os
import sys

# Make the checker self-sufficient regardless of invocation cwd: ensure the
# repo root (parent of scripts/) is importable so `cherenkov.*` resolves even
# when run as `python3 scripts/ci_docs_check.py` without PYTHONPATH set.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def load_cherenkov_cli():
    """Load cherenkov.py as a module directly (not the cherenkov/ package)."""
    cli_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "cherenkov.py")
    )
    spec = importlib.util.spec_from_file_location("cherenkov_cli", cli_path)
    mod = importlib.util.module_from_spec(spec)
    # Prevent execution of main() during import
    sys.modules["cherenkov_cli"] = mod
    spec.loader.exec_module(mod)
    return mod


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

    with open(docs_file, "r", encoding="utf-8") as f:
        docs_content = f.read()

    # Dynamically load cherenkov.py (not the cherenkov/ package)
    import argparse

    cli_mod = load_cherenkov_cli()
    parser = cli_mod.get_parser()

    # Programmatically get all configured subcommands from the argparse parser
    subcommands = []
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for choice in action.choices.keys():
                subcommands.append(choice)

    print(f"Detected subcommands from argparse: {subcommands}")

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
