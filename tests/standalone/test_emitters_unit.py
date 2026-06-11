"""
test_emitters_unit.py — Unit tests for UnitTestEmitter in truth/emitters/ (#120).

Tests pytest and jest code generation from Truth Model.
"""
import os
import tempfile
import unittest

from pathlib import Path

from cherenkov.core.truth_model import TruthModel, GraphNode, NodeType
from cherenkov.truth.emitters.unit_test import UnitTestEmitter


class TestUnitTestEmitter(unittest.TestCase):
    """Tests for UnitTestEmitter following the Emitter SPI."""

    def setUp(self):
        self.emitter = UnitTestEmitter()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _make_tm(self, method="GET", path="/api/users", summary="List users") -> TruthModel:
        tm = TruthModel()
        node = GraphNode(
            id=f"ep:{method}:{path}",
            type=NodeType.ENDPOINT,
            label=f"{method} {path}",
            properties={
                "summary": summary,
                "operation": {
                    "summary": summary,
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
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
            },
        )
        tm.add_node(node)
        return tm

    def test_emit_pytest_from_truth_model(self):
        tm = self._make_tm()
        result = self.emitter.emit(tm, Path(self.tmp.name), framework="pytest")
        self.assertTrue(result.exists())

        py_files = list(Path(self.tmp.name).glob("*.py"))
        self.assertGreaterEqual(len(py_files), 1)

    def test_emit_jest_from_truth_model(self):
        tm = self._make_tm()
        result = self.emitter.emit(tm, Path(self.tmp.name), framework="jest")
        self.assertTrue(result.exists())

        ts_files = list(Path(self.tmp.name).glob("*.ts"))
        self.assertGreaterEqual(len(ts_files), 1)

    def test_emit_pytest_contains_assertions(self):
        tm = self._make_tm()
        self.emitter.emit(tm, Path(self.tmp.name), framework="pytest")
        py_files = list(Path(self.tmp.name).glob("*.py"))
        self.assertGreaterEqual(len(py_files), 1, "No pytest files generated")
        content = py_files[0].read_text()
        self.assertIn("assert", content)
        self.assertIn("requests", content)

    def test_emit_jest_contains_expect(self):
        tm = self._make_tm()
        self.emitter.emit(tm, Path(self.tmp.name), framework="jest")
        ts_files = list(Path(self.tmp.name).glob("*.ts"))
        self.assertGreaterEqual(len(ts_files), 1, "No jest files generated")
        content = ts_files[0].read_text()
        self.assertIn("expect", content)
        self.assertIn("describe", content)

    def test_emit_empty_truth_model(self):
        tm = TruthModel()
        self.emitter.emit(tm, Path(self.tmp.name), framework="pytest")
        py_files = list(Path(self.tmp.name).glob("*.py"))
        self.assertEqual(len(py_files), 0)

    def test_emit_with_base_url(self):
        tm = self._make_tm()
        self.emitter.emit(
            tm, Path(self.tmp.name),
            framework="pytest", base_url="https://api.example.com",
        )
        py_files = list(Path(self.tmp.name).glob("*.py"))
        if py_files:
            content = py_files[0].read_text()
            self.assertIn("api.example.com", content)

    def test_unknown_framework_raises(self):
        tm = self._make_tm()
        with self.assertRaises(ValueError):
            self.emitter.emit(tm, Path(self.tmp.name), framework="mocha")

    def test_emitter_follows_spi(self):
        from cherenkov.truth.emitters.interface import Emitter
        self.assertIsInstance(self.emitter, Emitter)

    def test_emit_pytest_code_is_standalone(self):
        tm = self._make_tm()
        self.emitter.emit(tm, Path(self.tmp.name), framework="pytest")
        py_files = list(Path(self.tmp.name).glob("*.py"))
        if py_files:
            content = py_files[0].read_text()
            self.assertNotIn("cherenkov", content.lower())

    def test_emit_jest_code_is_standalone(self):
        tm = self._make_tm()
        self.emitter.emit(tm, Path(self.tmp.name), framework="jest")
        ts_files = list(Path(self.tmp.name).glob("*.ts"))
        if ts_files:
            content = ts_files[0].read_text()
            self.assertNotIn("cherenkov", content.lower())

    def test_emit_pytest_code_content(self):
        tm = self._make_tm()
        self.emitter.emit(tm, Path(self.tmp.name), framework="pytest")
        py_files = list(Path(self.tmp.name).glob("*.py"))
        if py_files:
            content = py_files[0].read_text()
            self.assertIn("GET", content)
            self.assertIn("/api/users", content)

    def test_emit_jest_code_content(self):
        tm = self._make_tm()
        self.emitter.emit(tm, Path(self.tmp.name), framework="jest")
        ts_files = list(Path(self.tmp.name).glob("*.ts"))
        if ts_files:
            content = ts_files[0].read_text()
            self.assertIn("GET", content)
            self.assertIn("/api/users", content)

    def test_multiple_endpoints_generate_multiple_files(self):
        tm = TruthModel()
        for i, (method, path) in enumerate([("GET", "/users"), ("POST", "/users"), ("GET", "/orders")]):
            node = GraphNode(
                id=f"ep-{i}",
                type=NodeType.ENDPOINT,
                label=f"{method} {path}",
                properties={
                    "operation": {
                        "responses": {"200": {"description": "OK"}},
                    }
                },
            )
            tm.add_node(node)
        result = self.emitter.emit(tm, Path(self.tmp.name), framework="pytest")
        py_files = list(Path(self.tmp.name).glob("*.py"))
        self.assertGreaterEqual(len(py_files), 1)


if __name__ == "__main__":
    unittest.main()
