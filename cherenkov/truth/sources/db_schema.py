"""
cherenkov/truth/sources/db_schema.py — E2-5: DB-schema adapter.
Authority: v3.1 + delta.

Turn DB schema constraints into claims (enables D4: spec-vs-db divergence).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from cherenkov.core.contracts import Claim, Provenance, ProvenanceType
from cherenkov.truth.sources.interface import SourceAdapter


def _parse_create_table(sql: str) -> list[dict[str, Any]]:
    """Extract table definitions and their constraints from a SQL CREATE statement."""
    tables: list[dict[str, Any]] = []
    pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\.)?(\w+)\s*\((.*?)\)\s*;",
        re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(sql):
        table_name = match.group(1)
        body = match.group(2)

        columns: list[dict[str, Any]] = []
        constraints: list[dict[str, Any]] = []

        for line in body.split(","):
            line = line.strip()
            if not line:
                continue
            tokens = line.split()
            if not tokens:
                continue

            upper = tokens[0].upper()
            if upper in (
                "PRIMARY",
                "UNIQUE",
                "FOREIGN",
                "INDEX",
                "CHECK",
                "CONSTRAINT",
            ):
                constraints.append({"raw": line, "type": upper})
            else:
                col: dict[str, Any] = {
                    "name": tokens[0],
                    "type": tokens[1] if len(tokens) > 1 else "UNKNOWN",
                }
                rest_raw = " ".join(tokens[2:])
                rest_upper = rest_raw.upper()
                col["nullable"] = "NOT NULL" not in rest_upper
                col["primary_key"] = "PRIMARY KEY" in rest_upper
                col["unique"] = "UNIQUE" in rest_upper
                col["default"] = None
                default_match = re.search(r"DEFAULT\s+(\S+)", rest_raw, re.IGNORECASE)
                if default_match:
                    col["default"] = default_match.group(1)
                columns.append(col)

        tables.append(
            {
                "name": table_name,
                "columns": columns,
                "constraints": constraints,
            }
        )

    return tables


class DBSchemaSourceAdapter(SourceAdapter):
    """Source adapter for SQL database schema files.

    Parses CREATE TABLE statements into schema constraint claims.
    """

    def discover_claims(self, source_uri: str) -> list[Claim]:
        uri_path = Path(source_uri)
        if not uri_path.exists():
            raise FileNotFoundError(f"DB schema file not found: {source_uri}")

        sql = uri_path.read_text(encoding="utf-8")
        tables = _parse_create_table(sql)
        resolved = uri_path.resolve()

        claims: list[Claim] = []

        for table in tables:
            subject = f"table:{table['name']}"

            # Table existence claim
            claims.append(
                Claim(
                    id=f"db_table_{table['name']}",
                    category="table",
                    subject=subject,
                    value={
                        "name": table["name"],
                        "column_count": len(table["columns"]),
                    },
                    provenance=Provenance(
                        source_type=ProvenanceType.DB,
                        source_uri=str(resolved),
                        details={"type": "table_existence"},
                    ),
                )
            )

            # Column constraint claims
            for col in table["columns"]:
                col_subject = f"{subject}.{col['name']}"
                claims.append(
                    Claim(
                        id=f"db_col_{table['name']}_{col['name']}",
                        category="column",
                        subject=col_subject,
                        value={
                            "name": col["name"],
                            "type": col["type"],
                            "nullable": col["nullable"],
                            "primary_key": col["primary_key"],
                            "unique": col["unique"],
                            "default": col["default"],
                        },
                        provenance=Provenance(
                            source_type=ProvenanceType.DB,
                            source_uri=str(resolved),
                            details={"type": "column_constraint"},
                        ),
                    )
                )

            # Table-level constraint claims
            for constraint in table["constraints"]:
                claims.append(
                    Claim(
                        id=f"db_constraint_{table['name']}_{constraint['type'].lower()}",
                        category="constraint",
                        subject=subject,
                        value={"raw": constraint["raw"], "type": constraint["type"]},
                        provenance=Provenance(
                            source_type=ProvenanceType.DB,
                            source_uri=str(resolved),
                            details={"type": "table_constraint"},
                        ),
                    )
                )

        return claims
