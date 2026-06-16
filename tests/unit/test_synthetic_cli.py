"""Tests for the synthetic CLI command."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from cherenkov.synthetic.cmd import synthetic_cmd


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
                }
            }
        },
    }
    path = tmp_path / "test_spec.yaml"
    path.write_text(yaml.dump(spec))
    return path


class TestSyntheticCLI:
    def test_synthetic_command_help(self):
        """Test that the synthetic command help works."""
        runner = CliRunner()
        result = runner.invoke(synthetic_cmd, ["--help"])
        assert result.exit_code == 0
        assert "Generate synthetic test data" in result.output
        assert "SPEC_PATH" in result.output

    def test_synthetic_command_default(self, spec_file: Path):
        """Test running synthetic generation with default options."""
        runner = CliRunner()
        result = runner.invoke(synthetic_cmd, [str(spec_file)])
        assert result.exit_code == 0, result.output
        assert "Synthetic Data Generation Complete" in result.output
        assert "Endpoints:" in result.output

    def test_synthetic_command_strategy_flag(self, spec_file: Path):
        """Test the --strategy flag."""
        runner = CliRunner()
        result = runner.invoke(synthetic_cmd, [str(spec_file), "--strategy", "random"])
        assert result.exit_code == 0
        assert "random" in result.output.lower()

    def test_synthetic_command_with_output(self, spec_file: Path, tmp_path: Path):
        """Test writing output to a file."""
        output = tmp_path / "out.json"
        runner = CliRunner()
        result = runner.invoke(synthetic_cmd, [str(spec_file), "--output", str(output)])
        assert result.exit_code == 0
        assert output.exists()

    def test_synthetic_command_nonexistent_spec(self):
        """Test with a nonexistent spec file."""
        runner = CliRunner()
        result = runner.invoke(synthetic_cmd, ["/nonexistent/spec.yaml"])
        assert result.exit_code != 0
