"""Tests for E4-1 and E4-2: Artifact Emitters."""
import unittest
import tempfile
from pathlib import Path

from cherenkov.core.truth_model import TruthModel, GraphNode, NodeType
from cherenkov.truth.emitters.interface import Emitter
from cherenkov.truth.emitters.playwright import PlaywrightEmitter
from cherenkov.truth.emitters.spec_patch import SpecPatchEmitter
from cherenkov.truth.emitters.pr_comment import PRCommentEmitter


class TestEmitterInterface(unittest.TestCase):
    def test_interface_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            Emitter()


class TestPlaywrightEmitter(unittest.TestCase):
    def setUp(self):
        self.emitter = PlaywrightEmitter()
        self.tm = TruthModel()
        node = GraphNode(
            id="ep-1",
            type=NodeType.ENDPOINT,
            label="GET /api/users",
        )
        self.tm.add_node(node)

    def test_emit_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.emitter.emit(self.tm, Path(tmp))
            self.assertTrue(result.exists())
            content = result.read_text(encoding="utf-8")
            self.assertIn("playwright", content)

    def test_emit_empty_tm(self):
        empty_tm = TruthModel()
        with tempfile.TemporaryDirectory() as tmp:
            result = self.emitter.emit(empty_tm, Path(tmp))
            self.assertTrue(result.exists())


class TestSpecPatchEmitter(unittest.TestCase):
    def setUp(self):
        self.emitter = SpecPatchEmitter()
        self.tm = TruthModel()

    def test_emit_no_divergences(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "patch.diff"
            result = self.emitter.emit(self.tm, output)
            content = result.read_text(encoding="utf-8")
            self.assertEqual(content, "")

    def test_emit_creates_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "patch.diff"
            result = self.emitter.emit(self.tm, output, divergences=[])
            self.assertTrue(result.exists())


class TestPRCommentEmitter(unittest.TestCase):
    def setUp(self):
        self.emitter = PRCommentEmitter()
        self.tm = TruthModel()

    def test_emit_no_divergences(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "comment.md"
            result = self.emitter.emit(self.tm, output)
            content = result.read_text(encoding="utf-8")
            self.assertIn("CHERENKOV Divergence Report", content)
            self.assertIn("No divergences detected", content)

    def test_emit_with_divergences_creates_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "comment.md"
            result = self.emitter.emit(self.tm, output, divergences=[])
            content = result.read_text(encoding="utf-8")
            self.assertIn("| Endpoint | Divergence | Severity", content)


if __name__ == "__main__":
    unittest.main()
