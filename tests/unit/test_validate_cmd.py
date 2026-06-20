"""
Unit tests for cherenkov/cli/commands/validate.py

Covers the gRPC / GraphQL generation paths and the human-readable
summary that is now always emitted regardless of source type.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cherenkov.cli.commands.validate import validate_cmd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROTO_CONTENT = """\
syntax = "proto3";
service Greeter {
  rpc SayHello (HelloRequest) returns (HelloReply);
}
message HelloRequest { string name = 1; }
message HelloReply { string message = 1; }
"""

GQL_CONTENT = """\
type Query {
  user(id: ID!): User
}
type User { id: ID name: String }
"""


def _mock_results(passed=2, total=2):
    reports = [
        {"scenario_id": f"scenario_{i}", "passed": i < passed, "error": "" if i < passed else "timeout"}
        for i in range(total)
    ]
    return {"status": "done", "reports": reports}


# ---------------------------------------------------------------------------
# Shared mocks
# ---------------------------------------------------------------------------

@pytest.fixture()
def runner():
    return CliRunner()


def _patch_engine(passed=2, total=2):
    engine = MagicMock()
    engine.validate_suite.return_value = _mock_results(passed, total)
    return engine


# ---------------------------------------------------------------------------
# gRPC path
# ---------------------------------------------------------------------------

class TestValidateCmdGRPC:
    def test_requires_spec(self, runner):
        result = runner.invoke(validate_cmd, ["--target", "http://localhost:9000", "--source", "grpc"])
        assert result.exit_code != 0
        assert "required" in result.output.lower() or "error" in result.output.lower()

    def test_grpc_happy_path(self, runner, tmp_path):
        proto = tmp_path / "service.proto"
        proto.write_text(PROTO_CONTENT)

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run") as mock_gen,
        ):
            MockEngine.return_value = _patch_engine()
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:9000",
                "--source", "grpc",
                "--spec", str(proto),
            ])

        assert result.exit_code == 0
        assert "Ingesting gRPC proto" in result.output
        assert "services" in result.output
        assert "Generated" in result.output

    def test_grpc_shows_results_summary(self, runner, tmp_path):
        proto = tmp_path / "service.proto"
        proto.write_text(PROTO_CONTENT)

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            MockEngine.return_value = _patch_engine(passed=1, total=2)
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:9000",
                "--source", "grpc",
                "--spec", str(proto),
            ])

        assert "Results:" in result.output
        assert "1/2" in result.output

    def test_grpc_fail_on_drift(self, runner, tmp_path):
        proto = tmp_path / "service.proto"
        proto.write_text(PROTO_CONTENT)

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            MockEngine.return_value = _patch_engine(passed=0, total=2)
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:9000",
                "--source", "grpc",
                "--spec", str(proto),
                "--fail-on-drift",
            ])

        assert result.exit_code == 1

    def test_grpc_generation_error_is_warned_not_fatal(self, runner, tmp_path):
        proto = tmp_path / "service.proto"
        proto.write_text(PROTO_CONTENT)

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run", side_effect=RuntimeError("template missing")),
        ):
            MockEngine.return_value = _patch_engine()
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:9000",
                "--source", "grpc",
                "--spec", str(proto),
            ])

        assert result.exit_code == 0
        assert "warn" in result.output.lower()


# ---------------------------------------------------------------------------
# GraphQL path
# ---------------------------------------------------------------------------

class TestValidateCmdGraphQL:
    def test_requires_spec(self, runner):
        result = runner.invoke(validate_cmd, ["--target", "http://localhost:4000", "--source", "graphql"])
        assert result.exit_code != 0
        assert "required" in result.output.lower() or "error" in result.output.lower()

    def test_graphql_happy_path(self, runner, tmp_path):
        schema = tmp_path / "schema.graphql"
        schema.write_text(GQL_CONTENT)

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            MockEngine.return_value = _patch_engine()
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "graphql",
                "--spec", str(schema),
            ])

        assert result.exit_code == 0
        assert "Ingesting GraphQL SDL" in result.output
        assert "operations" in result.output

    def test_graphql_shows_results_summary(self, runner, tmp_path):
        schema = tmp_path / "schema.graphql"
        schema.write_text(GQL_CONTENT)

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            MockEngine.return_value = _patch_engine(passed=2, total=2)
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "graphql",
                "--spec", str(schema),
            ])

        assert "Results:" in result.output
        assert "2/2" in result.output

    def test_graphql_json_summary_written(self, runner, tmp_path):
        schema = tmp_path / "schema.graphql"
        schema.write_text(GQL_CONTENT)
        out = tmp_path / "summary.json"

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            MockEngine.return_value = _patch_engine()
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "graphql",
                "--spec", str(schema),
                "--json-summary", str(out),
            ])

        assert result.exit_code == 0
        data = json.loads(out.read_text())
        assert "total_tests" in data
        assert "passed" in data


# ---------------------------------------------------------------------------
# Summary output (source-agnostic)
# ---------------------------------------------------------------------------

class TestValidateSummaryOutput:
    def test_always_prints_results_line(self, runner, tmp_path):
        schema = tmp_path / "schema.graphql"
        schema.write_text(GQL_CONTENT)

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            MockEngine.return_value.validate_suite.return_value = _mock_results(passed=2, total=2)
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "graphql",
                "--spec", str(schema),
            ])

        assert "Results:" in result.output

    def test_failed_scenarios_are_listed(self, runner, tmp_path):
        schema = tmp_path / "schema.graphql"
        schema.write_text(GQL_CONTENT)

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            mock_results = {
                "status": "done",
                "reports": [
                    {"scenario_id": "user_happy_path", "passed": False, "error": "connection refused"},
                ],
            }
            MockEngine.return_value.validate_suite.return_value = mock_results
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "graphql",
                "--spec", str(schema),
            ])

        assert "FAIL" in result.output
        assert "user_happy_path" in result.output
