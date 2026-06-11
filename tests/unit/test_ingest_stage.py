"""Unit tests for cherenkov/stages/ingest.py — resolve_refs_depth and IngestStage error path."""
import unittest


class TestResolveRefsDepth(unittest.TestCase):
    def _call(self, node, schemas, resolved=None, depth=0, max_depth=3):
        from cherenkov.stages.ingest import resolve_refs_depth
        if resolved is None:
            resolved = {}
        resolve_refs_depth(node, schemas, resolved, depth, max_depth)
        return resolved

    def test_empty_node_leaves_resolved_empty(self):
        resolved = self._call({}, {})
        self.assertEqual(resolved, {})

    def test_ref_is_resolved_into_dict(self):
        schemas = {"Pet": {"type": "object", "properties": {"name": {"type": "string"}}}}
        node = {"$ref": "#/components/schemas/Pet"}
        resolved = self._call(node, schemas)
        self.assertIn("Pet", resolved)

    def test_unknown_ref_is_not_added(self):
        node = {"$ref": "#/components/schemas/Unknown"}
        resolved = self._call(node, {})
        self.assertNotIn("Unknown", resolved)

    def test_max_depth_stops_recursion(self):
        schemas = {
            "A": {"$ref": "#/components/schemas/B"},
            "B": {"$ref": "#/components/schemas/C"},
            "C": {"type": "string"},
        }
        node = {"$ref": "#/components/schemas/A"}
        resolved = self._call(node, schemas, max_depth=1)
        self.assertIn("A", resolved)
        self.assertNotIn("C", resolved)

    def test_list_nodes_are_traversed(self):
        schemas = {"Tag": {"type": "object"}}
        node = [{"$ref": "#/components/schemas/Tag"}]
        resolved = self._call(node, schemas)
        self.assertIn("Tag", resolved)

    def test_already_resolved_ref_is_not_duplicated(self):
        schemas = {"Pet": {"type": "object"}}
        resolved = {"Pet": {"type": "object"}}
        node = {"$ref": "#/components/schemas/Pet"}
        self._call(node, schemas, resolved=resolved)
        self.assertEqual(len([k for k in resolved if k == "Pet"]), 1)


class TestIngestStageMissingSpec(unittest.TestCase):
    def test_missing_spec_returns_failed_status(self):
        from cherenkov.stages.ingest import IngestStage
        from cherenkov.core.contracts import Status
        stage = IngestStage(run_id="test")
        result = stage.run("/no/such/spec.yaml")
        self.assertEqual(result.status, Status.FAILED)
        self.assertEqual(len(result.endpoints), 0)
        self.assertTrue(any("SPEC_NOT_FOUND" in e.code for e in result.errors))
