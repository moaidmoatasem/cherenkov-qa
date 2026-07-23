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
    resolution reuses probe_planner's helpers unchanged. Returns None when
    the operation documents no success response to mutate from.
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
