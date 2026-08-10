#!/usr/bin/env python3
"""
verify_onboarding_transcripts.py — cold-run verification for onboarding sessions.

The three onboarding session docs (docs/onboarding/sessions/*.md) are a scripted
walk-through: each "```bash```" fenced block is a real terminal session a viewer
(or an agent reproducing the video) is expected to run. This harness extracts
every fenced bash/sh block, resolves each `cherenkov` invocation against the live
Click CLI, and fails if a command/subcommand/flag in a session does not exist.

Scope — what is verified:
  * `cherenkov`, `./bin/cherenkov`, `python cherenkov.py`, `python3 cherenkov.py`
    invocations: the top-level command and (for a subcommand) the full path must
    exist, and every `--flag` on the line must be a real Click option of that
    command.
  * Non-CHERENKOV shell lines (git, npm, docker-compose, cd, ...) are expected
    external tooling and are reported, not validated.

Scope — what is deliberately NOT run:
  * The script never executes the blocks (offline mode: no network, no docker,
    no LLM). It is a static parity gate, mirroring check_cli_flags.py but for
    the onboarding transcripts specifically.

Exit 0 = every cherenkov command/subcommand/flag in the transcripts is real,
1 = drift found.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SESSIONS_DIR = os.path.join(_REPO_ROOT, "docs", "onboarding", "sessions")

_HELP_FLAGS = {"--help"}

# A cherenkov invocation inside a bash block. Group 1 = command path, Group 2
# = trailing token (flag) if the line has no subcommand token.
_INVOKE_RE = re.compile(
    r"(?:python(?:3)?\s+cherenkov\.py|cherenkov|\./bin/cherenkov)\s+"
    r"([a-z][\w-]*(?:\s+[a-z][\w-]*)?)"
)
_FLAG_RE = re.compile(r"(?<![\w-])--[a-z][\w-]*")


def _real_flags_by_command(cli) -> dict[str, set[str]]:
    """{command_ref: {long flag options}} — mirrors check_cli_flags.py."""
    out: dict[str, set[str]] = {}

    def visit(cmd, prefix: str) -> None:
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
    for key, flags in list(out.items()):
        if " " in key:
            parent = key.split(" ", 1)[0]
            out.setdefault(parent, set()).update(flags)
    return out


def _command_exists(real: dict[str, set[str]], path: str) -> bool:
    """A command path exists if it is a real key, or one of its parent
    groups rolls up to it (e.g. `review review` documents `review`'s flags).
    """
    if path in real:
        return True
    parts = path.split()
    if len(parts) > 1:
        return any(
            k.startswith(parts[0] + " ") and k.split()[1:] == parts[1:]
            for k in real
        )
    return False


def _flags_for(real: dict[str, set[str]], path: str) -> set[str]:
    if path in real:
        return real[path]
    merged: set[str] = set()
    for k, v in real.items():
        if k == path or k.startswith(path + " "):
            merged |= v
    return merged


def _iter_bash_blocks(path: str):
    """Yield (start_line, [raw line, ...]) for each fenced bash/sh block."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    in_block = False
    block: list[str] = []
    start = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_block and stripped.startswith("```"):
            lang = stripped[3:].strip()
            if lang in ("bash", "sh"):
                in_block = True
                block = []
                start = i
            continue
        if in_block:
            if stripped.startswith("```"):
                yield start, block
                in_block = False
                block = []
            else:
                block.append(line)


def _strip_shell(line: str) -> str:
    """Remove a `$ ` prompt prefix and inline trailing comments."""
    line = line.strip()
    if line.startswith("$ "):
        line = line[2:].strip()
    # Strip trailing comment only when it is not inside quotes.
    quote = None
    for i, ch in enumerate(line):
        if ch in ("'", '"'):
            if quote is None:
                quote = ch
            elif quote == ch:
                quote = None
        elif ch == "#" and quote is None:
            line = line[:i].rstrip()
            break
    return line.strip()


def _validate_session(path: str, real: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    try:
        rel = os.path.relpath(path, _REPO_ROOT)
    except ValueError:
        # Path may be on a different mount (e.g., Windows vs WSL); use absolute path.
        rel = path
    seen_commands = 0
    external = 0
    for start, block in _iter_bash_blocks(path):
        for line in block:
            cleaned = _strip_shell(line)
            if not cleaned:
                continue
            if not re.match(r"(?:python(?:3)?\s+cherenkov\.py|cherenkov|\./bin/cherenkov)", cleaned):
                external += 1
                continue
            m = _INVOKE_RE.search(cleaned)
            if not m:
                continue
            seen_commands += 1
            path_ref = m.group(1).strip()
            if not _command_exists(real, path_ref):
                errors.append(
                    f"{rel}:{start}: `{path_ref}` is not a real command "
                    f"(documented in a session but missing from the CLI)."
                )
                continue
            opts = _flags_for(real, path_ref)
            for flag in _FLAG_RE.findall(cleaned):
                if flag in _HELP_FLAGS:
                    continue
                if flag not in opts:
                    errors.append(
                        f"{rel}:{start}: `{path_ref} {flag}` — flag does not exist "
                        f"(has: {sorted(opts) if opts else 'none'})."
                    )
    if seen_commands == 0:
        print(f"  {rel}: no cherenkov invocations found in bash blocks")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify onboarding transcripts against the live CHERENKOV CLI."
    )
    parser.add_argument(
        "--session",
        default="all",
        help="Which session to verify (a, b, c, or all). Default: all.",
    )
    args = parser.parse_args()

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

    real = _real_flags_by_command(cli)

    session_files = {
        "a": os.path.join(_SESSIONS_DIR, "session_a_zero_to_hero.md"),
        "b": os.path.join(_SESSIONS_DIR, "session_b_live_case.md"),
        "c": os.path.join(_SESSIONS_DIR, "session_c_pitch_companion.md"),
    }
    if args.session == "all":
        targets = list(session_files.values())
    elif args.session in session_files:
        targets = [session_files[args.session]]
    else:
        print(f"[FAIL] unknown session '{args.session}' (expected a, b, c, or all)")
        return 1

    errors: list[str] = []
    for path in targets:
        if not os.path.isfile(path):
            print(f"[FAIL] missing session doc: {path}")
            return 1
        print(f"Verifying {os.path.relpath(path, _REPO_ROOT)} ...")
        errors.extend(_validate_session(path, real))

    print()
    if errors:
        print(f"[FAIL] {len(errors)} transcript drift issue(s):")
        for e in errors:
            print(f"  * {e}")
        print("\nFix the session doc so every cherenkov command/flag is a real CLI option.")
        return 1
    print("[PASS] every cherenkov command and flag in the onboarding transcripts is real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
