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
import json
import re
import sys
from pathlib import Path

import click

_RE_WEAK_MATCHER = re.compile(
    r"expect\([^)]+\)\.(not\.toBe|toContain|toBeTruthy|toBeFalsy|toBeDefined)\("
)
_RE_STRICT_MATCHER = re.compile(r"expect\([^)]+\)\.toBe\(")
_RE_YAML_PROPS_HDR = re.compile(r"\s*properties:\s*$")
_RE_YAML_FIELD = re.compile(r"\s{2,}([A-Za-z_][\w]*):")
_RE_TEST_NAME = re.compile(r"(?:it|test)\(['\"]([^'\"]+)['\"]")
_RE_PROP_ACCESS = re.compile(r"\.([a-zA-Z_]\w+)\b")

# ── TypeScript suite grammar (see _check_typescript) ─────────────────────────
_TS_STRONG = {"toBe", "toEqual", "toStrictEqual"}
_TS_WEAK = {
    "toBeLessThan", "toBeGreaterThan", "toBeLessThanOrEqual",
    "toBeGreaterThanOrEqual", "toBeTruthy", "toBeFalsy", "toBeDefined",
    "toBeUndefined", "toContain", "toMatch", "toHaveProperty",
    "not.toBeNull", "not.toBeUndefined", "toBeNull",
}
_TS_DATA_NAMES = ("data", "body", "json", "payload")
_RE_TS_TEST = re.compile(r"""\btest\s*\(\s*['"`](?P<name>[^'"`]+)['"`]""")
_RE_TS_EXPECT = re.compile(
    r"""expect\(\s*(?P<subj>.*?)\s*\)\s*\.\s*"""
    r"""(?P<matcher>(?:not\.)?[A-Za-z]+)\s*\(\s*(?P<arg>[^)]*)\)"""
)

# ── AST analysis (no external deps, stdlib only) ──────────────────────────────

_STRONG = {"Eq"}
_WEAK = {"NotEq", "Lt", "LtE", "Gt", "GtE", "In", "NotIn", "Is", "IsNot"}
_BODY_NAMES = {"body", "data", "payload", "json", "resp_json", "response"}
_JSON_METHODS = {"json", "get_json"}

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
                    fields.update(props)
                for v in node.values():
                    _walk(v)
            elif isinstance(node, list):
                for v in node:
                    _walk(v)

        _walk(doc)
    except Exception:
        in_props = False
        for line in text.splitlines():
            if _RE_YAML_PROPS_HDR.match(line):
                in_props = True
                continue
            if in_props:
                m = _RE_YAML_FIELD.match(line)
                if m:
                    fields.add(m.group(1))
                elif line.strip() and not line.startswith(" "):
                    in_props = False
    return fields

def _response_field(left: ast.expr) -> str | None:
    """Extract the response-body field a comparison's left-hand side asserts on.

    Recognises the common idioms for reading a JSON response body:
      * a bound body variable — ``body["f"]`` / ``data.f`` where the name is in
        ``_BODY_NAMES``
      * a chained ``.json()`` / ``.get_json()`` call — ``resp.json()["f"]``,
        ``client.get(...).json()["f"]``

    Returns the field name, or ``None`` if the LHS is not a body-field access.
    """
    if isinstance(left, ast.Subscript) and isinstance(left.slice, ast.Constant) and isinstance(left.slice.value, str):
        base = left.value
        if isinstance(base, ast.Name) and base.id in _BODY_NAMES:
            return left.slice.value
        # chained call: <expr>.json()["f"] / <expr>.get_json()["f"]
        if isinstance(base, ast.Call) and isinstance(base.func, ast.Attribute) and base.func.attr in _JSON_METHODS:
            return left.slice.value
    elif isinstance(left, ast.Attribute) and isinstance(left.value, ast.Name) and left.value.id in _BODY_NAMES:
        return left.attr
    return None

def _subject_and_field(left: ast.expr) -> tuple[str, str | None]:
    field = _response_field(left)
    if field is not None:
        # Canonical subject: unifies `resp.json()["id"]`, `body["id"]`, and
        # `body.id` so a semantics-preserving refactor of the access idiom
        # does not read as a WEAKENED/DELETED assertion (avoids false positives).
        # For the bare `body["id"]` idiom this equals the previous ast.unparse
        # output, so existing detection is unchanged.
        return f"body[{field!r}]", field
    return ast.unparse(left), None

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
    help=(
        "Path to the OpenAPI spec (YAML/JSON). Required for HALLUCINATED "
        "detection on Python suites; HALLUCINATED is not implemented for "
        "TypeScript, where this flag has no effect."
    ),
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
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit the findings as JSON on stdout instead of the human report.",
)
def check_suite_cmd(
    candidate: str,
    baseline: str | None,
    spec: str | None,
    output: str | None,
    fail_on_finding: bool,
    as_json: bool,
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

    # The `.ts` warning below used to be unreachable: `.ts` sat inside this
    # guard tuple, so the one audience that needed to hear "this is regex, not
    # AST" was the only audience never shown it. Split into two messages.
    if cand_path.suffix == ".ts":
        click.echo(
            "[WARNING] TypeScript suites use regex-based detection, not AST "
            "analysis. WEAKENED is a file-level heuristic (it does not compare "
            "against the baseline per assertion), DELETED only tracks test "
            "names, and HALLUCINATED is NOT IMPLEMENTED for TypeScript — "
            "--spec will not surface hallucinated assertions here. Full AST "
            "analysis is available for Python (.py) suites.",
            err=True,
        )
    elif cand_path.suffix != ".py":
        click.echo(
            f"[WARNING] Candidate file has extension '{cand_path.suffix}'. "
            "Only Python (.py) and TypeScript (.ts) suites are supported; "
            "results for other extensions are unreliable.",
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
        if spec_path is not None and not _spec_fields(spec_path):
            click.echo(
                "[WARNING] --spec defines no response-body 'properties'; "
                "HALLUCINATED detection is inactive for this run.",
                err=True,
            )
        findings = check_integrity(spec_path, baseline_code, candidate_code)

    payload = {"candidate": candidate, "findings": findings, "clean": not findings}

    # --json owns stdout: a caller parsing this must not have to strip a banner.
    # Warnings above already went to stderr, so they do not corrupt the document.
    if as_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        _print_findings(cand_path.name, findings)

    if output:
        Path(output).write_text(json.dumps(payload, indent=2))
        if not as_json:
            click.echo(f"\nFindings written to {output}")

    if fail_on_finding and findings:
        sys.exit(1)

def _ts_normalise_subject(raw: str) -> str:
    """`(data as any).total` and `data.total` are the same subject."""
    s = re.sub(r"\(\s*data\s+as\s+any\s*\)", "data", raw)
    s = s.replace("as any", "").replace("(", "").replace(")", "")
    return re.sub(r"\s+", "", s)


def _ts_field_of(subject: str) -> str | None:
    """`data.total` -> `total`; anything else -> None."""
    for name in _TS_DATA_NAMES:
        m = re.match(rf"^{name}\.([A-Za-z_]\w*)$", subject)
        if m:
            return m.group(1)
    return None


def _ts_parse_suite(code: str) -> dict[str, dict[str, set[str]]]:
    """`{test_name: {subject: {matchers}}}`, segmented per `test(...)` block.

    Segmenting matters: without it, DELETED and WEAKENED can only be judged
    across the whole file, so dropping an assertion from one test while another
    still asserts the same subject is invisible.
    """
    bounds = [(m.start(), m.group("name")) for m in _RE_TS_TEST.finditer(code)]
    out: dict[str, dict[str, set[str]]] = {}
    for i, (start, name) in enumerate(bounds):
        end = bounds[i + 1][0] if i + 1 < len(bounds) else len(code)
        segment = code[start:end]
        subjects: dict[str, set[str]] = {}
        for em in _RE_TS_EXPECT.finditer(segment):
            subject = _ts_normalise_subject(em.group("subj"))
            matcher = em.group("matcher")
            arg = em.group("arg").strip().strip("'\"`")
            # `expect(data).toHaveProperty('total')` asserts on data.total
            if matcher == "toHaveProperty" and arg:
                subject = f"data.{arg}"
            subjects.setdefault(subject, set()).add(matcher)
        out[name] = subjects
    return out


def _check_typescript(
    candidate_code: str,
    baseline_code: str | None,
    spec_path: Path | None,
) -> list[str]:
    """Integrity check for TypeScript suites.

    Regex over the Playwright assertion grammar — genuinely weaker than the
    `ast.parse` path used for Python, and the CLI says so before running.

    This is a port of `demos/catch-the-ai-cheating/integrity_check_ts.py`,
    which the CLI claimed to wrap while actually reimplementing a degraded
    version: WEAKENED was a whole-file heuristic that never consulted the
    baseline (so weakening nine of ten assertions passed clean if one
    `.toBe()` survived anywhere), DELETED compared only test names (so an
    assertion dropped from a surviving test was invisible), and HALLUCINATED
    was dead code — a `pass` statement under a loop, reachable by nothing.
    Since `.spec.ts` is CHERENKOV's own primary output format, the format the
    product emits had the weakest analysis behind it.
    """
    findings: list[str] = []
    candidate = _ts_parse_suite(candidate_code)

    if baseline_code:
        baseline = _ts_parse_suite(baseline_code)
        for test_name, base_subjects in baseline.items():
            if test_name not in candidate:
                findings.append(f"DELETED   test removed entirely: '{test_name}'")
                continue
            cand_subjects = candidate[test_name]
            for subject, base_matchers in base_subjects.items():
                if subject not in cand_subjects:
                    findings.append(
                        f"DELETED   assertion dropped in '{test_name}': "
                        f"`{subject}` no longer checked"
                    )
                    continue
                cand_matchers = cand_subjects[subject]
                strong_before = bool(base_matchers & _TS_STRONG)
                strong_after = bool(cand_matchers & _TS_STRONG)
                weak_after = bool(cand_matchers & _TS_WEAK)
                if strong_before and not strong_after and weak_after:
                    findings.append(
                        f"WEAKENED  '{test_name}': `{subject}` exact check "
                        f"loosened to {sorted(cand_matchers)}"
                    )

    if spec_path:
        allowed = _spec_fields(spec_path)
        if allowed:
            asserted: set[str] = set()
            for subjects in candidate.values():
                for subject in subjects:
                    field = _ts_field_of(subject)
                    if field:
                        asserted.add(field)
            for field in sorted(asserted):
                if field not in allowed:
                    findings.append(
                        f"HALLUCINATED candidate asserts on `{field}` — "
                        "not defined in the spec"
                    )

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
