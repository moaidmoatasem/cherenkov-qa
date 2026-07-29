"""
CHERENKOV divergence/mutant_synth.py — spec-derived mutant-response synthesis.

Feeds `BrokenImplServer` (divergence/self_play.py) a deliberately-wrong
response derived mechanically from an OpenAPI operation, so the
meaningful-assertion check (E11-2, cherenkov/sdet/assertion_gate.py) can run
against *any* endpoint without a hand-authored broken-response table. This
closes the gap where `RepairLoop` (cherenkov generate --repair) only proved a
generated test satisfies syntactic/LLM-judge gates (ReviewStage), never that
it would actually catch a real regression — the same failure mode
`demos/catch-the-ai-cheating/` illustrates by hand.

The status mutation swaps within {200, 201} rather than emitting an error
code: a weakened assertion like `expect(status).toBeLessThan(500)` needs to
be caught, and an obvious 5xx would let it slip through as "meaningful" when
it isn't.
"""
from __future__ import annotations

from typing import Any

from cherenkov.divergence.probe_planner import (
    _path_with_samples,
    _resolve_ref,
    _response_fields,
    _sample_body,
    _success_code,
)
from cherenkov.divergence.self_play import BrokenImplServer


def _response_body_schema(
    operation: dict[str, Any], status: int, spec: dict[str, Any]
) -> dict[str, Any] | None:
    resp = _resolve_ref(operation.get("responses", {}).get(str(status), {}), spec)
    media = resp.get("content", {}).get("application/json")
    if not isinstance(media, dict):
        return None
    schema = _resolve_ref(media.get("schema", {}), spec)
    return schema if isinstance(schema, dict) else None


def _mutate_status(success: int) -> int:
    """A different, still-plausible 2xx code — a subtle regression, not an error."""
    return 200 if success != 200 else 201


def synthesize_mutant_response(
    path: str,
    operation: dict[str, Any],
    schemas: dict[str, Any] | None = None,
) -> tuple[str, int, dict[str, Any]] | None:
    """Derive one deliberately-wrong (concrete_path, status, body) triple.

    `schemas` is the already-resolved component-schema map carried on
    EndpointSlice/RepairLoop, wrapped here as a minimal spec stub so $ref
    resolution reuses probe_planner's helpers unchanged.

    Returns None for two distinct reasons — no documented success response to
    mutate from, or path parameters that cannot be filled with sample values.
    Call `explain_unmutatable()` for which one, so the gate's skip message
    names the real cause instead of guessing.
    """
    success = _success_code(operation)
    if success is None:
        return None

    spec_stub = {"components": {"schemas": schemas or {}}}

    concrete_path = _path_with_samples(path, operation, spec_stub)
    if concrete_path is None:
        return None

    schema = _response_body_schema(operation, success, spec_stub)
    body: dict[str, Any] = _sample_body(schema, spec_stub) if schema else {}
    fields = _response_fields(operation, success, spec_stub)
    if fields:
        body.pop(fields[0], None)

    return concrete_path, _mutate_status(success), body


def _enum_field(
    schema: dict[str, Any] | None, spec: dict[str, Any]
) -> tuple[str, list[Any]] | None:
    """First property carrying an `enum`, with its allowed values."""
    if not schema:
        return None
    for name, prop in (schema.get("properties") or {}).items():
        prop = _resolve_ref(prop, spec)
        values = prop.get("enum")
        if isinstance(values, list) and values:
            return str(name), values
    return None


def _wrong_same_type(value: Any) -> Any:
    """A different value of the same JSON type.

    Type-preserving on purpose: a type change is caught by any schema
    validator, so it proves nothing about whether the assertion checked the
    *value*. This is what separates `toBe(99.5)` from `toBeDefined()`.
    """
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return 0 if value != 0 else 1
    if isinstance(value, str):
        return "cherenkov_wrong_value" if value != "cherenkov_wrong_value" else "x"
    if isinstance(value, list):
        return []
    if isinstance(value, dict):
        return {}
    return None


def synthesize_mutant_battery(
    path: str,
    operation: dict[str, Any],
    schemas: dict[str, Any] | None = None,
    base: tuple[int, dict[str, Any]] | None = None,
) -> tuple[str, dict[str, tuple[int, dict[str, Any]]]] | None:
    """One mutant per failure axis, plus the conforming control.

    **`base` matters more than it looks.** Pass the response actually observed
    from the target — status and body — and every mutant perturbs *that*.
    Omit it and the body is sampled from the schema, which yields the right
    *types* but arbitrary *values* (`{"id": 1, "total": 1.0}` where the API
    returns 42 and 99.5).

    Schema sampling is only sound inside a closed loop, where the test was
    written against the same mock that now serves it — the repair loop's
    prism-dryrun path. For auditing a suite someone else wrote, sampled values
    make the honest suite fail the conforming control, and every verdict below
    becomes meaningless. Record first, then perturb.

    `synthesize_mutant_response` perturbs the status code *and* drops a
    required field in the same response. Measured against the labelled corpus
    in `demos/catch-the-ai-cheating/` that combination separates nothing: every
    suite fails it for some reason, so a deliberately weakened suite is scored
    "assertions are meaningful". See `docs/evidence/e0.5e_oracle_discrimination.md`.

    Isolating one axis at a time makes a failure attributable. A suite that
    passes the `conforming` control but also passes a mutant has an assertion
    blind to that axis:

      conforming  the documented success response, unperturbed. A suite that
                  fails this is broken or hallucinating — not weak — and no
                  mutant verdict below is meaningful for it.
      status      documented success code swapped for another plausible 2xx.
                  Passing means the status assertion is loose.
      value       one documented field set to a different value of the same
                  type. Passing means the field is checked for presence only.
      enum        an enum field set outside its allowed values. Passing means
                  the constraint is unasserted.
      missing     a required field dropped. Kept for conformance coverage; it
                  discriminates poorly, since honest suites fail it too.

    Returns (concrete_path, {name: (status, body)}) or None when the operation
    cannot be mutated — see `explain_unmutatable()` for why.
    """
    success = _success_code(operation)
    if success is None:
        return None

    spec_stub = {"components": {"schemas": schemas or {}}}
    concrete_path = _path_with_samples(path, operation, spec_stub)
    if concrete_path is None:
        return None

    schema = _response_body_schema(operation, success, spec_stub)
    if base is not None:
        success, conforming = base[0], dict(base[1])
    else:
        conforming = _sample_body(schema, spec_stub) if schema else {}

    battery: dict[str, tuple[int, dict[str, Any]]] = {
        "conforming": (success, dict(conforming)),
        "status": (_mutate_status(success), dict(conforming)),
    }

    fields = _response_fields(operation, success, spec_stub)

    if conforming:
        target = fields[0] if fields and fields[0] in conforming else next(iter(conforming))
        battery["value"] = (
            success,
            {**conforming, target: _wrong_same_type(conforming[target])},
        )

    enum = _enum_field(schema, spec_stub)
    if enum:
        name, allowed = enum
        outside = "cherenkov_not_in_enum"
        while outside in allowed:
            outside += "_x"
        battery["enum"] = (success, {**conforming, name: outside})

    if fields:
        dropped = {k: v for k, v in conforming.items() if k != fields[0]}
        battery["missing"] = (success, dropped)

    return concrete_path, battery


def explain_unmutatable(
    path: str,
    operation: dict[str, Any],
    schemas: dict[str, Any] | None = None,
) -> str:
    """Why `synthesize_mutant_response` returned None, in the user's terms.

    The two causes need different fixes — one is a spec that documents no
    success response, the other is a path parameter the planner cannot sample.
    Reporting them under one message sent readers looking for a missing 200
    that was never missing.
    """
    if _success_code(operation) is None:
        documented = ", ".join(sorted(str(c) for c in operation.get("responses", {}))) or "none"
        return (
            "spec documents no 2xx success response to mutate from "
            f"(documented: {documented})"
        )
    if _path_with_samples(path, operation, {"components": {"schemas": schemas or {}}}) is None:
        unfilled = [seg for seg in path.split("/") if seg.startswith("{")]
        return (
            f"path parameters could not be sampled: {', '.join(unfilled) or path}. "
            "Declare them under the operation's or the PathItem's `parameters` "
            "with a typed schema."
        )
    return "unknown cause"


def spawn_mutant_server(
    port: int,
    path: str,
    operation: dict[str, Any],
    schemas: dict[str, Any] | None = None,
) -> BrokenImplServer | None:
    """Build (unstarted) a BrokenImplServer mimicking a subtle spec regression.

    Returns None when the operation has no documented success response —
    callers should skip the meaningful-assertion gate rather than fabricate
    a response the spec never described.
    """
    mutation = synthesize_mutant_response(path, operation, schemas)
    if mutation is None:
        return None
    concrete_path, status, body = mutation
    return BrokenImplServer(port=port, responses={concrete_path: (status, body)})
