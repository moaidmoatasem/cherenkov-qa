#!/usr/bin/env python3
"""
check_cli_flags.py -- CLI-flag docs parity checker.

Extends check_cli_docs.py (which only cross-references top-level *command
names*) to also verify that every *flag* documented for a command in the CLI
reference actually exists on the real Click command.

Checks, per command section in docs-site/docs/cli/reference.md:

  1. Every `--flag` named in a "**Flags:**" table resolves to that command's
     real Click options (opts | secondary_opts, so `--no-repair` beside
     `--repair` counts as existing).
  2. For a group command whose section table describes a subcommand (e.g.
     `guardian` documents `start`'s flags), documented flags are matched
     against the union of all of that command's flags, since the reference
     tables may describe either the command or one of its subcommands.

Exit 0 = every documented flag exists, 1 = flag drift found.
"""

from __future__ import annotations

import os
import re
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REFERENCE_PATH = os.path.join(_REPO_ROOT, "docs-site", "docs", "cli", "reference.md")

# Click exposes --help on every command; the reference repeats it as a global
# option. It is not part of any per-command param list, so ignore it here.
_HELP_FLAGS = {"--help"}


def _real_flags_by_command(cli) -> dict[str, set[str]]:
    """Flatten the Click CLI into {command_ref: {long flag options}}.

    command_ref mirrors the documented spelling (`certify`, `guardian`,
    `hitl list`, `mcp publish`). Per-subcommand keys exist, and each group's
    bare key is the union of every descendant's flags (a section table may
    describe the group or a specific subcommand).

    Args:
        cli: Root Click CLI Group object.

    Returns:
        dict[str, set[str]]: Mapping from command paths to sets of supported option flags.
    """
    out: dict[str, set[str]] = {}

    def visit(cmd, prefix: str) -> None:
        """Recursively collect long CLI flag options for a command and its subcommands.

        Args:
            cmd: Click Command or Group object.
            prefix: Current command path prefix string.
        """
        if prefix:
            opts = set()
            for p in getattr(cmd, "params", []):
                for o in (*getattr(p, "opts", []), *getattr(p, "secondary_opts", [])):
                    if o.startswith("--"):
                        opts.add(o)
            out.setdefault(prefix, set()).update(opts)
        if hasattr(cmd, "commands"):
            for name, sub in cmd.commands.items():
                visit(sub, (prefix + " " + name).strip())

    visit(cli, "")

    # Roll each subcommand's flags up into its parent group key, so a bare
    # `guardian` table that really documents `guardian start` still validates.
    for key, flags in list(out.items()):
        if " " in key:
            parent = key.split(" ", 1)[0]
            out.setdefault(parent, set()).update(flags)
    return out


_CMD_RE = re.compile(r"^###\s+`([a-z][\w-]*(?:\s+[a-z][\w-]*)?)`\s*$")


def _iter_doc_flags(content: str):
    """Yield (command_ref, [long flags documented in its Flags: table]).

    Args:
        content: Markdown documentation string.

    Yields:
        tuple[str, list[str]]: Command reference and list of documented CLI option flags.
    """
    current = None
    in_flags = False
    pending: list[str] = []
    for line in content.splitlines():
        m = _CMD_RE.match(line)
        if m:
            if current and pending:
                yield current, pending
            current = m.group(1).strip()
            in_flags = False
            pending = []
            continue
        if current is None:
            continue
        if line.strip() == "**Flags:**":
            in_flags = True
            continue
        if in_flags and line.startswith("|"):
            for token in re.findall(r"(?<![\w-])--[a-z][\w-]*", line):
                if token not in _HELP_FLAGS:
                    pending.append(token)
        elif in_flags and re.match(r"^\s*(#{3,6}\s|\w+ \*\*|```)", line):
            in_flags = False
    if current:
        yield current, pending


def main() -> int:
    """Verify that all documented CLI flags in the documentation exist in Click command definitions.

    Returns:
        int: 0 if all flags match without drift, 1 if missing or invalid flags detected.
    """
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    try:
        from cherenkov.cli.core import _register_commands, cli
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[FAIL] Could not load CLI parser: {exc}")
        return 1
    try:
        _register_commands()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[FAIL] Could not register CLI commands: {exc}")
        return 1
    if not os.path.isfile(_REFERENCE_PATH):
        print(f"[FAIL] {_REFERENCE_PATH} not found")
        return 1
    with open(_REFERENCE_PATH, encoding="utf-8") as f:
        content = f.read()

    real = _real_flags_by_command(cli)
    errors = []
    checked = 0
    
    # 1. Check reference.md Flags tables
    for command, flags in _iter_doc_flags(content):
        if not flags:
            continue
        if "<" in command:  # e.g. a table heading that isn't a CLI ref
            continue
        real_opts = real.get(command, set())
        if command not in real:
            errors.append(
                f"[{command}] documents flags {sorted(flags)} but has no such "
                "command/flags in the CLI parser (documented as a command)."
            )
            continue
        for flag in flags:
            checked += 1
            if flag not in real_opts:
                errors.append(
                    f"[{command}] documented flag `{flag}` does not exist in CLI "
                    f"(has: {sorted(real_opts) if real_opts else 'none'})"
                )

    # 2. Check all other .md files for inline `cherenkov <cmd> --flag` uses
    import glob
    # Archived/planning/vision docs are point-in-time records: they may cite
    # commands or flags that never shipped or were later renamed. Excluding
    # them keeps the gate scoped to docs that read as current, runnable
    # instructions.
    _EXCLUDED_DIRS = ("_archive", "vision", "plans")
    _md_files = (
        glob.glob(os.path.join(_REPO_ROOT, "docs", "**", "*.md"), recursive=True)
        + glob.glob(os.path.join(_REPO_ROOT, "skills", "**", "*.md"), recursive=True)
    )
    md_files = [
        f
        for f in _md_files
        if not any(
            os.sep + d + os.sep in os.path.relpath(f, _REPO_ROOT) for d in _EXCLUDED_DIRS
        )
    ]

    inline_re = re.compile(r"(?:python\s+cherenkov\.py|cherenkov|\./bin/cherenkov)\s+([a-z][\w-]*(?:\s+[a-z][\w-]*)?)\s+.*?(--[a-z][\w-]+)")
    for md_file in md_files:
        with open(md_file, encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                for match in inline_re.finditer(line):
                    command, flag = match.groups()
                    if flag in _HELP_FLAGS:
                        continue
                    real_opts = real.get(command, set())
                    if command not in real:
                        errors.append(
                            f"{os.path.relpath(md_file, _REPO_ROOT)}:{line_no} uses command '{command}' which doesn't exist."
                        )
                    elif flag not in real_opts:
                        errors.append(
                            f"{os.path.relpath(md_file, _REPO_ROOT)}:{line_no} uses flag '{flag}' on command '{command}' but it doesn't exist "
                            f"(has: {sorted(real_opts) if real_opts else 'none'})"
                        )
                        checked += 1
    print(f"Checked {checked} documented flags across the CLI reference.")
    if errors:
        print(f"\n[FAIL] {len(errors)} flag drift issue(s):")
        for e in errors:
            print(f"  * {e}")
        print(f"\nFix the markdown files so every documented flag is a real Click option.")
        return 1
    print("[PASS] every documented CLI flag exists on the real Click command.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
