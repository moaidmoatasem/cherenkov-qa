"""
cherenkov/truth/spec_validator.py — Pre-ingest OpenAPI spec validation.

Validates a spec file or URL before the IngestStage touches it, surfacing
problems early with structured ValidationResult objects rather than
cryptic errors deep in the YAML parser.

Checks (in order):
  1. File/URL reachability (SPEC_NOT_FOUND)
  2. YAML/JSON parse (SPEC_PARSE_ERROR)
  3. Minimum required fields: openapi/swagger + info + paths (SPEC_PARSE_ERROR)
  4. Paths block is a non-empty dict (SPEC_PARSE_ERROR)
  5. Each path item has at least one HTTP operation (warning, not fatal)
  6. OpenAPI version recognised (warning)
  7. $ref resolution — detect dangling references (SPEC_PARSE_ERROR)

Returns a ValidationResult; callers decide whether to abort on warnings.

Usage:
    from cherenkov.truth.spec_validator import validate_spec

    result = validate_spec("openapi.yaml")
    if not result.ok:
        for e in result.errors:
            print(e.message)
        sys.exit(1)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class SpecIssue:
    severity: Severity
    code: str          # matches web ErrorCode names where applicable
    message: str
    location: str = ""  # JSONPath-style e.g. "paths./pets.get"


@dataclass
class ValidationResult:
    ok: bool                                    # False if any ERROR-level issue
    issues: list[SpecIssue] = field(default_factory=list)
    spec: dict | None = None                    # parsed spec on success

    @property
    def errors(self) -> list[SpecIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[SpecIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]


_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
_KNOWN_VERSIONS = {"3.0.0", "3.0.1", "3.0.2", "3.0.3", "3.1.0", "2.0"}


def _load_raw(source: str) -> tuple[str, str]:
    """Return (raw_text, detected_format) for a file path or URL."""
    p = Path(source)

    if p.exists():
        raw = p.read_text(encoding="utf-8")
        suffix = p.suffix.lower()
        fmt = "json" if suffix == ".json" else "yaml"
        return raw, fmt

    raise FileNotFoundError(f"Spec not found: {source!r}")


def _parse(raw: str, fmt: str) -> dict:
    if fmt == "json":
        return json.loads(raw)
    try:
        import yaml
        return yaml.safe_load(raw)
    except ImportError:
        raise ImportError("PyYAML is required to parse YAML specs: pip install pyyaml")


def _collect_refs(obj: Any, refs: set[str]) -> None:
    """Recursively collect all $ref strings from a spec object."""
    if isinstance(obj, dict):
        if "$ref" in obj and isinstance(obj["$ref"], str):
            refs.add(obj["$ref"])
        for v in obj.values():
            _collect_refs(v, refs)
    elif isinstance(obj, list):
        for item in obj:
            _collect_refs(item, refs)


def _resolve_local_ref(ref: str, spec: dict) -> bool:
    """Return True if a local $ref (#/...) resolves inside the spec."""
    if not ref.startswith("#/"):
        return True  # external refs — skip (can't resolve without network)
    parts = ref[2:].split("/")
    node = spec
    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def validate_spec(source: str, *, fatal_on_warnings: bool = False) -> ValidationResult:
    """
    Validate an OpenAPI spec at *source* (file path).

    Args:
        source: Path to a YAML or JSON OpenAPI spec file.
        fatal_on_warnings: If True, warnings also set ok=False.

    Returns:
        ValidationResult with .ok, .issues, and .spec (parsed dict on success).
    """
    issues: list[SpecIssue] = []

    # ── 1. Reachability ──────────────────────────────────────────────────────
    try:
        raw, fmt = _load_raw(source)
    except FileNotFoundError as exc:
        issues.append(SpecIssue(
            severity=Severity.ERROR,
            code="SPEC_NOT_FOUND",
            message=str(exc),
        ))
        return ValidationResult(ok=False, issues=issues)

    # ── 2. Parse ─────────────────────────────────────────────────────────────
    try:
        spec = _parse(raw, fmt)
    except Exception as exc:
        issues.append(SpecIssue(
            severity=Severity.ERROR,
            code="SPEC_PARSE_ERROR",
            message=f"Failed to parse {fmt.upper()}: {exc}",
        ))
        return ValidationResult(ok=False, issues=issues)

    if not isinstance(spec, dict):
        issues.append(SpecIssue(
            severity=Severity.ERROR,
            code="SPEC_PARSE_ERROR",
            message="Spec root must be a YAML/JSON object, not a scalar or list.",
        ))
        return ValidationResult(ok=False, issues=issues)

    # ── 3. Minimum required fields ───────────────────────────────────────────
    has_openapi = "openapi" in spec or "swagger" in spec
    if not has_openapi:
        issues.append(SpecIssue(
            severity=Severity.ERROR,
            code="SPEC_PARSE_ERROR",
            message="Missing required field: 'openapi' (or 'swagger' for v2). "
                    "This does not appear to be an OpenAPI spec.",
        ))

    if "info" not in spec or not isinstance(spec.get("info"), dict):
        issues.append(SpecIssue(
            severity=Severity.ERROR,
            code="SPEC_PARSE_ERROR",
            message="Missing required field: 'info'.",
            location="info",
        ))

    paths = spec.get("paths")
    if paths is None:
        issues.append(SpecIssue(
            severity=Severity.ERROR,
            code="SPEC_PARSE_ERROR",
            message="Missing required field: 'paths'. No endpoints to test.",
            location="paths",
        ))
        return ValidationResult(ok=False, issues=issues, spec=spec)

    if not isinstance(paths, dict) or len(paths) == 0:
        issues.append(SpecIssue(
            severity=Severity.ERROR,
            code="SPEC_PARSE_ERROR",
            message="'paths' is empty — no endpoints to test.",
            location="paths",
        ))
        return ValidationResult(ok=False, issues=issues, spec=spec)

    # ── 4. Version check ─────────────────────────────────────────────────────
    version = spec.get("openapi") or spec.get("swagger", "")
    if version and str(version) not in _KNOWN_VERSIONS:
        issues.append(SpecIssue(
            severity=Severity.WARNING,
            code="SPEC_PARSE_ERROR",
            message=f"Unrecognised OpenAPI version: {version!r}. "
                    f"Known: {sorted(_KNOWN_VERSIONS)}.",
            location="openapi",
        ))

    # ── 5. Per-path operation check ──────────────────────────────────────────
    paths_without_ops: list[str] = []
    for path_key, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        ops = [k for k in path_item if k.lower() in _HTTP_METHODS]
        if not ops:
            paths_without_ops.append(path_key)

    if paths_without_ops:
        issues.append(SpecIssue(
            severity=Severity.WARNING,
            code="SPEC_PARSE_ERROR",
            message=f"{len(paths_without_ops)} path(s) have no HTTP operations "
                    f"(only shared parameters/refs?): {paths_without_ops[:5]}",
            location="paths",
        ))

    # ── 6. Dangling $ref detection ───────────────────────────────────────────
    refs: set[str] = set()
    _collect_refs(spec, refs)
    dangling = [r for r in refs if r.startswith("#/") and not _resolve_local_ref(r, spec)]
    if dangling:
        for ref in dangling[:10]:  # cap output
            issues.append(SpecIssue(
                severity=Severity.ERROR,
                code="SPEC_PARSE_ERROR",
                message=f"Dangling $ref: {ref!r} does not resolve.",
                location=ref,
            ))

    has_errors = any(i.severity == Severity.ERROR for i in issues)
    ok = not has_errors and (not fatal_on_warnings or not any(
        i.severity == Severity.WARNING for i in issues
    ))
    return ValidationResult(ok=ok, issues=issues, spec=spec)
