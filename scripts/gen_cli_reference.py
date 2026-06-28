#!/usr/bin/env python3
"""
gen_cli_reference.py
────────────────────
Generates docs-site/docs/cli/_generated_reference.md from `cherenkov --help`.

This script auto-generates the authoritative CLI reference from the live CLI,
eliminating the "manual CLI doc → spec drift" parity trap.

Run:
    python scripts/gen_cli_reference.py

The generated file is then included in docs-site/docs/cli/reference.md via:
    --8<-- "cli/_generated_reference.md"

CI:
    This script runs in the docs-lint job before mkdocs build.
    The generated file is committed to the branch if changed (or diff-checked).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import indent

OUTPUT_PATH = Path(__file__).parent.parent / "docs-site" / "docs" / "cli" / "_generated_reference.md"

# Top-level command and all subcommands to document
COMMANDS: list[list[str]] = [
    ["cherenkov"],
    ["cherenkov", "validate"],
    ["cherenkov", "generate"],
    ["cherenkov", "eject"],
    ["cherenkov", "dashboard"],
    ["cherenkov", "hitl"],
    ["cherenkov", "hitl", "list"],
    ["cherenkov", "hitl", "approve"],
    ["cherenkov", "hitl", "reject"],
    ["cherenkov", "knowledge"],
    ["cherenkov", "knowledge", "query"],
    ["cherenkov", "knowledge", "list"],
    ["cherenkov", "knowledge", "add"],
    ["cherenkov", "memory"],
    ["cherenkov", "memory", "status"],
    ["cherenkov", "memory", "list"],
    ["cherenkov", "memory", "search"],
    ["cherenkov", "memory", "promote"],
    ["cherenkov", "routine"],
    ["cherenkov", "teleport"],
    ["cherenkov", "doctor"],
    ["cherenkov", "examples"],
]


def run_help(cmd: list[str]) -> str:
    """Run `cmd --help` and return the stdout."""
    try:
        result = subprocess.run(
            cmd + ["--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return (result.stdout or result.stderr).strip()
    except FileNotFoundError:
        return f"(cherenkov not installed — install with: pip install cherenkov-qa)"
    except subprocess.TimeoutExpired:
        return "(timed out)"


def cmd_to_heading(cmd: list[str]) -> str:
    """cherenkov validate --help → ### `cherenkov validate`"""
    level = "#" * min(len(cmd) + 2, 6)
    return f"{level} `{' '.join(cmd)}`"


def generate() -> str:
    lines: list[str] = [
        "<!-- AUTO-GENERATED — DO NOT EDIT -->",
        "<!-- Source: scripts/gen_cli_reference.py -->",
        "<!-- Re-generate: python scripts/gen_cli_reference.py -->",
        "",
        "> [!NOTE]",
        "> This section is auto-generated from `cherenkov --help`. "
        "Last generated: see git log on this file.",
        "",
    ]

    for cmd in COMMANDS:
        help_text = run_help(cmd)
        lines.append(cmd_to_heading(cmd))
        lines.append("")
        lines.append("```")
        lines.append(help_text)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    print(f"Generating CLI reference → {OUTPUT_PATH.relative_to(Path.cwd())}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    content = generate()
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"✅ Written {len(content)} bytes to {OUTPUT_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
