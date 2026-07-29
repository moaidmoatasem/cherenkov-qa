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
