"""cherenkov/synthetic/merge.py — Merge and deduplicate persona test suites.

Analogous to STORM's information aggregation step where parallel conversation
outputs are consolidated into a single InformationTable.
"""

from __future__ import annotations

from typing import Any


def merge_suites(suites: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Merge multiple persona suites into one, deduplicating by test name.

    Each persona namespaces its test names (e.g. ``happy_path_listPets``),
    so collisions are rare. The dedup guard handles any edge cases.
    """
    merged: dict[str, list[dict[str, Any]]] = {}
    seen: dict[str, set[str]] = {}

    for suite in suites:
        for op_id, tests in suite.items():
            if not isinstance(tests, list):
                continue
            if op_id not in merged:
                merged[op_id] = []
                seen[op_id] = set()
            for test in tests:
                if not isinstance(test, dict):
                    continue
                name = test.get("name", "")
                if name not in seen[op_id]:
                    merged[op_id].append(test)
                    seen[op_id].add(name)

    return merged
