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
# JS intrinsics on the parsed body — `expect(data.length).toBeGreaterThan(0)` is
# an assertion about the array, not about a spec-defined field called `length`.
# `status` is absent on purpose: it is a real petstore `Pet` property.
_TS_NON_FIELD_ATTRS = {"length", "size"}
# Only the modifiers that *declare a test* belong here. `test.describe` is
# deliberately absent: matching it would swallow every test inside the block as
# one segment, which is the bug HANDOVER.md records against the repo-audit
# detector. Hooks (`beforeEach`, `setTimeout`, …) are absent for the same
# reason — they hold no assertions and would be scored as empty tests.
_RE_TS_TEST = re.compile(
    r"""\btest(?:\.(?P<mod>skip|only|fixme|failing))?\s*\(\s*['"`](?P<name>[^'"`]+)['"`]"""
)
_RE_TS_EXPECT = re.compile(
    r"""expect\(\s*(?P<subj>.*?)\s*\)\s*\.\s*"""
    r"""(?P<matcher>(?:not\.)?[A-Za-z]+)\s*\(\s*(?P<arg>[^)]*)\)"""
)
# `request.get('/pets')`, `api.post("/pet/1", …)`, `fetch(\`/orders\`)` — the
# endpoint a test targets, used to scope HALLUCINATED to that endpoint's schema.
_RE_TS_REQUEST = re.compile(
    r"""(?:\.(?:get|post|put|patch|delete|head|options|fetch)|\bfetch)"""
    r"""\s*\(\s*['"`](?P<path>[^'"`]+)['"`]""",
    re.IGNORECASE,
)

# ── AST analysis (no external deps, stdlib only) ──────────────────────────────

_STRONG = {"Eq"}
_WEAK = {
    "NotEq", "Lt", "LtE", "Gt", "GtE", "In", "NotIn", "Is", "IsNot",
    # Bare `assert body["id"]` / `assert not resp.failed`: a truthiness check is
    # the weakest assertion there is, so a baseline `== 201` degraded to one is
    # WEAKENED, and dropping one entirely is DELETED.
    "Truthy", "Falsy",
}
_BODY_NAMES = {"body", "data", "payload", "json", "resp_json", "response"}
_JSON_METHODS = {"json", "get_json"}

# Attributes of an HTTP *response object* — never keys of the response *body*.
# `response` is in `_BODY_NAMES` because `response["id"]` is a real body idiom,
# but that also made `response.status_code` parse as a body field named
# `status_code`, which is then checked against the body schema it can never
# appear in. Measured against `bench/integrity_corpus/`, that single confusion
# produced a 41.7% false positive rate: every honest pytest case asserting
# `response.status_code == 200` was reported HALLUCINATED.
#
# Deliberately excluded from this list: `status`, `url`, `id`, `name` — all
# plausible response-body fields (petstore's `Pet` really does have `status`),
# so suppressing them would buy a lower FPR with false negatives.
_RESPONSE_ATTRS = {
    "status_code", "ok", "text", "content", "headers", "cookies", "elapsed",
    "encoding", "apparent_encoding", "reason", "raw", "history", "is_redirect",
    "is_permanent_redirect", "request", "links", "next", "connection",
}
_HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}

# `unittest`/`TestCase` assertions are method calls, not `assert` statements, so
# an AST walk looking only for `ast.Assert` is blind to the entire idiom.
_UNITTEST_OPS = {
    "assertEqual": "Eq", "assertEquals": "Eq",
    "assertNotEqual": "NotEq",
    "assertIs": "Is", "assertIsNot": "IsNot",
    "assertIsNone": "Is", "assertIsNotNone": "IsNot",
    "assertIn": "In", "assertNotIn": "NotIn",
    "assertGreater": "Gt", "assertGreaterEqual": "GtE",
    "assertLess": "Lt", "assertLessEqual": "LtE",
    "assertTrue": "Truthy", "assertFalse": "Falsy",
}

def _spec_fields(spec_path: Path) -> set[str]:
    """Every property name defined anywhere in the spec.

    This is the *fallback* alphabet for HALLUCINATED detection, used only when a
    test's target endpoint cannot be resolved. On its own it is a weak check: it
    asks "does this name exist somewhere in the spec", so a test on `/pet/{id}`
    asserting `shipDate` (an Order field) reads as clean. Prefer
    ``_spec_endpoint_fields`` + ``_match_path``, which scope the alphabet to the
    endpoint actually under test.
    """
    text = spec_path.read_text(encoding="utf-8")
    fields: set[str] = set()
    doc = _load_spec(spec_path)
    if doc is not None:

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
        return fields

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


def _load_spec(spec_path: Path) -> dict | None:
    """Parse the spec to a dict, or None if it cannot be parsed structurally."""
    try:
        import yaml  # type: ignore[import]

        doc = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def _resolve_ref(doc: dict, ref: str) -> object | None:
    """Resolve a local `#/components/schemas/X` pointer. Remote refs are skipped."""
    if not ref.startswith("#/"):
        return None
    node: object = doc
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _schema_fields(schema: object, doc: dict, seen: set[int] | None = None) -> set[str]:
    """Property names reachable from a response schema.

    Follows `$ref`, unwraps `array.items`, and unions the branches of
    `allOf`/`oneOf`/`anyOf`. Recursive schemas terminate via ``seen``.
    """
    if not isinstance(schema, dict):
        return set()
    seen = seen if seen is not None else set()
    if id(schema) in seen:
        return set()
    seen.add(id(schema))

    ref = schema.get("$ref")
    if isinstance(ref, str):
        return _schema_fields(_resolve_ref(doc, ref), doc, seen)

    fields: set[str] = set()
    props = schema.get("properties")
    if isinstance(props, dict):
        fields.update(props)
        # Nested objects contribute their own field names: a test may assert on
        # `body["category"]` and on the nested `name` it carries.
        for sub in props.values():
            fields |= _schema_fields(sub, doc, seen)
    for key in ("allOf", "oneOf", "anyOf"):
        branches = schema.get(key)
        if isinstance(branches, list):
            for branch in branches:
                fields |= _schema_fields(branch, doc, seen)
    if schema.get("type") == "array" or "items" in schema:
        fields |= _schema_fields(schema.get("items"), doc, seen)
    extra = schema.get("additionalProperties")
    if isinstance(extra, dict):
        fields |= _schema_fields(extra, doc, seen)
    return fields


def _spec_endpoint_fields(spec_path: Path) -> dict[str, set[str]]:
    """`{path_template: field_names}` drawn from each path's response schemas.

    This is what makes HALLUCINATED detection mean "not on *this* endpoint"
    rather than "absent from the entire document".
    """
    doc = _load_spec(spec_path)
    if doc is None:
        return {}
    paths = doc.get("paths")
    if not isinstance(paths, dict):
        return {}

    out: dict[str, set[str]] = {}
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        fields: set[str] = set()
        for method, op in item.items():
            if method.lower() not in _HTTP_METHODS or not isinstance(op, dict):
                continue
            responses = op.get("responses")
            if not isinstance(responses, dict):
                continue
            for resp in responses.values():
                if not isinstance(resp, dict):
                    continue
                content = resp.get("content")
                if isinstance(content, dict):
                    for media in content.values():
                        if isinstance(media, dict):
                            fields |= _schema_fields(media.get("schema"), doc)
                # Swagger 2.0 puts the schema directly on the response.
                if "schema" in resp:
                    fields |= _schema_fields(resp.get("schema"), doc)
        out[str(path)] = fields
    return out


def _normalise_url_path(raw: str) -> str:
    """Strip scheme/host, query and trailing slash so a URL can meet a template."""
    path = raw.split("?", 1)[0].split("#", 1)[0]
    if "://" in path:
        path = "/" + path.split("://", 1)[1].partition("/")[2]
    path = path.rstrip("/")
    return path or "/"


def _match_path(url: str, templates: list[str]) -> str | None:
    """Match a concrete request path against OpenAPI path templates.

    `/pet/1` matches `/pet/{petId}`. Exact matches win over templated ones, and
    an ambiguous match (two templates of equal specificity) returns None rather
    than guessing — a wrong endpoint would produce a false HALLUCINATED.
    """
    target = _normalise_url_path(url)
    exact = [t for t in templates if _normalise_url_path(t) == target]
    if exact:
        return exact[0]

    segments = target.strip("/").split("/")
    candidates: list[tuple[int, str]] = []
    for template in templates:
        tpl_segments = _normalise_url_path(template).strip("/").split("/")
        if len(tpl_segments) != len(segments):
            continue
        literals = 0
        for tpl_seg, seg in zip(tpl_segments, segments):
            if tpl_seg.startswith("{") and tpl_seg.endswith("}"):
                continue
            if tpl_seg != seg:
                break
            literals += 1
        else:
            candidates.append((literals, template))
    if not candidates:
        return None
    best = max(c[0] for c in candidates)
    top = [c[1] for c in candidates if c[0] == best]
    return top[0] if len(top) == 1 else None


def _allowed_fields_for(
    request_paths: set[str],
    endpoint_fields: dict[str, set[str]],
    fallback: set[str],
) -> tuple[set[str], bool]:
    """Resolve the field alphabet a test's assertions are checked against.

    Returns `(fields, scoped)`. `scoped` is False when no request path in the
    test resolved to a spec endpoint, in which case the caller is holding the
    weaker whole-document alphabet and should say so rather than imply precision.
    """
    templates = list(endpoint_fields)
    matched = {m for p in request_paths if (m := _match_path(p, templates)) is not None}
    if not matched:
        return fallback, False
    scoped: set[str] = set()
    for template in matched:
        scoped |= endpoint_fields.get(template, set())
    return scoped, True

def _response_field(left: ast.expr, _depth: int = 0) -> str | None:
    """Extract the response-body field a comparison's left-hand side asserts on.

    Recognises the common idioms for reading a JSON response body:
      * a bound body variable — ``body["f"]`` / ``data.f`` where the name is in
        ``_BODY_NAMES``
      * a chained ``.json()`` / ``.get_json()`` call — ``resp.json()["f"]``,
        ``client.get(...).json()["f"]``
      * a field wrapped in a call — ``data["f"].endswith(...)``, ``len(data["f"])``,
        ``str(data["f"]).strip()``. Without this the field is invisible: the LHS
        is an ``ast.Call``, so the ``Subscript`` carrying the name is never
        reached. `bench/integrity_corpus/` case ``py-halluc-owner-field``
        (`data['owner_email'].endswith(...)`) went undetected for exactly this
        reason — a hallucinated field hidden behind a string method.

    Returns the field name, or ``None`` if the LHS is not a body-field access.
    """
    if _depth > 4:  # pathological nesting — stop rather than recurse forever
        return None

    # Unwrap calls: `data["f"].endswith(x)` (method on the field) and
    # `len(data["f"])` (field as the argument) both hide the subscript.
    if isinstance(left, ast.Call):
        if isinstance(left.func, ast.Attribute) and left.func.attr not in _JSON_METHODS:
            inner = _response_field(left.func.value, _depth + 1)
            if inner is not None:
                return inner
        for arg in left.args:
            inner = _response_field(arg, _depth + 1)
            if inner is not None:
                return inner
        return None

    if isinstance(left, ast.Subscript) and isinstance(left.slice, ast.Constant) and isinstance(left.slice.value, str):
        base = left.value
        if isinstance(base, ast.Name) and base.id in _BODY_NAMES:
            return left.slice.value
        # chained call: <expr>.json()["f"] / <expr>.get_json()["f"]
        if isinstance(base, ast.Call) and isinstance(base.func, ast.Attribute) and base.func.attr in _JSON_METHODS:
            return left.slice.value
    elif isinstance(left, ast.Attribute) and isinstance(left.value, ast.Name) and left.value.id in _BODY_NAMES:
        # `response.status_code` is an attribute of the response object, not a
        # field of the body — returning it here would have it checked against
        # the body schema and reported HALLUCINATED on every honest test.
        # Returning None keeps it a tracked *subject* (so `== 201` degraded to
        # `< 500` is still WEAKENED) while removing it from the field alphabet.
        if left.attr in _RESPONSE_ATTRS:
            return None
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

def _iter_test_expr(test: ast.expr):
    """Yield `(subject, field, ops)` for every assertion inside one `assert`.

    Previously only a bare `ast.Compare` was recognised, which made three very
    common forms invisible — and a suite that deleted all of them still reported
    clean:

      * `assert a == 1 and b == 2` — a `BoolOp`, so *neither* comparison was seen
      * `assert resp.ok` — a truthiness check, not a comparison
      * `assert not resp.failed` — a negated truthiness check

    Compound assertions are decomposed into their operands so weakening one half
    of an `and` is caught on its own terms.
    """
    if isinstance(test, ast.BoolOp):
        for value in test.values:
            yield from _iter_test_expr(value)
        return
    if isinstance(test, ast.Compare):
        subject, field = _subject_and_field(test.left)
        yield subject, field, {type(o).__name__ for o in test.ops}
        return
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        subject, field = _subject_and_field(test.operand)
        yield subject, field, {"Falsy"}
        return
    subject, field = _subject_and_field(test)
    yield subject, field, {"Truthy"}


def _iter_unittest_call(call: ast.Call):
    """Yield `(subject, field, ops)` for a `self.assertEqual(...)`-style call."""
    func = call.func
    name = (
        func.attr if isinstance(func, ast.Attribute)
        else func.id if isinstance(func, ast.Name)
        else None
    )
    op = _UNITTEST_OPS.get(name or "")
    if op is None or not call.args:
        return
    subject, field = _subject_and_field(call.args[0])
    yield subject, field, {op}


def _iter_assertions(node: ast.AST):
    """Yield `(subject, field, ops)` for every assertion in a function body."""
    for n in ast.walk(node):
        if isinstance(n, ast.Assert):
            yield from _iter_test_expr(n.test)
        elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
            yield from _iter_unittest_call(n.value)


def _test_functions(tree: ast.AST):
    """Every `test*` function, including `async def` and methods on TestCase classes."""
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name.startswith("test"):
            yield fn


def _parse_suite(code: str) -> dict[str, dict[str, set[str]]]:
    tree = ast.parse(code)
    out: dict[str, dict[str, set[str]]] = {}
    for fn in _test_functions(tree):
        subjects: dict[str, set[str]] = {}
        for subject, _field, ops in _iter_assertions(fn):
            subjects.setdefault(subject, set()).update(ops)
        out[fn.name] = subjects
    return out


def _py_test_paths(code: str) -> dict[str, set[str]]:
    """`{test_name: request paths}` — the endpoints each test appears to call.

    Any string literal starting with `/` passed to a call inside the test is
    treated as a candidate request path; f-strings contribute their literal
    segments, so `f"{base}/pets"` still resolves. This over-collects rather than
    under-collects, and an unresolvable path degrades to the whole-document
    alphabet instead of producing a false HALLUCINATED.
    """
    tree = ast.parse(code)
    out: dict[str, set[str]] = {}
    for fn in _test_functions(tree):
        paths: set[str] = set()
        for n in ast.walk(fn):
            if not isinstance(n, ast.Call):
                continue
            for arg in n.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith("/") or "://" in arg.value:
                        paths.add(arg.value)
                elif isinstance(arg, ast.JoinedStr):
                    literal = "".join(
                        v.value for v in arg.values
                        if isinstance(v, ast.Constant) and isinstance(v.value, str)
                    )
                    if literal.startswith("/"):
                        paths.add(literal)
        out[fn.name] = paths
    return out


def _candidate_fields(code: str) -> set[str]:
    fields: set[str] = set()
    tree = ast.parse(code)
    for fn in _test_functions(tree):
        for _subject, field, _ops in _iter_assertions(fn):
            if field:
                fields.add(field)
    return fields


def _candidate_fields_by_test(code: str) -> dict[str, set[str]]:
    """`{test_name: asserted response fields}` — the per-test form of the above."""
    tree = ast.parse(code)
    out: dict[str, set[str]] = {}
    for fn in _test_functions(tree):
        out[fn.name] = {f for _s, f, _o in _iter_assertions(fn) if f}
    return out

def check_integrity(
    spec_path: Path | None,
    baseline_code: str,
    candidate_code: str,
) -> list[str]:
    """Check integrity of generated suite against baseline and spec fields.

    Args:
        spec_path (Path | None): OpenAPI specification path.
        baseline_code (str): Baseline test code string.
        candidate_code (str): Candidate test code string.

    Returns:
        list[str]: List of finding strings.
    """

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

    if spec_path is not None:
        findings.extend(_hallucinated_findings(spec_path, candidate_code, allowed))
    return findings


def _hallucinated_findings(
    spec_path: Path,
    candidate_code: str,
    fallback: set[str],
) -> list[str]:
    """HALLUCINATED findings, scoped to each test's own endpoint where possible.

    The whole-document alphabet is only the fallback. Scoping matters because the
    union of every `properties` key in a real spec covers most plausible field
    names, so an unscoped check approaches a no-op as the spec grows — a test on
    `/pet/{petId}` asserting `shipDate` reads as clean under it.
    """
    endpoint_fields = _spec_endpoint_fields(spec_path)
    per_test = _candidate_fields_by_test(candidate_code)
    test_paths = _py_test_paths(candidate_code)

    findings: list[str] = []
    for test_name in sorted(per_test):
        fields = per_test[test_name]
        if not fields:
            continue
        allowed, scoped = _allowed_fields_for(
            test_paths.get(test_name, set()), endpoint_fields, fallback
        )
        if not allowed:
            continue
        for field in sorted(fields - allowed):
            where = (
                f"not on the endpoint {test_name}() calls"
                if scoped
                else "not defined in the spec"
            )
            findings.append(
                f"HALLUCINATED {test_name}() asserts on `{field}` — {where}"
            )
    return findings

# ── CLI command ────────────────────────────────────────────────────────────────

@click.command("check-suite")
@click.option(
    "--candidate",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Path to the candidate test suite to check — a single file "
    "(Python .py or TypeScript .ts) or a directory, which is walked "
    "recursively for .py/.ts suites.",
)
@click.option(
    "--baseline",
    "-b",
    default=None,
    type=click.Path(exists=True),
    help="Path to the known-honest baseline suite to compare against. "
    "Required for WEAKENED and DELETED detection. When --candidate is a "
    "directory, pass the matching baseline directory: files are paired by "
    "their path relative to each root.",
)
@click.option(
    "--spec",
    "-s",
    default=None,
    type=click.Path(exists=True),
    help=(
        "Path to the OpenAPI spec (YAML/JSON). Required for HALLUCINATED "
        "detection, which is available for both Python and TypeScript suites. "
        "Asserted fields are checked against the response schema of the "
        "endpoint each test calls, falling back to the whole document when the "
        "endpoint cannot be resolved."
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


All three checks need their inputs: WEAKENED and DELETED require --baseline,
HALLUCINATED requires --spec. Whatever could not run is listed under
NOT_CHECKED in the report, so a green verdict always states its own scope.

Examples:
  # Full audit — all three checks. Both paths may be files or directories:
  cherenkov check-suite --candidate ./tests --baseline ./tests-baseline --spec openapi.yaml

  # Baseline-only check (hallucinated detection requires --spec):
  cherenkov check-suite --candidate candidate.py --baseline baseline.py

  # CI gate mode — fail the build if integrity violations are found:
  cherenkov check-suite -c candidate.py -b baseline.py -s api.yaml --fail-on-finding

Args:
    candidate: Path to the candidate test suite file.
    baseline: Path to the baseline test suite file, or None.
    spec: Path to the OpenAPI specification file, or None.
    output: Path to write output JSON report file, or None.
    fail_on_finding: True to exit code 1 when findings are present.
    as_json: True to emit structured JSON output on stdout.

Returns:
    None: Command execution result.
    """

    cand_path = Path(candidate)

    # A directory is what the README tells people to pass, and what anyone
    # pointing this at a real `tests/` tree will try first. Walk it rather than
    # failing with "Is a directory" on the product's own headline command.
    if cand_path.is_dir():
        cand_files = _collect_suite_files(cand_path)
        if not cand_files:
            click.echo(
                f"[ERROR] No .py or .ts test suites found under {cand_path}.",
                err=True,
            )
            sys.exit(2)
    else:
        cand_files = [cand_path]

    base_path = Path(baseline) if baseline else None
    if base_path is not None and base_path.is_dir() and not cand_path.is_dir():
        click.echo(
            "[ERROR] --baseline is a directory but --candidate is a single "
            "file; pass a baseline file, or make both directories.",
            err=True,
        )
        sys.exit(2)

    findings: list[str] = []
    per_file: list[dict] = []
    # A class is "checked" only if at least one file could actually run it.
    ran = {"WEAKENED": False, "DELETED": False, "HALLUCINATED": False}
    skipped: dict[str, str] = {}

    for cand_file in cand_files:
        base_file = _pair_baseline(cand_file, cand_path, base_path)
        file_findings = _check_one_file(cand_file, base_file, spec, ran, skipped)
        # With many files the bare finding text loses track of which suite it
        # came from, so prefix it once we are past the single-file case.
        if len(cand_files) > 1:
            rel = cand_file.relative_to(cand_path)
            file_findings = [f"{rel}: {f}" for f in file_findings]
        per_file.append({"file": str(cand_file), "findings": file_findings})
        findings.extend(file_findings)

    not_checked = _not_checked_reasons(ran, skipped)

    payload = {
        "candidate": candidate,
        "findings": findings,
        "clean": not findings,
        # Additive: a consumer that only reads `clean` still works, but one
        # that wants to know what the verdict actually covers now can.
        "files_checked": [str(p) for p in cand_files],
        "per_file": per_file,
        "checks_run": sorted(k for k, v in ran.items() if v),
        "checks_not_run": not_checked,
    }

    # --json owns stdout: a caller parsing this must not have to strip a banner.
    # Warnings above already went to stderr, so they do not corrupt the document.
    if as_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        label = (
            cand_path.name
            if len(cand_files) == 1
            else f"{cand_path} ({len(cand_files)} suites)"
        )
        _print_findings(label, findings, sorted(k for k, v in ran.items() if v), not_checked)

    if output:
        Path(output).write_text(json.dumps(payload, indent=2))
        if not as_json:
            click.echo(f"\nFindings written to {output}")

    if fail_on_finding and findings:
        sys.exit(1)


# Directories a test tree carries but never wants audited.
_SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}


def _collect_suite_files(root: Path) -> list[Path]:
    """Every `.py`/`.ts` suite under `root`, sorted, minus vendored trees."""
    out = [
        p
        for p in sorted(root.rglob("*"))
        if p.suffix in (".py", ".ts")
        and p.is_file()
        and not any(part in _SKIP_DIRS for part in p.parts)
    ]
    return out


def _pair_baseline(
    cand_file: Path, cand_root: Path, base_path: Path | None
) -> Path | None:
    """Baseline file matching `cand_file`, or None when there is no pair.

    Directory mode pairs on the path relative to each root, so
    `tests/api/users.py` is compared against `baseline/api/users.py` and not
    against some same-named file elsewhere in the tree.
    """
    if base_path is None:
        return None
    if not base_path.is_dir():
        return base_path
    candidate_rel = cand_file.relative_to(cand_root)
    paired = base_path / candidate_rel
    return paired if paired.is_file() else None


def _not_checked_reasons(ran: dict[str, bool], skipped: dict[str, str]) -> list[dict]:
    """`[{class, reason}]` for every violation class that never ran."""
    return [
        {"check": name, "reason": skipped.get(name, "not applicable to this suite")}
        for name in ("WEAKENED", "DELETED", "HALLUCINATED")
        if not ran[name]
    ]


def _check_one_file(
    cand_path: Path,
    base_path: Path | None,
    spec: str | None,
    ran: dict[str, bool],
    skipped: dict[str, str],
) -> list[str]:
    """Run the detector over one suite file, recording which classes ran.

    `ran` and `skipped` are accumulated across files by the caller, so a class
    counts as checked if any file in the run was able to check it.
    """
    # The `.ts` warning below used to be unreachable: `.ts` sat inside this
    # guard tuple, so the one audience that needed to hear "this is regex, not
    # AST" was the only audience never shown it. Split into two messages.
    if cand_path.suffix == ".ts":
        # This banner described a version of `_check_typescript` that no longer
        # exists: it announced "HALLUCINATED is NOT IMPLEMENTED" and "WEAKENED is
        # a file-level heuristic" in the same run that emitted per-test WEAKENED
        # and HALLUCINATED findings. A tool whose purpose is catching software
        # that misstates what it verifies cannot ship a banner that misstates
        # what it verifies. `tests/unit/test_capability_claims.py` now holds this
        # text to the code's real behaviour.
        click.echo(
            "[WARNING] TypeScript suites use regex over the Playwright assertion "
            "grammar, not AST analysis. WEAKENED and DELETED are compared per "
            "assertion against the baseline, segmented per test; HALLUCINATED is "
            "checked against --spec. Because the parse is regex rather than a "
            "syntax tree, assertions built dynamically or spanning unusual "
            "formatting can be missed. Full AST analysis is available for "
            "Python (.py) suites.",
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

    # Record what this run can and cannot establish. A verdict that does not
    # say which of the three checks actually ran is the exact failure this
    # tool exists to catch in other people's suites.
    if base_path is None:
        skipped["WEAKENED"] = "no --baseline given (required to compare assertions)"
        skipped["DELETED"] = "no --baseline given (required to detect removals)"
    else:
        ran["WEAKENED"] = True
        ran["DELETED"] = True

    spec_path = Path(spec) if spec else None
    if spec_path is None:
        skipped["HALLUCINATED"] = "no --spec given (required to resolve response fields)"

    if cand_path.suffix == ".ts":
        if spec_path is not None:
            ran["HALLUCINATED"] = True
        findings = _check_typescript(
            candidate_code,
            base_path.read_text(encoding="utf-8") if base_path else None,
            spec_path,
        )
    else:
        baseline_code = ""
        if base_path:
            try:
                baseline_code = base_path.read_text(encoding="utf-8")
            except Exception as exc:
                click.echo(f"[ERROR] Could not read baseline: {exc}", err=True)
                sys.exit(2)

        if spec_path is not None:
            if _spec_fields(spec_path):
                ran["HALLUCINATED"] = True
            else:
                skipped["HALLUCINATED"] = (
                    "--spec defines no response-body 'properties'"
                )
                click.echo(
                    "[WARNING] --spec defines no response-body 'properties'; "
                    "HALLUCINATED detection is inactive for this run.",
                    err=True,
                )
        findings = check_integrity(spec_path, baseline_code, candidate_code)

    return findings


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
            # See `_TS_NON_FIELD_ATTRS`: a JS intrinsic is not a spec field, and
            # reporting it HALLUCINATED punishes an honest length assertion.
            return None if m.group(1) in _TS_NON_FIELD_ATTRS else m.group(1)
    return None


def _ts_skipped_tests(code: str) -> set[str]:
    """Names of tests declared with a modifier that stops them executing."""
    return {
        m.group("name")
        for m in _RE_TS_TEST.finditer(code)
        if m.group("mod") in ("skip", "fixme")
    }


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
        base_skipped = _ts_skipped_tests(baseline_code)
        cand_skipped = _ts_skipped_tests(candidate_code)
        for test_name, base_subjects in baseline.items():
            if test_name not in candidate:
                findings.append(f"DELETED   test removed entirely: '{test_name}'")
                continue
            # Neutering a test with `.skip` leaves its body in the diff but
            # removes it from the run just as completely as deleting it — and
            # it reads as untouched to any check that only compares assertions.
            if test_name in cand_skipped and test_name not in base_skipped:
                findings.append(
                    f"DELETED   test disabled with .skip: '{test_name}' "
                    "(present in the file but never executed)"
                )
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
        fallback = _spec_fields(spec_path)
        endpoint_fields = _spec_endpoint_fields(spec_path)
        test_paths = _ts_test_paths(candidate_code)
        for test_name in sorted(candidate):
            asserted = {
                field
                for subject in candidate[test_name]
                if (field := _ts_field_of(subject))
            }
            if not asserted:
                continue
            allowed, scoped = _allowed_fields_for(
                test_paths.get(test_name, set()), endpoint_fields, fallback
            )
            if not allowed:
                continue
            for field in sorted(asserted - allowed):
                where = (
                    f"not on the endpoint '{test_name}' calls"
                    if scoped
                    else "not defined in the spec"
                )
                findings.append(
                    f"HALLUCINATED candidate asserts on `{field}` — {where}"
                )

    return findings


def _ts_test_paths(code: str) -> dict[str, set[str]]:
    """`{test_name: request paths}` for a TypeScript suite, segmented per test."""
    bounds = [(m.start(), m.group("name")) for m in _RE_TS_TEST.finditer(code)]
    out: dict[str, set[str]] = {}
    for i, (start, name) in enumerate(bounds):
        end = bounds[i + 1][0] if i + 1 < len(bounds) else len(code)
        out[name] = {m.group("path") for m in _RE_TS_REQUEST.finditer(code[start:end])}
    return out

def _print_findings(
    label: str,
    findings: list[str],
    checks_run: list[str] | None = None,
    not_checked: list[dict] | None = None,
) -> None:
    width = 64
    total = 3
    n_run = len(checks_run) if checks_run is not None else total
    click.echo(f"\n{'=' * width}")
    click.echo(f"  check-suite: {label}")
    click.echo(f"{'=' * width}")
    if not findings:
        # "PASS" alone overstates a run where two of three checks never
        # executed. The scope rides along with the verdict, always.
        scope = "" if n_run == total else f" ({n_run}/{total} checks)"
        click.echo(
            click.style(
                f"  PASS{scope} — no integrity violations found"
                f"{' in the checks that ran' if n_run != total else ''}.",
                fg="green",
                bold=True,
            )
        )
    else:
        click.echo(
            click.style(f"  FAIL — {len(findings)} integrity violation(s):", fg="red", bold=True)
        )
        for f in findings:
            tag = f.split()[0]
            colour = {"WEAKENED": "yellow", "DELETED": "red", "HALLUCINATED": "magenta"}.get(tag, "white")
            click.echo(f"    {click.style('[CAUGHT]', fg=colour, bold=True)} {f}")

    # The certificate printed by `cherenkov demo` states the boundary of its
    # guarantee via NOT_checked. This is that idea applied where it matters
    # most — the command people put in CI.
    if not_checked:
        click.echo("")
        click.echo(click.style("  NOT_CHECKED:", fg="yellow", bold=True))
        for entry in not_checked:
            click.echo(f"    {entry['check']:<14} {entry['reason']}")
    click.echo("")
