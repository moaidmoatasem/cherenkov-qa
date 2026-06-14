#!/usr/bin/env python3
"""
check_cli_docs.py -- CLI-docs parity checker.

Extracts all subcommands from cherenkov.py's argparse parser and cross-references
them against GETTING_STARTED.md.

Checks:
  1. Every top-level CLI command is documented in GETTING_STARTED.md
  2. Every documented top-level command exists in the CLI parser
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


def _load_cli_commands():
    # Ensure repo root is on sys.path so cherenkov package is resolvable
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    spec = importlib.util.spec_from_file_location("cherenkov_cli", _CLI_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cherenkov_cli"] = mod
    spec.loader.exec_module(mod)
    parser = mod.get_parser()
    commands = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                subs = []
                for sa in subparser._actions:
                    if isinstance(sa, argparse._SubParsersAction):
                        subs.extend(sa.choices.keys())
                commands[name] = subs
    return commands


_DOC_CMD_RE = re.compile(
    r"^#{4,5}\s+`([a-z][\w-]*(?:\s+[a-z][\w-]*)?)(?:\s+<[^>]+>)?`\s*(?:\(([^)]*)\))?",
    re.MULTILINE,
)

# Headings whose backtick content is NOT a CLI command (e.g. error code tables)
_IGNORED_HEADINGS = frozenset({"hitl/v1"})


def _parse_doc_headings(content):
    out = {}
    for m in _DOC_CMD_RE.finditer(content):
        raw = m.group(1).strip()
        if raw in _IGNORED_HEADINGS:
            continue
        out[raw] = (m.group(2) or "").strip()
    return out


def _cmd_section(content, cmd):
    current = None
    for line in content.splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
        elif re.match(r"^#{4,5}\s+`" + re.escape(cmd) + r"`", line):
            return current
    return None


def main():
    errors = []
    try:
        cli = _load_cli_commands()
    except Exception as exc:
        print(f"[FAIL] Could not load CLI parser: {exc}")
        return 1
    if not os.path.isfile(_DOCS_PATH):
        print(f"[FAIL] {_DOCS_PATH} not found")
        return 1
    content = open(_DOCS_PATH, encoding="utf-8").read()
    doc_headings = _parse_doc_headings(content)
    doc_top = set()
    doc_cmd_tags = {}
    for raw, tag in doc_headings.items():
        parts = raw.split()
        doc_top.add(parts[0])
        doc_cmd_tags[parts[0]] = tag
        if len(parts) > 1:
            doc_top.add(raw)
    print("--- CLI -> docs ---")
    for cmd in sorted(cli):
        if cmd in doc_top:
            print(f"  OK  [{cmd}] documented")
        else:
            errors.append(f"[{cmd}] is not documented in GETTING_STARTED.md")
    print()
    print("--- Docs -> CLI ---")
    for cmd in sorted(doc_top):
        if " " in cmd:
            parent, sub = cmd.split(" ", 1)
            if parent not in cli or sub not in cli.get(parent, []):
                errors.append(f"[{cmd}] documented but not found in CLI parser")
            else:
                print(f"  OK  [{cmd}] exists in CLI")
        elif cmd not in cli:
            errors.append(f"[{cmd}] documented but not found in CLI parser")
        else:
            print(f"  OK  [{cmd}] exists in CLI")
    print()
    print("--- Horizon 2 tags ---")
    for cmd in sorted(doc_top):
        raw = cmd.split()[0]
        section = _cmd_section(content, raw)
        tag = doc_cmd_tags.get(raw, "")
        if section == _HORIZON_2 and not tag:
            errors.append(f"[{cmd}] under {_HORIZON_2} but has no epoch/track tag")
    print()
    print("==================================================")
    if errors:
        print(f"[FAIL] {len(errors)} issue(s):")
        for e in errors:
            print(f"  * {e}")
        return 1
    print("[PASS] CLI-docs parity confirmed, Horizon 2 tags correct.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
