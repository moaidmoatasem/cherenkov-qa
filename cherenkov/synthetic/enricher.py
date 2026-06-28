"""cherenkov/synthetic/enricher.py — Assertion enrichment (polishing pass).

Analogous to STORM's ArticlePolishingModule: takes the merged suite and
promotes under-asserted tests by injecting Content-Type and json_key
assertions where the spec tells us they should exist.
"""

from __future__ import annotations

from typing import Any


def enrich_suite(
    suite: dict[str, list[dict[str, Any]]],
    spec: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Polish a merged suite by enriching under-asserted tests.

    For each test that expects a 2xx response and has fewer than 3 assertions:
    - Add ``Content-Type: json`` header assertion if absent.
    - Add ``json_key`` assertion for the first declared response field if absent.
    """
    from cherenkov.synthetic.personas import build_spec_contexts

    contexts = build_spec_contexts(spec)
    result: dict[str, list[dict[str, Any]]] = {}

    for op_id, tests in suite.items():
        if not isinstance(tests, list):
            result[op_id] = tests
            continue

        ctx = contexts.get(op_id)
        enriched: list[dict[str, Any]] = []

        for test in tests:
            assertions: list[dict[str, Any]] = list(test.get("assertions", []))

            status_a = next((a for a in assertions if a.get("type") == "status"), None)
            expects_2xx = status_a and any(
                isinstance(c, int) and c < 300 for c in status_a.get("expected", [])
            )

            if expects_2xx and len(assertions) < 3:
                has_ct = any(
                    a.get("type") == "header" and "Content-Type" in a.get("name", "")
                    for a in assertions
                )
                has_jk = any(a.get("type") == "json_key" for a in assertions)

                if not has_ct:
                    assertions.append({
                        "type": "header",
                        "name": "Content-Type",
                        "contains": "json",
                    })
                if not has_jk and ctx and ctx.response_fields:
                    assertions.append({
                        "type": "json_key",
                        "field": ctx.response_fields[0],
                        "exists": True,
                    })

            enriched.append({**test, "assertions": assertions})

        result[op_id] = enriched

    return result
