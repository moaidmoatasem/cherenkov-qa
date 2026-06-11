# TODO: convert to pytest — complex file (>150 lines, multiple setUp/tearDown with temp dirs)
"""
Tests for Issue #195 — Semantic Chunking / RAG for Large Specs.

Validates:
- SchemaIndex builds chunk text from component schemas
- SchemaIndex caches and loads from disk
- SchemaIndex retrieves relevant schemas via cosine similarity
- SchemaIndex always unions explicit refs with retrieved schemas
- Integration with ingest pipeline when CHERENKOV_RAG_ENABLED=1
"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None
    _NUMPY_AVAILABLE = False


@unittest.skipUnless(_NUMPY_AVAILABLE, "numpy not installed — skipping SchemaIndex tests")
class TestSchemaChunking(unittest.TestCase):
    """Tests for schema chunk text building."""

    def setUp(self):
        # Import here to avoid import-order issues with mocks
        from cherenkov.rag.schema_index import SchemaIndex
        self.SchemaIndex = SchemaIndex

    def test_build_chunk_text_includes_name_and_type(self):
        text = self.SchemaIndex._build_chunk_text("UserCreate", {
            "type": "object",
            "description": "A user creation payload",
            "properties": {
                "email": {"type": "string", "description": "User email"},
                "age": {"type": "integer"},
            },
            "required": ["email"],
        })
        self.assertIn("schema: UserCreate", text)
        self.assertIn("description: A user creation payload", text)
        self.assertIn("type: object", text)
        self.assertIn("email (string): User email", text)
        self.assertIn("age (integer)", text)
        self.assertIn("required: email", text)

    def test_build_chunk_text_minimal_schema(self):
        text = self.SchemaIndex._build_chunk_text("Empty", {"type": "object"})
        self.assertIn("schema: Empty", text)
        self.assertIn("type: object", text)


@unittest.skipUnless(_NUMPY_AVAILABLE, "numpy not installed — skipping SchemaIndex tests")
class TestSchemaIndexCache(unittest.TestCase):
    """Tests for SchemaIndex disk cache."""

    def setUp(self):
        from cherenkov.rag.schema_index import SchemaIndex
        self.SchemaIndex = SchemaIndex
        self.tmpdir = tempfile.mkdtemp()

    def test_spec_hash_stable(self):
        spec = {"components": {"schemas": {"Foo": {"type": "object"}}}}
        h1 = self.SchemaIndex._get_spec_hash(spec)
        h2 = self.SchemaIndex._get_spec_hash(spec)
        self.assertEqual(h1, h2)

    def test_spec_hash_changes_on_schema_diff(self):
        spec1 = {"components": {"schemas": {"Foo": {"type": "object"}}}}
        spec2 = {"components": {"schemas": {"Bar": {"type": "string"}}}}
        h1 = self.SchemaIndex._get_spec_hash(spec1)
        h2 = self.SchemaIndex._get_spec_hash(spec2)
        self.assertNotEqual(h1, h2)

    def test_cache_write_and_load(self):
        index = self.SchemaIndex(cache_dir=self.tmpdir)
        spec = {
            "components": {
                "schemas": {
                    "Foo": {"type": "object", "properties": {"x": {"type": "string"}}},
                    "Bar": {"type": "object", "properties": {"y": {"type": "integer"}}},
                }
            }
        }
        with patch("cherenkov.rag.schema_index.embed_text") as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]
            index.index_spec(spec)
        self.assertEqual(index.count, 2)

        # Load from cache with a fresh index
        index2 = self.SchemaIndex(cache_dir=self.tmpdir)
        with patch("cherenkov.rag.schema_index.embed_text") as mock_embed:
            index2.index_spec(spec)
        self.assertEqual(index2.count, 2)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)


@unittest.skipUnless(_NUMPY_AVAILABLE, "numpy not installed — skipping SchemaIndex tests")
class TestSchemaRetrieval(unittest.TestCase):
    """Tests for RAG-based schema retrieval."""

    def setUp(self):
        from cherenkov.rag.schema_index import SchemaIndex
        self.SchemaIndex = SchemaIndex
        self.index = SchemaIndex(cache_dir=tempfile.mkdtemp())

    def test_retrieve_always_includes_explicit_refs(self):
        spec = {
            "components": {
                "schemas": {
                    "UserCreate": {"type": "object", "properties": {"email": {"type": "string"}}},
                    "UserResponse": {"type": "object", "properties": {"id": {"type": "integer"}}},
                    "Pagination": {"type": "object", "properties": {"page": {"type": "integer"}}},
                }
            }
        }
        with patch("cherenkov.rag.schema_index.embed_text") as mock_embed:
            mock_embed.side_effect = [
                [0.1, 0.2, 0.3],  # UserCreate embedding
                [0.4, 0.5, 0.6],  # UserResponse embedding
                [0.7, 0.8, 0.9],  # Pagination embedding
                [0.1, 0.2, 0.3],  # query embedding (closest to UserCreate)
            ]
            self.index.index_spec(spec)
            result = self.index.retrieve(
                query_text="create user email",
                explicit_refs={"UserResponse"},
                top_k=1,
            )
        self.assertIn("UserResponse", result, "Explicit ref must always be included")
        self.assertEqual(len(result), 2, "Should include explicit ref + top-k hit")

    def test_empty_index_returns_empty(self):
        result = self.index.retrieve("anything", top_k=5)
        self.assertEqual(result, {})

    def test_retrieve_respects_top_k(self):
        spec = {
            "components": {
                "schemas": {
                    "A": {"type": "object", "properties": {"a1": {"type": "string"}}},
                    "B": {"type": "object", "properties": {"b1": {"type": "string"}}},
                    "C": {"type": "object", "properties": {"c1": {"type": "string"}}},
                }
            }
        }
        with patch("cherenkov.rag.schema_index.embed_text") as mock_embed:
            mock_embed.side_effect = [
                [0.9, 0.1, 0.1],
                [0.1, 0.9, 0.1],
                [0.1, 0.1, 0.9],
                [0.9, 0.1, 0.1],
            ]
            self.index.index_spec(spec)
            result = self.index.retrieve("a stuff", top_k=2)
        self.assertLessEqual(len(result), 2)

    def tearDown(self):
        import shutil
        if hasattr(self, 'index') and hasattr(self.index, '_cache_dir'):
            cache_dir = self.index._cache_dir
            import shutil
            shutil.rmtree(str(cache_dir.parent), ignore_errors=True)


@unittest.skipUnless(_NUMPY_AVAILABLE, "numpy not installed — skipping SchemaIndex tests")
class TestRAGIngestIntegration(unittest.TestCase):
    """Tests that RAG enriches schemas in the ingest pipeline."""

    def setUp(self):
        self.spec = {
            "openapi": "3.1.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "summary": "Create User",
                        "operationId": "create_user",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/UserCreate"
                                    }
                                }
                            },
                            "required": True,
                        },
                        "responses": {
                            "201": {"description": "Created"},
                            "422": {"description": "Validation Error"},
                        },
                    }
                }
            },
            "components": {
                "schemas": {
                    "UserCreate": {
                        "type": "object",
                        "required": ["email", "password"],
                        "properties": {
                            "email": {"type": "string", "description": "User email"},
                            "password": {"type": "string", "description": "User password"},
                        },
                    },
                    "UserResponse": {
                        "type": "object",
                        "properties": {"id": {"type": "integer"}, "email": {"type": "string"}},
                    },
                }
            },
        }

    def test_rag_enriches_resolved_schemas(self):
        import cherenkov.stages.ingest as ingest_mod
        ingest_mod._rag_enabled = lambda: True

        from cherenkov.stages.ingest import IngestStage as IngSt

        stage = IngSt("test_rag")
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(self.spec, tmp)
        tmp.close()

        try:
            with patch("cherenkov.rag.schema_index.embed_text") as mock_embed:
                mock_embed.side_effect = [
                    [0.1, 0.2],
                    [0.3, 0.4],
                    [0.1, 0.2],
                ]
                output = stage.run(tmp.name)
            ep = output.endpoints[0]
            self.assertIn("UserCreate", ep.schemas,
                          "Depth-limited ref resolution should find UserCreate")
            self.assertIn("UserResponse", ep.schemas,
                          "RAG enrichment should add UserResponse schema")
        finally:
            os.unlink(tmp.name)
            if hasattr(IngSt, "_rag"):
                IngSt._rag = None  # reset class-level cache
            ingest_mod._rag_enabled = lambda: bool(os.getenv("CHERENKOV_RAG_ENABLED", "").lower() in ("1", "true", "yes"))


if __name__ == "__main__":
    unittest.main()
