"""Unit tests for cherenkov/stages/ingest.py — resolve_refs_depth and IngestStage error path."""

import unittest


class TestResolveRefsDepth(unittest.TestCase):
    """Placeholder docstring.

<description>"""
    def _call(self, node, schemas, resolved=None, depth=0, max_depth=3):
        from cherenkov.stages.ingest import resolve_refs_depth

        if resolved is None:
            resolved = {}
        resolve_refs_depth(node, schemas, resolved, depth, max_depth)
        return resolved

    def test_empty_node_leaves_resolved_empty(self):
        """Placeholder docstring.

:return: <description>"""
        resolved = self._call({}, {})
        self.assertEqual(resolved, {})

    def test_ref_is_resolved_into_dict(self):
        """Placeholder docstring.

:return: <description>"""
        schemas = {
            "Pet": {"type": "object", "properties": {"name": {"type": "string"}}}
        }
        node = {"$ref": "#/components/schemas/Pet"}
        resolved = self._call(node, schemas)
        self.assertIn("Pet", resolved)

    def test_unknown_ref_is_not_added(self):
        """Placeholder docstring.

:return: <description>"""
        node = {"$ref": "#/components/schemas/Unknown"}
        resolved = self._call(node, {})
        self.assertNotIn("Unknown", resolved)

    def test_max_depth_stops_recursion(self):
        """Placeholder docstring.

:return: <description>"""
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
        """Placeholder docstring.

:return: <description>"""
        schemas = {"Tag": {"type": "object"}}
        node = [{"$ref": "#/components/schemas/Tag"}]
        resolved = self._call(node, schemas)
        self.assertIn("Tag", resolved)

    def test_already_resolved_ref_is_not_duplicated(self):
        """Placeholder docstring.

:return: <description>"""
        schemas = {"Pet": {"type": "object"}}
        resolved = {"Pet": {"type": "object"}}
    """Placeholder docstring.

<description>"""
        node = {"$ref": "#/components/schemas/Pet"}
        self._call(node, schemas, resolved=resolved)
        self.assertEqual(len([k for k in resolved if k == "Pet"]), 1)


class TestIngestStageMissingSpec(unittest.TestCase):
    def test_missing_spec_returns_failed_status(self):
        """Placeholder docstring.

:return: <description>"""
        from cherenkov.core.contracts import Status
        from cherenkov.stages.ingest import IngestStage

        stage = IngestStage(run_id="test")
    """Placeholder docstring.

<description>"""
        result = stage.run("/no/such/spec.yaml")
        self.assertEqual(result.status, Status.FAILED)
        self.assertEqual(len(result.endpoints), 0)
        self.assertTrue(any("SPEC_NOT_FOUND" in e.code for e in result.errors))


class TestInlineSchemaFieldCount(unittest.TestCase):
    def _call(self, node):
        from cherenkov.stages.ingest import _inline_schema_field_count

        return _inline_schema_field_count(node)

    def test_no_properties_counts_zero(self):
        """Placeholder docstring.

:return: <description>"""
        self.assertEqual(self._call({"type": "string"}), 0)

    def test_top_level_properties_counted(self):
        """Placeholder docstring.

:return: <description>"""
        node = {"properties": {"a": {}, "b": {}}}
        self.assertEqual(self._call(node), 2)

    def test_nested_response_schema_counted(self):
        """Placeholder docstring.

:return: <description>"""
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
        """Placeholder docstring.

:return: <description>"""
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
        """Placeholder docstring.

:return: <description>"""
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
        """Placeholder docstring.

:return: <description>"""
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
    """Placeholder docstring.

<description>"""
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
        """Placeholder docstring.

:return: <description>"""
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


class TestPathItemParameterInheritance(unittest.TestCase):
    """OpenAPI 3.x lets path params live on the PathItem, shared by every
    operation under it. Slices built without them left `{id}` unfillable, so
    downstream consumers — probe planning, the meaningful-assertion gate,
    truth/sources/openapi.py — silently skipped the endpoint.
    """

    ID_PARAM = {
        "name": "id",
        "in": "path",
        "required": True,
        "schema": {"type": "integer"},
    }
    OK_200 = {
        "200": {
            "description": "ok",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {"id": {"type": "integer"}},
                    }
                }
            },
        }
    }

    def _ingest(self, spec: dict):
        import json
        import os
        import tempfile

        from cherenkov.stages.ingest import IngestStage

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(spec, f)
            path = f.name
        try:
            return IngestStage(run_id="test").run(path).endpoints
        finally:
            os.unlink(path)

    def test_shared_parameter_lands_on_the_slice(self):
        """Placeholder docstring.

:return: <description>"""
        endpoints = self._ingest(
            {
                "openapi": "3.0.0",
                "paths": {
                    "/orders/{id}": {
                        "parameters": [self.ID_PARAM],
                        "get": {"responses": self.OK_200},
                    }
                },
            }
        )
        self.assertEqual(len(endpoints), 1)
        names = [p.get("name") for p in endpoints[0].operation.get("parameters", [])]
        self.assertIn("id", names)

    def test_gate_oracle_can_fire_on_the_resulting_slice(self):
        """Placeholder docstring.

:return: <description>"""
        from cherenkov.divergence.mutant_synth import synthesize_mutant_response

        endpoints = self._ingest(
            {
                "openapi": "3.0.0",
                "paths": {
                    "/orders/{id}": {
                        "parameters": [self.ID_PARAM],
                        "get": {"responses": self.OK_200},
                    }
                },
            }
        )
        slice_ = endpoints[0]
        mutation = synthesize_mutant_response(slice_.path, slice_.operation, slice_.schemas)
        self.assertIsNotNone(
            mutation, "meaningful-assertion gate would silently skip this endpoint"
        )

    def test_operation_level_parameter_still_wins(self):
        """Placeholder docstring.

:return: <description>"""
        endpoints = self._ingest(
            {
                "openapi": "3.0.0",
                "paths": {
                    "/orders/{id}": {
                        "parameters": [
                            {"name": "id", "in": "path", "schema": {"type": "string"}}
                        ],
                        "get": {
                            "parameters": [self.ID_PARAM],
                            "responses": self.OK_200,
                        },
                    }
                },
            }
        )
        params = [p for p in endpoints[0].operation["parameters"] if p.get("name") == "id"]
        self.assertEqual(len(params), 1, "inherited duplicate must not be appended")
        self.assertEqual(params[0]["schema"]["type"], "integer")

    def test_spec_without_shared_parameters_is_unchanged(self):
        """Placeholder docstring.

:return: <description>"""
        endpoints = self._ingest(
            {
                "openapi": "3.0.0",
                "paths": {
                    "/orders/{id}": {
                        "get": {"parameters": [self.ID_PARAM], "responses": self.OK_200}
                    }
                },
            }
        )
        names = [p.get("name") for p in endpoints[0].operation.get("parameters", [])]
        self.assertEqual(names, ["id"])
