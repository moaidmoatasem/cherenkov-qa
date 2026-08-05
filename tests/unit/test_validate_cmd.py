"""
Unit tests for cherenkov/cli/commands/validate.py

Covers the gRPC / GraphQL generation paths and the human-readable
summary that is now always emitted regardless of source type.
"""

import json
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
            patch("cherenkov.stages.generate.GenerateStage.run") as _mock_gen,
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
# Tightening suggestions (--verbose)
# ---------------------------------------------------------------------------

class TestValidateVerboseTighteningSuggestions:
    """Regression (#891): ValidationEngine.validate_suite() already computes
    per-scenario tightening suggestions via TighteningAnalyzer, but
    validate_cmd's --verbose loop never echoed them to stdout — so
    "consider -> ..." could never appear no matter how a run was scoped."""

    def test_suggestions_printed_for_passed_scenario(self, runner, tmp_path):
        schema = tmp_path / "schema.graphql"
        schema.write_text(GQL_CONTENT)

        mock_results = {
            "status": "success",
            "reports": [
                {
                    "scenario_id": "demo_tighten",
                    "passed": True,
                    "error": "",
                    "suggestions": [
                        "expect(data.email).toBe('test@example.com')",
                        "expect(data.email).toBe(body.email)",
                    ],
                },
            ],
        }

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            MockEngine.return_value.validate_suite.return_value = mock_results
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "graphql",
                "--spec", str(schema),
                "--verbose",
            ])

        assert "consider -> expect(data.email).toBe('test@example.com')" in result.output
        assert "consider -> expect(data.email).toBe(body.email)" in result.output

    def test_no_suggestions_line_without_verbose(self, runner, tmp_path):
        schema = tmp_path / "schema.graphql"
        schema.write_text(GQL_CONTENT)

        mock_results = {
            "status": "success",
            "reports": [
                {
                    "scenario_id": "demo_tighten",
                    "passed": True,
                    "error": "",
                    "suggestions": ["expect(data.email).toBe('test@example.com')"],
                },
            ],
        }

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            MockEngine.return_value.validate_suite.return_value = mock_results
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "graphql",
                "--spec", str(schema),
            ])

        # Verbose-gated, same as the PASS/FAIL scenario lines themselves.
        assert "consider ->" not in result.output


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


class TestValidateCmdTestsFilter:
    """Regression (#829): the --tests flag must reach the ValidationEngine so
    runs can be scoped away from the shipped demo/golden fixtures."""

    def test_tests_flag_forwarded_to_engine(self, runner, tmp_path):
        spec = tmp_path / "spec.yaml"
        spec.write_text(
            "openapi: '3.0.4'\n"
            "info:\n"
            "  title: T\n"
            "  version: '1'\n"
            "paths:\n"
            "  /x:\n"
            "    get:\n"
            "      responses:\n"
            "        '200':\n"
            "          description: ok\n",
            encoding="utf-8",
        )

        with patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine:
            engine = _patch_engine()
            MockEngine.return_value = engine
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "openapi",
                "--spec", str(spec),
                "--tests", "POST_*",
            ])

        assert result.exit_code == 0
        assert engine.validate_suite.call_args.kwargs["tests_filter"] == "POST_*"

    def test_no_tests_flag_means_no_filter(self, runner, tmp_path):
        spec = tmp_path / "spec.yaml"
        spec.write_text(
            "openapi: '3.0.4'\n"
            "info:\n"
            "  title: T\n"
            "  version: '1'\n"
            "paths:\n"
            "  /x:\n"
            "    get:\n"
            "      responses:\n"
            "        '200':\n"
            "          description: ok\n",
            encoding="utf-8",
        )

        with patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine:
            engine = _patch_engine()
            MockEngine.return_value = engine
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "openapi",
                "--spec", str(spec),
            ])

        assert result.exit_code == 0
        assert engine.validate_suite.call_args.kwargs["tests_filter"] is None


class TestValidateSuggestedTightening:
    """Regression (#891): the engine computes tightening suggestions via
    TighteningAnalyzer, but validate_cmd never echoed them to stdout —
    breaking the documented report format (docs/CLI_DEMO.md) and the
    smoke test that greps for "consider -> ..." lines."""

    def test_suggestions_are_printed(self, runner, tmp_path):
        schema = tmp_path / "schema.graphql"
        schema.write_text(GQL_CONTENT)

        mock_results = {
            "status": "success",
            "reports": [
                {
                    "scenario_id": "happy_path",
                    "passed": True,
                    "error": "",
                    "suggestions": [
                        "expect(data.email).toBe('test@example.com')",
                        "expect(data.email).toBe(body.email)",
                    ],
                },
            ],
        }

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            MockEngine.return_value.validate_suite.return_value = mock_results
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "graphql",
                "--spec", str(schema),
                "--verbose",
            ])

        assert "consider -> expect(data.email).toBe('test@example.com')" in result.output
        assert "consider -> expect(data.email).toBe(body.email)" in result.output

    def test_failed_scenario_status_line_has_no_suggestions(self, runner, tmp_path):
        schema = tmp_path / "schema.graphql"
        schema.write_text(GQL_CONTENT)

        mock_results = {
            "status": "success",
            "reports": [
                {"scenario_id": "password_too_short", "passed": False, "error": "boom"},
            ],
        }

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
        ):
            MockEngine.return_value.validate_suite.return_value = mock_results
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "graphql",
                "--spec", str(schema),
            ])

        assert "Suggested Assertion Tightening" not in result.output

    def test_git_status_verification_line_printed(self, runner, tmp_path):
        schema = tmp_path / "schema.graphql"
        schema.write_text(GQL_CONTENT)

        with (
            patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine,
            patch("cherenkov.stages.generate.GenerateStage.run"),
            patch("cherenkov.cli.commands.validate.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            MockEngine.return_value = _patch_engine()
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:4000",
                "--source", "graphql",
                "--spec", str(schema),
            ])

        assert "zero test files were auto-modified by validation" in result.output


class TestFindingsReport:
    """Regression: severity was passed as a raw string ("high") where DivergenceFinding
    requires the Severity enum — mypy-blocking (arg-type) and would also have raised a
    pydantic ValidationError at runtime the first time a failing scenario was reported."""

    def test_builds_finding_with_severity_enum(self):
        from cherenkov.cli.commands.validate import _findings_report
        from cherenkov.core.contracts import Severity

        report = _findings_report({
            "reports": [
                {"scenario_id": "user_happy_path", "passed": False, "error": "connection refused"},
            ],
        })

        assert len(report.findings) == 1
        assert report.findings[0].severity == Severity.HIGH

    def test_skips_passing_scenarios(self):
        from cherenkov.cli.commands.validate import _findings_report

        report = _findings_report({"reports": [{"scenario_id": "s1", "passed": True}]})

        assert report.findings == []
