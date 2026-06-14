from dataclasses import dataclass
from typing import Iterator
from graphql import (
    build_ast_schema,
    parse,
    build_client_schema,
    GraphQLScalarType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLInterfaceType,
    GraphQLUnionType,
)


@dataclass
class GraphQLOperation:
    name: str
    kind: str
    fields: list[str]
    variables: dict
    return_type: str


class GraphQLSourceAdapter:

    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.schema = self._load_schema()

    def _load_schema(self):
        content = open(self.spec_path).read()
        if self.spec_path.endswith(".json"):
            import json
            data = json.loads(content)
            if "data" in data:
                data = data["data"]
            return build_client_schema(data)
        else:
            return build_ast_schema(parse(content))

    def _get_leaf_fields(self, field_type, depth: int = 0, max_depth: int = 5) -> list[str]:
        if depth >= max_depth:
            return ["__typename"]
        while isinstance(field_type, (GraphQLNonNull, GraphQLList)):
            field_type = field_type.of_type
        if isinstance(field_type, GraphQLScalarType):
            return []
        if isinstance(field_type, (GraphQLObjectType, GraphQLInterfaceType, GraphQLUnionType)):
            fields = []
            if isinstance(field_type, GraphQLUnionType):
                for possible_type in field_type.types:
                    fields.extend(self._get_leaf_fields(possible_type, depth + 1, max_depth))
            else:
                for field_name, field in field_type.fields.items():
                    if field_name in ("__typename", "__schema", "__type"):
                        continue
                    sub_fields = self._get_leaf_fields(field.type, depth + 1, max_depth)
                    if sub_fields:
                        for sf in sub_fields:
                            fields.append(f"{field_name}.{sf}")
                    else:
                        fields.append(field_name)
            return fields if fields else ["__typename"]
        return ["__typename"]

    def iter_operations(self) -> Iterator[GraphQLOperation]:
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
