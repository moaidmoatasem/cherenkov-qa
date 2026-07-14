#!/usr/bin/env python3
"""
check_public_docs_clean.py
──────────────────────────
Validates that docs-site/docs/ contains no internal SSOT tokens, agent
operating instructions, or references that should never be public.

Run:
    python scripts/check_public_docs_clean.py
    python scripts/check_public_docs_clean.py --strict   # exit 1 on any warning

CI usage (in docs-deploy.yml):
    python scripts/check_public_docs_clean.py --strict

Exit codes:
    0 — clean
    1 — forbidden tokens found (in --strict mode)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

DOCS_PUBLIC_DIR = Path(__file__).parent.parent / "docs-site" / "docs"

# Patterns that MUST NOT appear in public docs
# Each entry: (pattern, description, severity)
FORBIDDEN: list[tuple[str, str, str]] = [
    # Internal doc references — ERROR in all contexts
    (r"HANDOVER\.md", "Reference to internal HANDOVER.md", "ERROR"),
    (r"PHASE_PLAN\.md", "Reference to internal PHASE_PLAN.md", "ERROR"),
    (r"AGENTS\.md", "Reference to internal AGENTS.md (agent operating rules)", "ERROR"),
    (r"INTEGRATION_STRATEGY\.md", "Reference to internal strategy doc", "ERROR"),
    (r"PRODUCT_STRATEGY_ROADMAP\.md", "Reference to internal strategy doc", "ERROR"),
    # Agent/AI-internal language — ERROR in all contexts
    (r"\bfabricated[- ]doc\b", "Fabricated-doc warning (agent artifact)", "ERROR"),
    (r"SSOT is `docs/`", "Internal SSOT reference", "ERROR"),
    (r"\bAgent Guidance\b", "Agent guidance block leaked to public docs", "ERROR"),
    (r"Authoritative handover:", "Handover language leaked to public docs", "ERROR"),
    (r"# Agent Operating Rules", "Agent operating rules header in public docs", "ERROR"),
    (r"\bINTERNAL\b", "Explicit INTERNAL marker", "ERROR"),
    (r"agent_sync\.py", "Internal agent sync script reference", "ERROR"),
    (r"docs/HANDOVER", "Raw path to internal HANDOVER doc", "ERROR"),
    (r"docs/PHASE_PLAN", "Raw path to internal PHASE_PLAN doc", "ERROR"),
    # TODO/FIXME markers
    (r"\bTODO\b", "Unresolved TODO", "WARN"),
    (r"\bFIXME\b", "Unresolved FIXME", "WARN"),
]

# These patterns only fire in non-architecture files
# (Architecture docs legitimately use Phase/CC-N as version markers)
FORBIDDEN_NON_ARCH: list[tuple[str, str, str]] = [
    (r"\bCC-[0-9]+\b", "Internal CC-N phase reference (ok in architecture/, warn elsewhere)", "WARN"),
    (r"\bPhase [0-9]+[ab]?\b", "Internal Phase N reference (ok in architecture/, warn elsewhere)", "WARN"),
    (r"\bagent[_\- ]memory\b", "Internal agent memory reference", "WARN"),
    (r"\btrack[- ][a-h]\b", "Internal track reference (Track A/B...)", "WARN"),
]

# File extensions to check
EXTENSIONS = {".md"}

# Files/dirs to skip (relative to DOCS_PUBLIC_DIR)
SKIP_PATHS = {
    "contributing.md",  # Contributing doc is allowed to reference internal docs
}


def check_file(path: Path, strict: bool) -> list[tuple[str, int, str, str]]:
    """Return list of (file, line_number, severity, message) for each violation."""
    violations = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return [(str(path), 0, "ERROR", f"Could not read file: {e}")]

    # Architecture docs legitimately use Phase/CC-N as version markers
    is_arch_doc = "architecture" in str(path)
    applicable_patterns = FORBIDDEN + ([] if is_arch_doc else FORBIDDEN_NON_ARCH)

    lines = text.splitlines()
    for lineno, line in enumerate(lines, start=1):
        for pattern, description, severity in applicable_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append((str(path), lineno, severity, f"{description}: `{line.strip()[:80]}`"))

    return violations



def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public docs are free of internal tokens")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any violation (including WARN)")
    parser.add_argument("--docs-dir", type=Path, default=DOCS_PUBLIC_DIR, help="Path to public docs dir")
    args = parser.parse_args()

    docs_dir = args.docs_dir
    if not docs_dir.exists():
        print(f"ERROR: docs dir not found: {docs_dir}", file=sys.stderr)
        return 1

    all_violations: list[tuple[str, int, str, str]] = []
    files_checked = 0

    for path in sorted(docs_dir.rglob("*")):
        if path.suffix not in EXTENSIONS:
            continue
        if path.name in SKIP_PATHS:
            continue
        files_checked += 1
        violations = check_file(path, args.strict)
        all_violations.extend(violations)

    errors = [(f, l, s, m) for f, l, s, m in all_violations if s == "ERROR"]
    warnings = [(f, l, s, m) for f, l, s, m in all_violations if s == "WARN"]

    print(f"CHERENKOV Public Docs Sanitizer — checked {files_checked} files")
    print(f"  Errors:   {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if all_violations:
        print()
        for filepath, lineno, severity, message in sorted(all_violations, key=lambda x: (x[2], x[0])):
            rel = Path(filepath).relative_to(docs_dir.parent.parent)
            tag = "❌ ERROR" if severity == "ERROR" else "⚠️  WARN "
            print(f"  {tag}  {rel}:{lineno}  {message}")

    print()
    if errors:
        print("❌ FAILED — internal tokens found in public docs. Fix before deploying.")
        return 1
    if args.strict and warnings:
        print("❌ FAILED (strict mode) — warnings treated as errors.")
        return 1
    if warnings:
        print("⚠️  PASSED with warnings — review before shipping.")
        return 0
    print("✅ PASSED — public docs are clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
