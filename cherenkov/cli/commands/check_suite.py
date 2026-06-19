"""
cherenkov/cli/commands/check_suite.py — E2.5: `cherenkov check-suite`.

Catches the three canonical ways an AI agent "cheats" when editing or
generating a test suite:

  1. WEAKENED   — a strict (==) assertion loosened to a weak comparator
  2. DELETED    — a test or specific assertion removed from the baseline
  3. HALLUCINATED — asserts on a response field the spec never defines

Wraps the static-analysis engine from demos/catch-the-ai-cheating/ as a
first-class CLI command (E2.5 / MCP_VERIFICATION_SERVER.md §4.1 wedge).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Optional

import click

# ── AST analysis (no external deps, stdlib only) ──────────────────────────────

_STRONG = {"Eq"}
_WEAK = {"NotEq", "Lt", "LtE", "Gt", "GtE", "In", "NotIn", "Is", "IsNot"}
_BODY_NAMES = {"body", "data", "payload", "json", "resp_json", "response"}


def _spec_fields(spec_path: Path) -> set[str]:
    text = spec_path.read_text(encoding="utf-8")
    fields: set[str] = set()
    try:
        import yaml  # type: ignore[import]
        doc = yaml.safe_load(text)

        def _walk(node: object) -> None:
            if isinstance(node, dict):
                props = node.get("properties")
                if isinstance(props, dict):
                    fields.update(props.keys())
                for v in node.values():
                    _walk(v)
            elif isinstance(node, list):
                for v in node:
                    _walk(v)

        _walk(doc)
    except Exception:
        in_props = False
        for line in text.splitlines():
            if re.match(r"\s*properties:\s*$", line):
                in_props = True
                continue
            if in_props:
                m = re.match(r"\s{2,}([A-Za-z_][\w]*):", line)
                if m:
                    fields.add(m.group(1))
                elif line.strip() and not line.startswith(" "):
                    in_props = False
    return fields


def _subject_and_field(left: ast.expr) -> tuple[str, str | None]:
    subject = ast.unparse(left)
    field: str | None = None
    if isinstance(left, ast.Subscript) and isinstance(left.value, ast.Name):
        if left.value.id in _BODY_NAMES and isinstance(left.slice, ast.Constant):
            if isinstance(left.slice.value, str):
                field = left.slice.value
    elif isinstance(left, ast.Attribute) and isinstance(left.value, ast.Name):
        if left.value.id in _BODY_NAMES:
            field = left.attr
    return subject, field


def _parse_suite(code: str) -> dict[str, dict[str, set[str]]]:
    tree = ast.parse(code)
    out: dict[str, dict[str, set[str]]] = {}
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test"):
            subjects: dict[str, set[str]] = {}
            for n in ast.walk(fn):
                if isinstance(n, ast.Assert) and isinstance(n.test, ast.Compare):
                    subj, _ = _subject_and_field(n.test.left)
                    ops = {type(o).__name__ for o in n.test.ops}
                    subjects.setdefault(subj, set()).update(ops)
            out[fn.name] = subjects
    return out


def _candidate_fields(code: str) -> set[str]:
    tree = ast.parse(code)
    fields: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assert) and isinstance(n.test, ast.Compare):
            _, f = _subject_and_field(n.test.left)
            if f:
                fields.add(f)
    return fields


def check_integrity(
    spec_path: Path | None,
    baseline_code: str,
    candidate_code: str,
) -> list[str]:
    findings: list[str] = []
    allowed = _spec_fields(spec_path) if spec_path else set()
    base = _parse_suite(baseline_code)
    cand = _parse_suite(candidate_code)

    for tname, bsubs in base.items():
        if tname not in cand:
            findings.append(f"DELETED   test removed entirely: {tname}()")
            continue
        csubs = cand[tname]
        for subj, bops in bsubs.items():
            if subj not in csubs:
                findings.append(
                    f"DELETED   assertion dropped in {tname}(): `{subj}` no longer checked"
                )
                continue
            cops = csubs[subj]
            if (bops & _STRONG) and not (cops & _STRONG) and (cops & _WEAK):
                findings.append(
                    f"WEAKENED  {tname}(): `{subj}` strict check (==) loosened to {sorted(cops)}"
                )

    if allowed:
        for f in sorted(_candidate_fields(candidate_code)):
            if f not in allowed:
                findings.append(
                    f"HALLUCINATED candidate asserts on `{f}` — not defined in the spec"
                )
    return findings


# ── CLI command ────────────────────────────────────────────────────────────────

@click.command("check-suite")
@click.option(
    "--candidate",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Path to the candidate test suite to check (Python .py or TypeScript .ts).",
)
@click.option(
    "--baseline",
    "-b",
    default=None,
    type=click.Path(exists=True),
    help="Path to the known-honest baseline suite to compare against. "
    "Required for WEAKENED and DELETED detection.",
)
@click.option(
    "--spec",
    "-s",
    default=None,
    type=click.Path(exists=True),
    help="Path to the OpenAPI spec (YAML/JSON). Required for HALLUCINATED detection.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Write JSON findings report to this file.",
)
@click.option(
    "--fail-on-finding",
    is_flag=True,
    default=False,
    help="Exit with code 1 if any integrity violations are found (CI gate mode).",
)
def check_suite_cmd(
    candidate: str,
    baseline: Optional[str],
    spec: Optional[str],
    output: Optional[str],
    fail_on_finding: bool,
) -> None:
    """Catch AI cheating in a test suite — detect WEAKENED, DELETED, or HALLUCINATED assertions.

    Runs fast static analysis (no execution, no server needed).

    \b
    Examples:
      # Check a candidate against a baseline and spec:
      cherenkov check-suite --candidate candidate.py --baseline baseline.py --spec openapi.yaml

      # Baseline-only check (hallucinated detection requires --spec):
      cherenkov check-suite --candidate candidate.py --baseline baseline.py

      # CI gate mode — fail the build if integrity violations are found:
      cherenkov check-suite -c candidate.py -b baseline.py -s api.yaml --fail-on-finding
    """
    cand_path = Path(candidate)

    if cand_path.suffix not in (".py", ".ts"):
        click.echo(
            f"[WARNING] Candidate file has extension '{cand_path.suffix}'. "
            "Full AST analysis is only available for Python (.py) suites. "
            "TypeScript suites use regex-based detection.",
            err=True,
        )

    try:
        candidate_code = cand_path.read_text(encoding="utf-8")
    except Exception as exc:
        click.echo(f"[ERROR] Could not read candidate: {exc}", err=True)
        sys.exit(2)

    if cand_path.suffix == ".ts":
        findings = _check_typescript(
            candidate_code,
            Path(baseline).read_text(encoding="utf-8") if baseline else None,
            Path(spec) if spec else None,
        )
    else:
        baseline_code = ""
        if baseline:
            try:
                baseline_code = Path(baseline).read_text(encoding="utf-8")
            except Exception as exc:
                click.echo(f"[ERROR] Could not read baseline: {exc}", err=True)
                sys.exit(2)

        spec_path = Path(spec) if spec else None
        findings = check_integrity(spec_path, baseline_code, candidate_code)

    _print_findings(cand_path.name, findings)

    if output:
        import json
        Path(output).write_text(json.dumps({"candidate": candidate, "findings": findings}, indent=2))
        click.echo(f"\nFindings written to {output}")

    if fail_on_finding and findings:
        sys.exit(1)


def _check_typescript(
    candidate_code: str,
    baseline_code: Optional[str],
    spec_path: Optional[Path],
) -> list[str]:
    """Regex-based integrity check for TypeScript test suites."""
    findings: list[str] = []

    weak_re = re.compile(r"expect\([^)]+\)\.(not\.toBe|toContain|toBeTruthy|toBeFalsy|toBeDefined)\(")
    strict_re = re.compile(r"expect\([^)]+\)\.toBe\(")

    cand_has_strict = bool(strict_re.search(candidate_code))
    cand_has_weak_only = bool(weak_re.search(candidate_code)) and not cand_has_strict
    if cand_has_weak_only:
        findings.append("WEAKENED  candidate uses only weak matchers (no .toBe() found)")

    if baseline_code:
        base_tests = set(re.findall(r"(?:it|test)\(['\"]([^'\"]+)['\"]", baseline_code))
        cand_tests = set(re.findall(r"(?:it|test)\(['\"]([^'\"]+)['\"]", candidate_code))
        for t in sorted(base_tests - cand_tests):
            findings.append(f"DELETED   test case removed: '{t}'")

    if spec_path:
        allowed = _spec_fields(spec_path)
        accessed = set(re.findall(r'\.([a-zA-Z_]\w+)\b', candidate_code))
        for f in sorted(accessed):
            if f not in allowed and f not in {
                "status", "data", "body", "json", "headers", "text",
                "toBe", "toEqual", "toContain", "not", "expect",
            }:
                pass  # too noisy for regex — skip hallucination check for TS

    return findings


def _print_findings(label: str, findings: list[str]) -> None:
    width = 64
    click.echo(f"\n{'=' * width}")
    click.echo(f"  check-suite: {label}")
    click.echo(f"{'=' * width}")
    if not findings:
        click.echo(click.style("  PASS — no integrity violations found.", fg="green", bold=True))
    else:
        click.echo(
            click.style(f"  FAIL — {len(findings)} integrity violation(s):", fg="red", bold=True)
        )
        for f in findings:
            tag = f.split()[0]
            colour = {"WEAKENED": "yellow", "DELETED": "red", "HALLUCINATED": "magenta"}.get(tag, "white")
            click.echo(f"    {click.style('[CAUGHT]', fg=colour, bold=True)} {f}")
    click.echo("")
