from dataclasses import dataclass
from typing import Iterator
from graphql import build_ast_schema, parse, build_client_schema, get_introspection_query

@dataclass
class GraphQLOperation:
    name: str
    kind: str  # "query" | "mutation" | "subscription"
    fields: list[str]
    variables: dict
    return_type: str

class GraphQLSourceAdapter:
    """Parses GraphQL SDL or introspection JSON → EndpointSlice-equivalent operations."""

    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.schema = self._load_schema()

    def _load_schema(self):
        content = open(self.spec_path).read()
        if self.spec_path.endswith(".json"):
            # introspection JSON
            import json
            return build_client_schema(json.loads(content)["data"])
        else:
            # SDL (.graphql)
            return build_ast_schema(parse(content))

    def _get_leaf_fields(self, field_type) -> list[str]:
        # Minimal implementation for getting fields, extracting underlying types.
        return ["__typename"]

    def iter_operations(self) -> Iterator[GraphQLOperation]:
        """Yield one operation per queryable field on Query/Mutation/Subscription."""
        for type_name in ["Query", "Mutation", "Subscription"]:
            type_def = self.schema.type_map.get(type_name)
            if not type_def:
                continue
            for field_name, field in type_def.fields.items():
                yield GraphQLOperation(
                    name=field_name,
                    kind=type_name.lower(),
                    fields=self._get_leaf_fields(field.type),
                    variables={arg_name: str(arg.type) for arg_name, arg in field.args.items()},
                    return_type=str(field.type),
                )
