"""
CHERENKOV Truth Sources — Source adapters for claim extraction.

This package provides source adapters that extract normalized claims from
different sources of truth:
- OpenAPISourceAdapter: Extract claims from OpenAPI specifications
- TrafficSourceAdapter: Extract claims from HAR traffic captures
- DBSchemaSourceAdapter: Extract claims from database schemas
- GRPCSourceAdapter: Extract claims from .proto files (E2.4)
- GraphQLSourceAdapter: Extract claims from GraphQL SDL files (E2.4)
- SourceAdapter: Abstract base class for custom source adapters
"""

from cherenkov.truth.sources.interface import SourceAdapter
from cherenkov.truth.sources.openapi import OpenAPISourceAdapter
from cherenkov.truth.sources.traffic import TrafficSourceAdapter
from cherenkov.truth.sources.db_schema import DBSchemaSourceAdapter
from cherenkov.truth.sources.grpc import GRPCSourceAdapter
from cherenkov.truth.sources.graphql import GraphQLSourceAdapter

__all__ = [
    "SourceAdapter",
    "OpenAPISourceAdapter",
    "TrafficSourceAdapter",
    "DBSchemaSourceAdapter",
    "GRPCSourceAdapter",
    "GraphQLSourceAdapter",
]
