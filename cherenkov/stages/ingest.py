"""
CHERENKOV stages/ingest.py — real OpenAPI spec ingestion and depth-limited slicing stage.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from cherenkov.core.contracts import (
    IngestOutput,
    EndpointSlice,
    Mutation,
    Status,
    StageMeta,
    StageError,
)
from cherenkov.core.settings import get_settings
from cherenkov.core.errors import get_logger
from cherenkov.sources.mobile.adapter import MobileSourceAdapter

# ── Issue #194: Lightweight DAST Mutation Profile ──────────────────────────
# Curated OWASP payload set for security mutation testing.
# One representative payload per class to prove the safe-rejection contract.
DAST_PAYLOADS: list[tuple[str, str]] = [
    ("sqli_tautology", "' OR '1'='1"),
    ("sqli_stacked", "'; DROP TABLE users;--"),
    ("xss_reflected", "<script>alert(1)</script>"),
    ("xss_attribute", '" onmouseover="alert(1)'),
    ("path_traversal", "../../../../etc/passwd"),
    ("template_injection", "${{7*7}}"),
]


# Toggle env var — security mutations are opt-in to keep default runs focused
def _dast_enabled() -> bool:
    return get_settings().DAST_ENABLED


# [Issue #195] RAG toggle — schema-level semantic retrieval for large specs
def _rag_enabled() -> bool:
    return get_settings().RAG_ENABLED


def resolve_refs_depth(
    node: Any,
    schemas: dict[str, Any],
    resolved: dict[str, Any],
    depth: int,
    max_depth: int,
) -> None:
    """Recursively resolve OpenAPI component schemas up to max_depth to prevent context blowup."""
    if depth > max_depth:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if (
                k == "$ref"
                and isinstance(v, str)
                and v.startswith("#/components/schemas/")
            ):
                ref_name = v.split("/")[-1]
                if ref_name not in resolved and ref_name in schemas:
                    resolved[ref_name] = schemas[ref_name]
                    resolve_refs_depth(
                        schemas[ref_name], schemas, resolved, depth + 1, max_depth
                    )
            else:
                resolve_refs_depth(v, schemas, resolved, depth, max_depth)
    elif isinstance(node, list):
        for item in node:
            resolve_refs_depth(item, schemas, resolved, depth, max_depth)


class IngestStage:
    """Parses OpenAPI specifications, slices them with depth-1 reference resolution, and extracts deterministic mutations."""

    def __init__(self, run_id: str | None = None):
        self.log = get_logger("INGEST", run_id)
        self.mobile_adapter = MobileSourceAdapter()

    def run(self, spec_path: str) -> IngestOutput:
        t0 = time.time()
        self.log.info("stage start", spec_path=spec_path)

        path = Path(spec_path)
        if not path.exists():
            error_msg = f"Spec file not found at {spec_path}"
            self.log.error(error_msg)
            return IngestOutput(
                endpoints=[],
                client_stub_path="stub/client.ts",
                status=Status.FAILED,
                errors=[StageError(code="SPEC_NOT_FOUND", detail=error_msg)],
                metadata=StageMeta(stage="INGEST", duration_ms=0),
            )

        # Mobile format detection
        if path.suffix in (".apk", ".har", ".hil"):
            self.log.info("detected mobile source", format=path.suffix)
            self.mobile_adapter.ingest(spec_path)
            # Mobile sources do not produce API endpoint slices for the standard pipeline.
            # Return DEGRADED so callers know no scenarios will be planned.
            return IngestOutput(
                endpoints=[],
                client_stub_path="stub/client.ts",
                status=Status.DEGRADED,
                errors=[
                    StageError(
                        code="MOBILE_SOURCE",
                        detail=f"Mobile source ({path.suffix}) ingested but produces no REST endpoint slices. Use Track B mobile pipeline.",
                    )
                ],
                metadata=StageMeta(
                    stage="INGEST-mobile", duration_ms=int((time.time() - t0) * 1000)
                ),
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix in [".yaml", ".yml"]:
                    import yaml

                    spec = yaml.safe_load(f)
                else:
                    spec = json.load(f)
        except Exception as e:
            error_msg = f"Failed to parse OpenAPI spec (JSON/YAML): {e}"
            self.log.error(error_msg)
            return IngestOutput(
                endpoints=[],
                client_stub_path="stub/client.ts",
                status=Status.FAILED,
                errors=[StageError(code="INVALID_SPEC_JSON", detail=error_msg)],
                metadata=StageMeta(stage="INGEST", duration_ms=0),
            )

        components = spec.get("components", {}).get("schemas", {})
        endpoints: list[EndpointSlice] = []
        skipped_low_richness: list[StageError] = []

        paths_and_webhooks = {}
        paths_and_webhooks.update(spec.get("paths", {}))
        for hook_name, hook_item in spec.get("webhooks", {}).items():
            if isinstance(hook_item, dict):
                paths_and_webhooks[f"/_webhook/{hook_name}"] = hook_item

        for url_path, methods in paths_and_webhooks.items():
            for method, op in methods.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue

                # 1. Depth-limited reference resolution
                resolved_schemas: dict[str, Any] = {}
                resolve_refs_depth(
                    op, components, resolved_schemas, 1, get_settings().SCHEMA_DEPTH
                )

                # [Issue #195] RAG-based schema enrichment — retrieves semantically relevant schemas
                if _rag_enabled():
                    try:
                        from cherenkov.rag.schema_index import SchemaIndex

                        _rag_index: SchemaIndex | None = getattr(
                            IngestStage, "_rag", None
                        )
                        if _rag_index is None:
                            _rag_index = SchemaIndex()
                            _rag_index.index_spec(spec)
                            IngestStage._rag = _rag_index  # type: ignore
                        # Build query text from operation summary + parameter names
                        query_parts = [url_path, method.upper()]
                        if "summary" in op:
                            query_parts.append(op["summary"])
                        if "description" in op:
                            query_parts.append(op["description"])
                        for param in op.get("parameters", []):
                            if isinstance(param, dict):
                                query_parts.append(param.get("name", ""))
                        explicit_refs = set(resolved_schemas.keys())
                        rag_schemas = _rag_index.retrieve(
                            query_text=" | ".join(query_parts),
                            explicit_refs=explicit_refs,
                            top_k=5,
                        )
                        # Merge: RAG augments, doesn't replace depth-limited refs
                        resolved_schemas.update(rag_schemas)
                        self.log.info(
                            "rag enrichment",
                            endpoint=url_path,
                            before=len(explicit_refs),
                            after=len(resolved_schemas),
                        )
                    except Exception as e:
                        self.log.warning(
                            "rag enrichment failed, falling back to depth-limited only",
                            error=str(e),
                        )

                # 2. Richness score calculation
                # Richness is a mathematical metric (0.0 to 1.0) based on fields in schemas + parameters.
                num_params = len(op.get("parameters", []))
                num_fields = 0
                for schema in resolved_schemas.values():
                    if isinstance(schema, dict) and "properties" in schema:
                        num_fields += len(schema["properties"])
                richness = min(1.0, (num_params + num_fields + 1.0) / 10.0)

                # Skip/warn low richness endpoints
                if richness < 0.2:
                    self.log.warning(
                        "skipping low richness endpoint",
                        path=url_path,
                        method=method.upper(),
                        richness=richness,
                    )
                    skipped_low_richness.append(
                        StageError(
                            code="LOW_RICHNESS",
                            detail=f"{method.upper()} {url_path} skipped: richness {richness:.2f} < 0.2",
                        )
                    )
                    continue

                # 3. Generate deterministic mutation menu
                mutations: list[Mutation] = []

                # Determine validation status code from responses (e.g. 422 if defined in spec, else 400)
                responses = op.get("responses", {})
                validation_status = 400
                if "422" in responses:
                    validation_status = 422
                elif "400" in responses:
                    validation_status = 400

                # Always generate happy path
                expected_happy = 201 if method.lower() == "post" else 200
                mutations.append(
                    Mutation(
                        id="happy_path",
                        case_type="happy_path",
                        expected_status=expected_happy,
                        instruction="Provide valid request payload and parameters.",
                    )
                )

                # Always generate auth scenario
                mutations.append(
                    Mutation(
                        id="unauthorized",
                        case_type="auth",
                        expected_status=401,
                        instruction="Send request without valid authentication headers.",
                    )
                )

                # Body validation scenarios if requestBody is specified
                req_body = op.get("requestBody", {})
                if req_body:
                    content = req_body.get("content", {})
                    json_media = content.get("application/json", {}) or content.get(
                        "multipart/form-data", {}
                    )
                    body_schema = json_media.get("schema", {}) if json_media else {}

                    # Dereference body schema if it's a ref
                    if isinstance(body_schema, dict) and "$ref" in body_schema:
                        ref_name = body_schema["$ref"].split("/")[-1]
                        body_schema = resolved_schemas.get(ref_name, body_schema)

                    if isinstance(body_schema, dict):
                        required_fields = body_schema.get("required", [])
                        properties = body_schema.get("properties", {})

                        # Generate field omission validation
                        for req_field in required_fields:
                            mutations.append(
                                Mutation(
                                    id=f"missing_{req_field}",
                                    case_type="validation",
                                    expected_status=validation_status,
                                    instruction=f"Omit the required property '{req_field}' from the request body.",
                                )
                            )

                        # Generate boundary validations
                        for prop, prop_schema in properties.items():
                            if not isinstance(prop_schema, dict):
                                continue

                            prop_type = prop_schema.get("type")
                            if isinstance(prop_type, list) and len(prop_type) > 0:
                                prop_type = prop_type[0]

                            # String length violation
                            if prop_type == "string":
                                if (
                                    "max_length" in prop_schema
                                    or "maxLength" in prop_schema
                                ):
                                    max_l = prop_schema.get(
                                        "maxLength"
                                    ) or prop_schema.get("max_length")
                                    mutations.append(
                                        Mutation(
                                            id=f"{prop}_too_long",
                                            case_type="validation",
                                            expected_status=validation_status,
                                            instruction=f"Provide a string value for '{prop}' exceeding the max length of {max_l} characters.",
                                        )
                                    )
                                if (
                                    "min_length" in prop_schema
                                    or "minLength" in prop_schema
                                ):
                                    min_l = prop_schema.get(
                                        "minLength"
                                    ) or prop_schema.get("min_length")
                                    mutations.append(
                                        Mutation(
                                            id=f"{prop}_too_short",
                                            case_type="validation",
                                            expected_status=validation_status,
                                            instruction=f"Provide a string value for '{prop}' shorter than the min length of {min_l} characters.",
                                        )
                                    )
                                # [Issue #194] DAST security mutations — opt-in via CHERENKOV_DAST_ENABLED
                                if _dast_enabled():
                                    for pid, payload in DAST_PAYLOADS:
                                        mutations.append(
                                            Mutation(
                                                id=f"{prop}_{pid}",
                                                case_type="security",
                                                expected_status=validation_status,
                                                instruction=(
                                                    f"Set '{prop}' to the literal hostile payload {payload!r}. "
                                                    f"Assert the response status is 4xx (NOT 5xx, NOT 2xx) and "
                                                    f"the response body does NOT echo the payload verbatim."
                                                ),
                                                value=payload,
                                            )
                                        )
                            # Number value violation
                            elif prop_type in ("number", "integer"):
                                if "maximum" in prop_schema:
                                    max_v = prop_schema["maximum"]
                                    mutations.append(
                                        Mutation(
                                            id=f"{prop}_exceeds_max",
                                            case_type="validation",
                                            expected_status=validation_status,
                                            instruction=f"Provide a numeric value for '{prop}' exceeding the maximum allowed limit of {max_v}.",
                                        )
                                    )
                                if "minimum" in prop_schema:
                                    min_v = prop_schema["minimum"]
                                    mutations.append(
                                        Mutation(
                                            id=f"{prop}_below_min",
                                            case_type="validation",
                                            expected_status=validation_status,
                                            instruction=f"Provide a numeric value for '{prop}' below the minimum allowed limit of {min_v}.",
                                        )
                                    )

                endpoints.append(
                    EndpointSlice(
                        path=url_path,
                        method=method.upper(),
                        operation=op,
                        schemas=resolved_schemas,
                        richness=richness,
                        mutations=mutations,
                    )
                )

        dt = int((time.time() - t0) * 1000)
        self.log.info("stage success", endpoints_count=len(endpoints), duration_ms=dt)

        return IngestOutput(
            endpoints=endpoints,
            client_stub_path="stub/client.ts",
            status=Status.DEGRADED if skipped_low_richness else Status.OK,
            errors=skipped_low_richness,
            metadata=StageMeta(stage="INGEST", duration_ms=dt),
        )
