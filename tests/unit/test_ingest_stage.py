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
        schemas = {
            "Pet": {"type": "object", "properties": {"name": {"type": "string"}}}
        }
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
        from cherenkov.core.contracts import Status
        from cherenkov.stages.ingest import IngestStage

        stage = IngestStage(run_id="test")
        result = stage.run("/no/such/spec.yaml")
        self.assertEqual(result.status, Status.FAILED)
        self.assertEqual(len(result.endpoints), 0)
        self.assertTrue(any("SPEC_NOT_FOUND" in e.code for e in result.errors))


class TestInlineSchemaFieldCount(unittest.TestCase):
    def _call(self, node):
        from cherenkov.stages.ingest import _inline_schema_field_count

        return _inline_schema_field_count(node)

    def test_no_properties_counts_zero(self):
        self.assertEqual(self._call({"type": "string"}), 0)

    def test_top_level_properties_counted(self):
        node = {"properties": {"a": {}, "b": {}}}
        self.assertEqual(self._call(node), 2)

    def test_nested_response_schema_counted(self):
        # Mirrors an operation dict with an inline (non-$ref) response schema.
        node = {
            "responses": {
                "200": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"id": {}, "total": {}, "status": {}},
                            }
                        }
                    }
                }
            }
        }
        self.assertEqual(self._call(node), 3)

    def test_list_nodes_are_traversed(self):
        node = [{"properties": {"a": {}}}, {"properties": {"b": {}, "c": {}}}]
        self.assertEqual(self._call(node), 3)


class TestIngestStageRichness(unittest.TestCase):
    """Regression: an endpoint with a real, typed inline response schema must
    not be dropped as 'low richness' just because it doesn't use a named
    $ref to components.schemas.
    """

    def _run(self, yaml_content: str):
        import os
        import tempfile

        from cherenkov.stages.ingest import IngestStage

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(yaml_content)
            path = f.name
        try:
            return IngestStage(run_id="test").run(path)
        finally:
            os.unlink(path)

    def test_inline_response_schema_is_not_skipped_as_low_richness(self):
        from cherenkov.core.contracts import Status

        result = self._run(
            """
openapi: "3.0.0"
info:
  title: Orders API
  version: "1.0"
paths:
  /orders/{id}:
    get:
      summary: Get an order by id
      responses:
        "200":
          description: The order
          content:
            application/json:
              schema:
                type: object
                required: [id, total, status]
                properties:
                  id:
                    type: integer
                  total:
                    type: number
                  status:
                    type: string
        "404":
          description: Not found
"""
        )
        self.assertNotEqual(result.status, Status.DEGRADED)
        self.assertEqual(len(result.endpoints), 1)
        self.assertFalse(any(e.code == "LOW_RICHNESS" for e in result.errors))

    def test_path_level_parameters_counted_toward_richness(self):
        # A shared path-level `id` parameter plus a nontrivial response body
        # should be enough to clear the richness floor even without any
        # operation-level `parameters` key.
        from cherenkov.core.contracts import Status

        result = self._run(
            """
openapi: "3.0.0"
info:
  title: Items API
  version: "1.0"
paths:
  /items/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: integer
    get:
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: integer
                  name:
                    type: string
"""
        )
        self.assertNotEqual(result.status, Status.DEGRADED)
        self.assertEqual(len(result.endpoints), 1)


class TestIngestStageYAML(unittest.TestCase):
    def test_yaml_spec_parses_successfully(self):
        import os
        import tempfile

        from cherenkov.core.contracts import Status
        from cherenkov.stages.ingest import IngestStage

        yaml_content = """
openapi: "3.0.0"
info:
  title: Test
  version: "1.0"
paths:
  /health:
    get:
      parameters:
        - name: verbose
          in: query
          schema:
            type: string
        - name: format
          in: query
          schema:
            type: string
      responses:
        "200":
          description: OK
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(yaml_content)
            path = f.name
        try:
            stage = IngestStage(run_id="test")
            result = stage.run(path)
            self.assertNotEqual(result.status, Status.FAILED)
            self.assertGreater(len(result.endpoints), 0)
            self.assertEqual(result.endpoints[0].path, "/health")
            self.assertEqual(result.endpoints[0].method, "GET")
        finally:
            os.unlink(path)
