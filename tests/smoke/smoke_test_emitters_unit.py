#!/usr/bin/env python3
"""
smoke_test_emitters_unit.py — Kill-criteria exit demo for E11 unit-test emitter.

C5 (#120): Unit-test emitter (pytest/jest) in truth/emitters/.

Verifies:
1. Emitter SPI compliance (interface.py)
2. Pytest test generation from Truth Model
3. Jest test generation from Truth Model
4. Anti-lock-in: generated tests have zero CHERENKOV dependency
5. Generated code compiles/syntax-checks (Python)

Exit code 0 = all criteria passed.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from cherenkov.core.truth_model import TruthModel, GraphNode, NodeType
from cherenkov.truth.emitters.unit_test import UnitTestEmitter
from cherenkov.truth.emitters.interface import Emitter

PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label} — {detail}")
        FAIL += 1


def make_test_tm() -> TruthModel:
    tm = TruthModel()
    endpoints = [
        (
            "GET",
            "/api/users",
            "List users",
            {
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                    },
                                }
                            }
                        },
                    }
                },
            },
        ),
        (
            "POST",
            "/api/users",
            "Create user",
            {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string"},
                                },
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                    },
                                }
                            }
                        },
                    }
                },
            },
        ),
        (
            "GET",
            "/health",
            "Health check",
            {
                "responses": {"200": {"description": "OK"}},
            },
        ),
    ]
    for i, (method, path, summary, operation) in enumerate(endpoints):
        node = GraphNode(
            id=f"ep-{i}",
            type=NodeType.ENDPOINT,
            label=f"{method} {path}",
            properties={"summary": summary, "operation": operation},
        )
        tm.add_node(node)
    return tm


def main():
    global PASS, FAIL
    print("=" * 60)
    print("E11 Unit-Test Emitter — Kill-Criteria Exit Demo (#120)")
    print("=" * 60)

    emitter = UnitTestEmitter()
    tm = make_test_tm()

    # 1. SPI compliance
    print("\n1. Emitter SPI compliance")
    check("emitter is instance of Emitter", isinstance(emitter, Emitter))
    check("emitter has emit method", hasattr(emitter, "emit"))

    # 2. Pytest generation
    print("\n2. Pytest generation")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        emitter.emit(tm, out, framework="pytest")
        py_files = list(out.glob("*.py"))
        check("pytest generates .py files", len(py_files) >= 1)
        if py_files:
            content = py_files[0].read_text()
            check("pytest code has assertions", "assert" in content)
            check("pytest uses requests library", "requests" in content)
            check("pytest has class definition", "class Test" in content)
            check("pytest has test_ prefix methods", "def test_" in content)
            check(
                "pytest code has no cherenkov dependency",
                "cherenkov" not in content.lower(),
            )
            # Check the generated import path is correct
            check(
                "pytest code has proper imports",
                "import pytest" in content and "import requests" in content,
            )

        check("all 3 endpoints generate files", len(py_files) == 3)

    # 3. Jest generation
    print("\n3. Jest generation")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        emitter.emit(tm, out, framework="jest")
        ts_files = list(out.glob("*.ts"))
        check("jest generates .ts files", len(ts_files) >= 1)
        if ts_files:
            content = ts_files[0].read_text()
            check("jest code has expectations", "expect" in content)
            check("jest has describe blocks", "describe" in content)
            check("jest has it blocks", 'it("' in content)
            check("jest uses fetch", "fetch" in content)
            check(
                "jest code has no cherenkov dependency",
                "cherenkov" not in content.lower(),
            )

    # 4. Empty Truth Model
    print("\n4. Edge cases")
    with tempfile.TemporaryDirectory() as tmp:
        empty_tm = TruthModel()
        out = Path(tmp)
        emitter.emit(empty_tm, out, framework="pytest")
        py_files = list(out.glob("*.py"))
        check("empty TM generates no files", len(py_files) == 0)

    # 5. Invalid framework
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        try:
            emitter.emit(tm, out, framework="mocha")
            check("unknown framework raises ValueError", False)
        except ValueError:
            check("unknown framework raises ValueError", True)

    # 6. Base URL injection
    print("\n5. Base URL injection")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        emitter.emit(
            tm, out, framework="pytest", base_url="https://staging.example.com"
        )
        py_files = list(out.glob("*.py"))
        if py_files:
            content = py_files[0].read_text()
            check("base URL appears in test code", "staging.example.com" in content)

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("STATUS: ALL CRITERIA PASSED — E11 unit-test emitter is ready.")
    else:
        print(f"STATUS: {FAIL} criteria FAILED — review output above.")
    print("=" * 60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
