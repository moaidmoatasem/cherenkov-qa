#!/usr/bin/env python3
"""
check_cli_docs.py -- CLI-docs parity checker.

Extracts all subcommands from cherenkov.py's argparse parser and cross-references
them against GETTING_STARTED.md.

Checks:
  1. Every CLI command is documented in GETTING_STARTED.md
  2. Every documented command exists in the CLI parser
  3. Commands under "Horizon 2 / Experimental" carry an epoch/track tag

Exit 0 = full parity, 1 = mismatch found.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CLI_PATH = os.path.join(_REPO_ROOT, "cherenkov.py")
_DOCS_PATH = os.path.join(_REPO_ROOT, "docs", "GETTING_STARTED.md")
_HORIZON_2 = "Horizon 2 / Experimental"


def _load_cli_commands() -> dict[str, list[str]]:
    """Load cherenkov.py and extract all subcommand names from argparse."""
    spec = importlib.util.spec_from_file_location("cherenkov_cli", _CLI_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cherenkov_cli"] = mod
    spec.loader.exec_module(mod)

    parser = mod.get_parser()
    commands: dict[str, list[str]] = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                subs: list[str] = []
                for sa in subparser._actions:
                    if isinstance(sa, argparse._SubParsersAction):
                        subs.extend(sa.choices.keys())
                commands[name] = subs
    return commands


def _parse_doc_headings(content: str) -> dict[str, str]:
    """Return {cmd_name: heading_tag} for all #### and ##### backtick sections."""
    out: dict[str, str] = {}
    for m in re.finditer(r"^#{4,5}\s+`([^`]+)`\s*(\([^)]*\))?", content, re.MULTILINE):
        out[m.group(1).strip()] = (m.group(2) or "").strip()
    return out


def _cmd_section(content: str, cmd: str) -> str | None:
    """Return the ### section heading under which *cmd* is documented."""
    current = None
    for line in content.splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
        elif re.match(rf"^#{4,5}\s+`{re.escape(cmd)}`", line):
            return current
    return None


def main() -> int:
    errors: list[str] = []

    # 1. Load CLI commands (importlib, not regex)
    try:
        cli = _load_cli_commands()
    except Exception as exc:
        print(f"[FAIL] Could not load CLI parser: {exc}")
        return 1

    # 2. Load docs headings (#### and #####)
    if not os.path.isfile(_DOCS_PATH):
        print(f"[FAIL] {_DOCS_PATH} not found")
        return 1
    content = open(_DOCS_PATH, encoding="utf-8").read()
    doc_headings = _parse_doc_headings(content)

    # Build a flat set of all doc-documented commands (top-level + subcommands)
    # Also handle space-separated doc commands like "mcp serve"
    doc_cmds_flat: set[str] = set()
    doc_cmd_to_tag: dict[str, str] = {}
    for raw, tag in doc_headings.items():
        parts = raw.split()
        doc_cmds_flat.add(parts[0])
        doc_cmd_to_tag[parts[0]] = tag
        # If space-separated (e.g. "mcp serve"), register the subcmd too
        if len(parts) > 1:
            doc_cmds_flat.add(raw)

    # 3. CLI -> docs
    print("--- CLI -> docs ---")
    for cmd in sorted(cli):
        if cmd not in doc_cmds_flat:
            errors.append(f"[{cmd}] is not documented in GETTING_STARTED.md")
        else:
            print(f"  OK  [{cmd}] documented")
        for sub in cli[cmd]:
            full = f"{cmd} {sub}"
            if full not in doc_cmds_flat and sub not in doc_cmds_flat:
                errors.append(f"[{full}] subcommand is not documented in GETTING_STARTED.md")

    # 4. Docs -> CLI
    print("\n--- Docs -> CLI ---")
    all_cli = set(cli.keys())
    for cmd in sorted(doc_cmds_flat):
        if " " in cmd:
            parent, sub = cmd.split(" ", 1)
            if parent not in all_cli or sub not in cli.get(parent, []):
                errors.append(f"[{cmd}] documented but not found in CLI parser")
            else:
                print(f"  OK  [{cmd}] exists in CLI")
        elif cmd not in all_cli:
            errors.append(f"[{cmd}] documented but not found in CLI parser")
        else:
            print(f"  OK  [{cmd}] exists in CLI")

    # 5. Horizon 2 tags
    print("\n--- Horizon 2 tags ---")
    for cmd in sorted(doc_cmds_flat):
        section = _cmd_section(content, cmd)
        tag = doc_cmd_to_tag.get(cmd, "")
        if section == _HORIZON_2 and not tag:
            # Check if parent command has tag
            parent = cmd.split()[0] if " " in cmd else cmd
            parent_tag = doc_cmd_to_tag.get(parent, "")
            if not parent_tag:
                errors.append(f"[{cmd}] under {_HORIZON_2} but has no epoch/track tag")

    # 6. Result
    print(f"\n{'=' * 50}")
    if errors:
        print(f"[FAIL] {len(errors)} issue(s):")
        for e in errors:
            print(f"  * {e}")
        return 1
    print("[PASS] CLI-docs parity confirmed, Horizon 2 tags correct.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
