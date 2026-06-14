"""
CHERENKOV truth/sources/openapi.py — OpenAPI Source Adapter.
Authority: v3.1 + delta.
"""

from __future__ import annotations

from pathlib import Path
from cherenkov.core.contracts import Claim, Provenance, ProvenanceType, Status
from cherenkov.stages.ingest import IngestStage
from cherenkov.truth.sources.interface import SourceAdapter


class OpenAPISourceAdapter(SourceAdapter):
    """Source adapter for OpenAPI specifications.

    Reuses the existing INGEST stage slicing logic to extract endpoints,
    richness, and mutation menus, presenting them as normalized Claims.
    """

    def discover_claims(self, source_uri: str) -> list[Claim]:
        uri_path = Path(source_uri)
        if not uri_path.exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {source_uri}")

        # Run the existing IngestStage parser
        ingest_stage = IngestStage()
        ingest_output = ingest_stage.run(str(uri_path))

        if ingest_output.status == Status.FAILED:
            errors_str = ", ".join(e.detail for e in ingest_output.errors)
            raise ValueError(f"Failed to ingest OpenAPI spec: {errors_str}")

        claims: list[Claim] = []

        for endpoint_slice in ingest_output.endpoints:
            method = endpoint_slice.method.upper()
            path = endpoint_slice.path
            subject_prefix = f"{method} {path}"

            # Normalize subject path for ID creation
            normalized_path = (
                path.replace("/", "_").replace("{", "").replace("}", "").strip("_")
            )
            id_prefix = f"spec_{method.lower()}_{normalized_path}"

            # 1. Endpoint existence and richness claim
            claims.append(
                Claim(
                    id=f"{id_prefix}_exists",
                    category="endpoint",
                    subject=subject_prefix,
                    value={
                        "richness": endpoint_slice.richness,
                        "operation_id": endpoint_slice.operation.get("operationId"),
                    },
                    provenance=Provenance(
                        source_type=ProvenanceType.SPEC,
                        source_uri=str(uri_path.resolve()),
                        details={"type": "endpoint_existence"},
                    ),
                )
            )

            # 2. Request configuration / details claim
            claims.append(
                Claim(
                    id=f"{id_prefix}_request",
                    category="request",
                    subject=subject_prefix,
                    value={
                        "parameters": endpoint_slice.operation.get("parameters", []),
                        "requestBody": endpoint_slice.operation.get("requestBody"),
                    },
                    provenance=Provenance(
                        source_type=ProvenanceType.SPEC,
                        source_uri=str(uri_path.resolve()),
                        details={"type": "request_definition"},
                    ),
                )
            )

            # 3. Mutation claims
            for mutation in endpoint_slice.mutations:
                claims.append(
                    Claim(
                        id=f"{id_prefix}_mutation_{mutation.id}",
                        category="mutation",
                        subject=f"{subject_prefix} -> mutation -> {mutation.id}",
                        value=mutation.model_dump(),
                        provenance=Provenance(
                            source_type=ProvenanceType.SPEC,
                            source_uri=str(uri_path.resolve()),
                            details={
                                "type": "mutation_scenario",
                                "mutation_id": mutation.id,
                                "expected_status": mutation.expected_status,
                            },
                        ),
                    )
                )

        return claims
