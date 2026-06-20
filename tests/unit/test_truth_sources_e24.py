"""E2.4 — truth/sources integration: GRPCSourceAdapter and GraphQLSourceAdapter."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cherenkov.truth.sources import GRPCSourceAdapter, GraphQLSourceAdapter
from cherenkov.core.contracts import Claim

_PROTO = """
syntax = "proto3";
package pets;

service PetService {
  rpc GetPet (GetPetRequest) returns (Pet);
  rpc ListPets (ListPetsRequest) returns (PetList);
}

message GetPetRequest { string id = 1; }
message Pet { string id = 1; string name = 2; }
message ListPetsRequest { int32 limit = 1; }
message PetList { repeated Pet pets = 1; }
"""

_SDL = """
type Query {
  pet(id: ID!): Pet
  pets(first: Int): [Pet!]!
}

type Mutation {
  createPet(name: String!): Pet
}

type Pet {
  id: ID!
  name: String!
}
"""


class TestGRPCSourceAdapter:
    def _adapter_with_proto(self, content: str) -> tuple[GRPCSourceAdapter, str]:
        tmp = tempfile.NamedTemporaryFile(suffix=".proto", delete=False, mode="w")
        tmp.write(content)
        tmp.close()
        return GRPCSourceAdapter(), tmp.name

    def test_returns_list_of_claims(self):
        adapter, path = self._adapter_with_proto(_PROTO)
        claims = adapter.discover_claims(path)
        assert isinstance(claims, list)
        assert all(isinstance(c, Claim) for c in claims)

    def test_rpc_claims_present(self):
        adapter, path = self._adapter_with_proto(_PROTO)
        claims = adapter.discover_claims(path)
        subjects = {c.subject for c in claims}
        assert any("GetPet" in s for s in subjects)
        assert any("ListPets" in s for s in subjects)

    def test_rpc_claim_category(self):
        adapter, path = self._adapter_with_proto(_PROTO)
        rpc_claims = [c for c in adapter.discover_claims(path) if c.category == "grpc_rpc"]
        assert len(rpc_claims) == 2

    def test_message_claims_present(self):
        adapter, path = self._adapter_with_proto(_PROTO)
        msg_claims = [c for c in adapter.discover_claims(path) if c.category == "grpc_message"]
        msg_names = {c.subject for c in msg_claims}
        assert any("Pet" in n for n in msg_names)

    def test_value_contains_request_response_types(self):
        adapter, path = self._adapter_with_proto(_PROTO)
        rpc_claims = [c for c in adapter.discover_claims(path) if c.category == "grpc_rpc"]
        get_pet = next(c for c in rpc_claims if "GetPet" in c.subject)
        assert get_pet.value["request_type"] == "GetPetRequest"
        assert get_pet.value["response_type"] == "Pet"

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            GRPCSourceAdapter().discover_claims("/nonexistent/path.proto")

    def test_wrong_extension_raises(self):
        with pytest.raises(ValueError):
            GRPCSourceAdapter().discover_claims("/some/file.yaml")

    def test_directory_with_no_protos_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with pytest.raises(FileNotFoundError):
                GRPCSourceAdapter().discover_claims(d)

    def test_directory_discovers_all_protos(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):
                (Path(d) / f"svc{i}.proto").write_text(_PROTO)
            claims = GRPCSourceAdapter().discover_claims(d)
            rpc_claims = [c for c in claims if c.category == "grpc_rpc"]
            assert len(rpc_claims) == 6  # 2 RPCs × 3 files

    def test_provenance_source_uri_is_absolute(self):
        adapter, path = self._adapter_with_proto(_PROTO)
        claims = adapter.discover_claims(path)
        for c in claims:
            assert Path(c.provenance.source_uri).is_absolute()


class TestGraphQLSourceAdapter:
    def _adapter_with_sdl(self, content: str) -> tuple[GraphQLSourceAdapter, str]:
        tmp = tempfile.NamedTemporaryFile(suffix=".graphql", delete=False, mode="w")
        tmp.write(content)
        tmp.close()
        return GraphQLSourceAdapter(), tmp.name

    def test_returns_list_of_claims(self):
        adapter, path = self._adapter_with_sdl(_SDL)
        claims = adapter.discover_claims(path)
        assert isinstance(claims, list)
        assert all(isinstance(c, Claim) for c in claims)

    def test_query_claims_present(self):
        adapter, path = self._adapter_with_sdl(_SDL)
        subjects = {c.subject for c in adapter.discover_claims(path)}
        assert any("pet" in s.lower() for s in subjects)

    def test_mutation_claims_present(self):
        adapter, path = self._adapter_with_sdl(_SDL)
        claims = adapter.discover_claims(path)
        mutation_claims = [
            c for c in claims
            if isinstance(c.value, dict) and c.value.get("operation_type") == "Mutation"
        ]
        assert len(mutation_claims) >= 1

    def test_file_not_found_raises(self):
        with pytest.raises((FileNotFoundError, Exception)):
            GraphQLSourceAdapter().discover_claims("/nonexistent/schema.graphql")

    def test_provenance_source_uri_set(self):
        adapter, path = self._adapter_with_sdl(_SDL)
        claims = adapter.discover_claims(path)
        assert all(c.provenance.source_uri for c in claims)

    def test_claim_ids_unique(self):
        adapter, path = self._adapter_with_sdl(_SDL)
        ids = [c.id for c in adapter.discover_claims(path)]
        assert len(ids) == len(set(ids)), "Duplicate claim IDs found"

    def test_schema_version_set(self):
        adapter, path = self._adapter_with_sdl(_SDL)
        from cherenkov.core.contracts import SCHEMA_VERSION
        claims = adapter.discover_claims(path)
        assert all(c.schema_version == SCHEMA_VERSION for c in claims)


class TestTruthSourcesPackageExports:
    def test_all_adapters_importable_from_package(self):
        from cherenkov.truth.sources import (
            GRPCSourceAdapter,
            GraphQLSourceAdapter,
            OpenAPISourceAdapter,
            TrafficSourceAdapter,
            DBSchemaSourceAdapter,
            SourceAdapter,
        )
        for cls in (GRPCSourceAdapter, GraphQLSourceAdapter, OpenAPISourceAdapter,
                    TrafficSourceAdapter, DBSchemaSourceAdapter):
            assert issubclass(cls, SourceAdapter)

    def test_grpc_adapter_in_all(self):
        from cherenkov.truth.sources import __all__
        assert "GRPCSourceAdapter" in __all__

    def test_graphql_adapter_in_all(self):
        from cherenkov.truth.sources import __all__
        assert "GraphQLSourceAdapter" in __all__
