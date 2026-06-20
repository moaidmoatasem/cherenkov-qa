"""
cherenkov/truth/sources/graphql.py — E2.4: GraphQL source adapter.

Parses GraphQL Schema Definition Language (SDL) files to extract type
definitions, query/mutation/subscription operations, and field contracts
as normalized Claims.

Zero additional dependencies — pure regex over SDL syntax.
"""

from __future__ import annotations

import re
from pathlib import Path

from cherenkov.core.contracts import Claim, Provenance, ProvenanceType, SCHEMA_VERSION
from cherenkov.truth.sources.interface import SourceAdapter

# Matches: type Query {  or  type Mutation {  or  type Subscription {
_RE_OPERATION_ROOT = re.compile(
    r"\btype\s+(Query|Mutation|Subscription)\s*\{([^}]*)\}", re.DOTALL
)
# Matches: type Foo {
_RE_TYPE = re.compile(r"\btype\s+(\w+)\s*(?:implements\s+[\w\s&]+)?\{([^}]*)\}", re.DOTALL)
# Matches: input FooInput {
_RE_INPUT = re.compile(r"\binput\s+(\w+)\s*\{([^}]*)\}", re.DOTALL)
# Matches: interface IFoo {
_RE_INTERFACE = re.compile(r"\binterface\s+(\w+)\s*\{([^}]*)\}", re.DOTALL)
# Matches: enum Status {
_RE_ENUM = re.compile(r"\benum\s+(\w+)\s*\{([^}]*)\}", re.DOTALL)
# Matches a field line (with or without args):
#   id: ID!
#   user(id: ID!): User
#   posts(limit: Int = 10, offset: Int): [Post!]!
_RE_FIELD = re.compile(
    r"^\s+(\w+)\s*(\([^)]*\))?\s*:\s*([\w\[\]!]+)",
    re.MULTILINE,
)
# Matches: scalar DateTime
_RE_SCALAR = re.compile(r"\bscalar\s+(\w+)")
# Matches: union SearchResult = User | Post | Comment
_RE_UNION = re.compile(r"\bunion\s+(\w+)\s*=\s*([\w\s|]+)")
# Matches: schema { query: Query  mutation: Mutation }
_RE_SCHEMA_DEF = re.compile(
    r"\bschema\s*\{([^}]*)\}", re.DOTALL
)
# Matches: directive @deprecated(reason: String) on FIELD_DEFINITION
_RE_DIRECTIVE = re.compile(r'@(\w+)(?:\([^)]*\))?')


def _strip_comments(text: str) -> str:
    """Remove # comments and block string (\"\"\"...\"\"\") descriptions."""
    text = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
    text = re.sub(r'#[^\n]*', "", text)
    return text


def _parse_fields(block: str) -> list[dict]:
    fields = []
    for m in _RE_FIELD.finditer(block):
        name = m.group(1)
        has_args = m.group(2) is not None
        type_ref = m.group(3).strip()
        required = type_ref.endswith("!")
        is_list = "[" in type_ref
        directives = _RE_DIRECTIVE.findall(m.group(0))
        fields.append(
            {
                "name": name,
                "type": type_ref,
                "required": required,
                "list": is_list,
                "has_args": has_args,
                "deprecated": "deprecated" in directives,
            }
        )
    return fields


def _parse_sdl(text: str) -> dict:
    clean = _strip_comments(text)

    operations: dict[str, list[dict]] = {}
    for m in _RE_OPERATION_ROOT.finditer(clean):
        op_type = m.group(1)  # Query / Mutation / Subscription
        operations[op_type] = _parse_fields(m.group(2))

    types: dict[str, list[dict]] = {}
    for m in _RE_TYPE.finditer(clean):
        name = m.group(1)
        if name in ("Query", "Mutation", "Subscription"):
            continue
        types[name] = _parse_fields(m.group(2))

    inputs: dict[str, list[dict]] = {}
    for m in _RE_INPUT.finditer(clean):
        inputs[m.group(1)] = _parse_fields(m.group(2))

    interfaces: dict[str, list[dict]] = {}
    for m in _RE_INTERFACE.finditer(clean):
        interfaces[m.group(1)] = _parse_fields(m.group(2))

    enums: dict[str, list[str]] = {}
    for m in _RE_ENUM.finditer(clean):
        values = [v.strip() for v in m.group(2).split() if v.strip()]
        enums[m.group(1)] = values

    scalars = [m.group(1) for m in _RE_SCALAR.finditer(clean)]

    unions: dict[str, list[str]] = {}
    for m in _RE_UNION.finditer(clean):
        members = [v.strip() for v in m.group(2).split("|") if v.strip()]
        unions[m.group(1)] = members

    return {
        "operations": operations,
        "types": types,
        "inputs": inputs,
        "interfaces": interfaces,
        "enums": enums,
        "scalars": scalars,
        "unions": unions,
    }


class GraphQLSourceAdapter(SourceAdapter):
    """Source adapter for GraphQL SDL schema files.

    Accepts a .graphql / .gql file path or a directory.
    Emits one Claim per root operation field (Query/Mutation/Subscription)
    and one Claim per named type contract.
    """

    def discover_claims(self, source_uri: str) -> list[Claim]:
        uri_path = Path(source_uri)

        schema_files: list[Path]
        if uri_path.is_dir():
            schema_files = sorted(
                list(uri_path.rglob("*.graphql")) + list(uri_path.rglob("*.gql"))
            )
        elif uri_path.suffix in (".graphql", ".gql", ".graphqls"):
            if not uri_path.exists():
                raise FileNotFoundError(f"GraphQL schema file not found: {source_uri}")
            schema_files = [uri_path]
        else:
            raise ValueError(
                f"Expected a .graphql/.gql file or directory, got: {source_uri}"
            )

        if not schema_files:
            raise FileNotFoundError(f"No GraphQL schema files found under: {source_uri}")

        claims: list[Claim] = []
        for schema_path in schema_files:
            text = schema_path.read_text(encoding="utf-8")
            parsed = _parse_sdl(text)
            resolved = str(schema_path.resolve())

            # One claim per root operation field
            for op_type, fields in parsed["operations"].items():
                for field in fields:
                    field_name = field["name"]
                    safe_id = f"graphql_{op_type.lower()}_{field_name}"
                    claims.append(
                        Claim(
                            id=safe_id,
                            category="graphql_operation",
                            subject=f"{op_type}.{field_name}",
                            value={
                                "operation_type": op_type,
                                "return_type": field["type"],
                                "required": field["required"],
                                "list": field["list"],
                                "has_args": field["has_args"],
                                "deprecated": field["deprecated"],
                            },
                            provenance=Provenance(
                                source_type=ProvenanceType.SPEC,
                                source_uri=resolved,
                                details={
                                    "format": "graphql_sdl",
                                    "type": "operation_field",
                                    "operation_root": op_type,
                                },
                            ),
                            schema_version=SCHEMA_VERSION,
                        )
                    )

            # One claim per named object type
            for type_name, fields in parsed["types"].items():
                safe_id = f"graphql_type_{type_name}"
                claims.append(
                    Claim(
                        id=safe_id,
                        category="graphql_type",
                        subject=f"type {type_name}",
                        value={
                            "fields": fields,
                            "field_count": len(fields),
                            "required_fields": [f["name"] for f in fields if f["required"]],
                        },
                        provenance=Provenance(
                            source_type=ProvenanceType.SPEC,
                            source_uri=resolved,
                            details={"format": "graphql_sdl", "type": "object_type"},
                        ),
                        schema_version=SCHEMA_VERSION,
                    )
                )

            # One claim per input type (mutation/query arguments)
            for input_name, fields in parsed["inputs"].items():
                safe_id = f"graphql_input_{input_name}"
                claims.append(
                    Claim(
                        id=safe_id,
                        category="graphql_input",
                        subject=f"input {input_name}",
                        value={
                            "fields": fields,
                            "required_fields": [f["name"] for f in fields if f["required"]],
                        },
                        provenance=Provenance(
                            source_type=ProvenanceType.SPEC,
                            source_uri=resolved,
                            details={"format": "graphql_sdl", "type": "input_type"},
                        ),
                        schema_version=SCHEMA_VERSION,
                    )
                )

            # One claim per enum (contract: value set)
            for enum_name, values in parsed["enums"].items():
                safe_id = f"graphql_enum_{enum_name}"
                claims.append(
                    Claim(
                        id=safe_id,
                        category="graphql_enum",
                        subject=f"enum {enum_name}",
                        value={"values": values, "value_count": len(values)},
                        provenance=Provenance(
                            source_type=ProvenanceType.SPEC,
                            source_uri=resolved,
                            details={"format": "graphql_sdl", "type": "enum_contract"},
                        ),
                        schema_version=SCHEMA_VERSION,
                    )
                )

            # One claim per union (type discriminator contract)
            for union_name, members in parsed["unions"].items():
                safe_id = f"graphql_union_{union_name}"
                claims.append(
                    Claim(
                        id=safe_id,
                        category="graphql_union",
                        subject=f"union {union_name}",
                        value={"members": members},
                        provenance=Provenance(
                            source_type=ProvenanceType.SPEC,
                            source_uri=resolved,
                            details={"format": "graphql_sdl", "type": "union_contract"},
                        ),
                        schema_version=SCHEMA_VERSION,
                    )
                )

        return claims
