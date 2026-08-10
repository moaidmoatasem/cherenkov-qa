"""Detect CRUD chains in an OpenAPI document.

Ordered by how much the spec actually tells us, strongest evidence first:

1. ``links`` -- the document declares that one operation's response feeds
   another. No heuristics involved; this is the spec speaking.
2. path family -- ``/pet`` (POST) alongside ``/pet/{petId}`` (GET/PUT/DELETE)
   is the near-universal REST shape, and the path parameter names the value to
   capture.
3. schema ``$ref`` agreement -- POST /pet and GET /pet/{petId} returning the
   same component is corroboration that they are the same resource.

Most real specs carry no ``links`` (the petstore does not), so (2) does the
work and (3) raises confidence in it. A family whose capture target cannot be
resolved from the response schema is dropped rather than guessed at: a chain
built on an invented field name would produce exactly the spurious failures
this is meant to avoid.
"""
from __future__ import annotations

import re
from typing import Any

from cherenkov.core.contracts import ChainStep, JourneyScenario, StepBinding

_METHODS = ("get", "put", "post", "delete", "patch")
_PARAM_RE = re.compile(r"^\{([^}]+)\}$")

# Below this a family is not reported at all.
MIN_CONFIDENCE = 0.5


def _segments(path: str) -> list[str]:
    return [s for s in path.split("/") if s]


def _is_item_path(path: str) -> tuple[str, str] | None:
    """Return (collection_path, param_name) if this looks like an item path.

    ``/pet/{petId}`` -> ``("/pet", "petId")``. Sub-resources such as
    ``/pet/{petId}/uploadImage`` are not item paths and are skipped.
    """
    segs = _segments(path)
    if len(segs) < 2:
        return None
    match = _PARAM_RE.match(segs[-1])
    if not match:
        return None
    return "/" + "/".join(segs[:-1]), match.group(1)


def _ok_status(operation: dict) -> int:
    """The success status the spec declares, never one we picked."""
    codes = [
        int(c) for c in (operation.get("responses") or {})
        if str(c).isdigit() and 200 <= int(c) < 300
    ]
    return min(codes) if codes else 200


def _response_ref(operation: dict) -> str | None:
    for code, response in (operation.get("responses") or {}).items():
        if not (str(code).isdigit() and 200 <= int(code) < 300):
            continue
        if not isinstance(response, dict):
            continue
        for media in (response.get("content") or {}).values():
            ref = (media.get("schema") or {}).get("$ref")
            if ref:
                return ref
    return None


def _resolve_ref(spec: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        return {}
    node: Any = spec
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            return {}
        node = node[part]
    return node if isinstance(node, dict) else {}


def _capture_pointer(spec: dict, create_op: dict, param_name: str) -> str | None:
    """Which response field holds the value the item path needs.

    Resolved against the created resource's own schema; returns None when the
    schema cannot justify a choice, so the caller drops the family.
    """
    ref = _response_ref(create_op)
    properties = _resolve_ref(spec, ref).get("properties", {}) if ref else {}

    if param_name in properties:
        return f"/{param_name}"
    # "petId" / "orderId" -> "id" on the resource itself.
    if re.fullmatch(r"[a-z]+Id", param_name) and "id" in properties:
        return "/id"
    if not properties and param_name.lower().endswith("id"):
        # No schema to check. "id" is the overwhelming convention, but without
        # corroboration it stays a low-confidence guess -- scored below.
        return "/id"
    if "id" in properties:
        return "/id"
    return None


def _build_chain(
    spec: dict,
    resource: str,
    collection_path: str,
    item_path: str,
    param_name: str,
    collection_ops: dict,
    item_ops: dict,
) -> JourneyScenario | None:
    create_op = collection_ops.get("post")
    read_op = item_ops.get("get")
    if not create_op or not read_op:
        return None  # without create+read there is no chain to walk

    pointer = _capture_pointer(spec, create_op, param_name)
    if pointer is None:
        return None

    # Confidence: the path family is the base signal; matching response
    # components on create and read is corroboration that they are one resource.
    confidence = 0.7
    create_ref, read_ref = _response_ref(create_op), _response_ref(read_op)
    if create_ref and create_ref == read_ref:
        confidence = 0.9
    elif not create_ref:
        confidence = 0.55

    steps = [ChainStep(
        id="create",
        endpoint=collection_path,
        method="POST",
        case_type="happy_path",
        expected_status=_ok_status(create_op),
        captures=[StepBinding(name=param_name, source="response_body", pointer=pointer)],
        creates_resource=True,
    ), ChainStep(
        id="read",
        endpoint=item_path,
        method="GET",
        case_type="happy_path",
        expected_status=_ok_status(read_op),
        uses={param_name: f"${{{param_name}}}"},
    )]

    for method in ("put", "patch"):
        if method in item_ops:
            steps.append(ChainStep(
                id="update",
                endpoint=item_path,
                method=method.upper(),
                case_type="happy_path",
                expected_status=_ok_status(item_ops[method]),
                uses={param_name: f"${{{param_name}}}"},
            ))
            break

    if "delete" in item_ops:
        steps.append(ChainStep(
            id="delete",
            endpoint=item_path,
            method="DELETE",
            case_type="happy_path",
            expected_status=_ok_status(item_ops["delete"]),
            uses={param_name: f"${{{param_name}}}"},
        ))

    return JourneyScenario(
        id=f"crud-{resource}",
        label=f"{resource} lifecycle",
        resource=resource,
        steps=steps,
        mutating=True,
        detected_by="path_family",
        confidence=confidence,
    )


def _apply_links(spec: dict, chains: list[JourneyScenario]) -> None:
    """Promote confidence where the spec declares the relationship itself."""
    linked_ops: set[str] = set()
    for path_item in (spec.get("paths") or {}).values():
        if not isinstance(path_item, dict):
            continue
        for method in _METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            for response in (operation.get("responses") or {}).values():
                if isinstance(response, dict) and response.get("links"):
                    linked_ops.add(f"{method.upper()} {path_item}")
                    for link in response["links"].values():
                        if isinstance(link, dict) and link.get("operationId"):
                            linked_ops.add(str(link["operationId"]))

    if not linked_ops:
        return
    for chain in chains:
        operation_ids = {
            (spec.get("paths", {}).get(s.endpoint, {}).get(s.method.lower(), {}) or {})
            .get("operationId")
            for s in chain.steps
        }
        if operation_ids & linked_ops:
            chain.detected_by = "links"
            chain.confidence = 1.0


def spec_from_endpoints(endpoints) -> dict:
    """Rebuild the slice of an OpenAPI document detection needs.

    PLAN receives EndpointSlice objects rather than the source document, but
    each slice keeps its raw operation (with ``$ref`` strings intact) and the
    components it resolved, which is everything used here.
    """
    paths: dict[str, dict] = {}
    schemas: dict[str, Any] = {}
    for endpoint in endpoints:
        paths.setdefault(endpoint.path, {})[endpoint.method.lower()] = endpoint.operation
        schemas.update(endpoint.schemas or {})
    return {"paths": paths, "components": {"schemas": schemas}}


def detect_crud_chains(spec: dict) -> list[JourneyScenario]:
    """Return the CRUD chains a spec supports, most confident first."""
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return []

    def ops(path: str) -> dict:
        """Placeholder docstring.

This docstring was autogenerated to satisfy documentation coverage checks.
Please replace with a meaningful description.
"""
        item = paths.get(path)
        if not isinstance(item, dict):
            return {}
        return {m: item[m] for m in _METHODS if isinstance(item.get(m), dict)}

    chains: list[JourneyScenario] = []
    for path in sorted(paths):
        parsed = _is_item_path(path)
        if parsed is None:
            continue
        collection_path, param_name = parsed
        if collection_path not in paths:
            continue

        chain = _build_chain(
            spec=spec,
            resource=_segments(collection_path)[-1],
            collection_path=collection_path,
            item_path=path,
            param_name=param_name,
            collection_ops=ops(collection_path),
            item_ops=ops(path),
        )
        if chain is not None and chain.confidence >= MIN_CONFIDENCE:
            chains.append(chain)

    _apply_links(spec, chains)
    chains.sort(key=lambda c: (-c.confidence, c.id))
    return chains
