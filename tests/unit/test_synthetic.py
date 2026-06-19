"""Tests for the synthetic data generator."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from cherenkov.synthetic.generator import (
    GenerationStrategy,
    SyntheticDataGenerator,
    generate_from_schema,
    generate_from_spec,
)
from cherenkov.synthetic.runner import generate_for_endpoints


@pytest.fixture
def simple_schema() -> dict:
    """A simple JSON schema for a user object."""
    return {
        "type": "object",
        "properties": {
            "id": {"type": "integer", "minimum": 1, "maximum": 99999},
            "name": {"type": "string"},
            "email": {"type": "string"},
            "age": {"type": "integer", "minimum": 0, "maximum": 150},
            "is_active": {"type": "boolean"},
        },
        "required": ["id", "name", "email"],
    }


@pytest.fixture
def spec_file(tmp_path: Path) -> Path:
    """Create a sample OpenAPI spec YAML file."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "User list",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    }
                },
                "post": {
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
                                            "name": {"type": "string"},
                                            "email": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
            }
        },
    }
    path = tmp_path / "test_spec.yaml"
    path.write_text(yaml.dump(spec))
    return path


class TestSyntheticDataGenerator:
    """Tests for SyntheticDataGenerator."""

    def test_generate_object(self, simple_schema: dict):
        """Generate an object from schema."""
        gen = SyntheticDataGenerator(GenerationStrategy.RANDOM)
        result = gen.generate(simple_schema)
        assert isinstance(result, dict)
        assert "id" in result
        assert "name" in result
        assert "email" in result
        assert isinstance(result["id"], int)
        assert isinstance(result["name"], str)
        assert isinstance(result["is_active"], bool)

    def test_generate_string_enum(self):
        """Generate a string with enum constraint."""
        schema = {
            "type": "string",
            "enum": ["admin", "user", "viewer"],
        }
        gen = SyntheticDataGenerator()
        result = gen.generate(schema)
        assert result in ["admin", "user", "viewer"]

    def test_generate_integer_with_range(self):
        """Generate an integer within range."""
        schema = {"type": "integer", "minimum": 10, "maximum": 20}
        gen = SyntheticDataGenerator()
        for _ in range(20):
            result = gen.generate(schema)
            assert 10 <= result <= 20

    def test_generate_boolean(self):
        """Generate a boolean value."""
        schema = {"type": "boolean"}
        gen = SyntheticDataGenerator()
        values = {gen.generate(schema) for _ in range(10)}
        assert values.issubset({True, False})

    def test_generate_array(self):
        """Generate an array of strings."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 3,
        }
        gen = SyntheticDataGenerator()
        result = gen.generate(schema)
        assert isinstance(result, list)
        assert 1 <= len(result) <= 3
        assert all(isinstance(item, str) for item in result)

    def test_generate_uuid_heuristic(self):
        """Generate a UUID for fields named 'id'."""
        schema = {"type": "string"}
        gen = SyntheticDataGenerator()
        result = gen.generate(schema, field_path="uuid")
        # UUID format check
        assert "-" in result

    def test_generate_email_heuristic(self):
        """Generate an email for fields named 'email'."""
        schema = {"type": "string"}
        gen = SyntheticDataGenerator()
        result = gen.generate(schema, field_path="email")
        assert "@" in result
        assert ".com" in result or ".org" in result

    def test_seed_overrides(self):
        """Seed specific values for determinism."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
            },
        }
        gen = SyntheticDataGenerator()
        gen.seed({"name": "TestUser", "email": "test@example.com"})
        result = gen.generate(schema)
        assert result["name"] == "TestUser"
        assert result["email"] == "test@example.com"

    def test_single_function(self, simple_schema: dict):
        """Test the convenience generate_from_schema function."""
        result = generate_from_schema(simple_schema)
        assert isinstance(result, dict)
        assert "id" in result

    def test_generate_from_spec(self, spec_file: Path):
        """Generate data from a full OpenAPI spec."""
        result = generate_from_spec(str(spec_file), max_endpoints=5)
        assert "GET /users" in result
        assert "POST /users" in result
        get_data = result["GET /users"]
        assert any(k.startswith("response_") for k in get_data)
        post_data = result["POST /users"]
        assert "request_body" in post_data or any(k.startswith("response_") for k in post_data)

    def test_generate_nested_object(self):
        """Generate nested object structures."""
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "profile": {
                            "type": "object",
                            "properties": {
                                "bio": {"type": "string"},
                            },
                        }
                    },
                }
            },
        }
        gen = SyntheticDataGenerator()
        result = gen.generate(schema)
        assert isinstance(result["user"]["profile"]["bio"], str)


class TestSyntheticRunner:
    """Tests for the synthetic data runner."""

    def test_generate_for_endpoints(self, spec_file: Path):
        """Test the runner with a spec file."""
        report = generate_for_endpoints(str(spec_file), max_endpoints=5)
        assert report.endpoint_count > 0
        assert report.field_count > 0
        assert report.generated_samples > 0
        assert report.strategy == "random"

    def test_generate_with_output(self, spec_file: Path, tmp_path: Path):
        """Test writing output to a file."""
        output = tmp_path / "synthetic_output.json"
        report = generate_for_endpoints(str(spec_file), output_path=str(output))
        assert output.exists()
        content = json.loads(output.read_text())
        assert "report" in content
        assert "data" in content
