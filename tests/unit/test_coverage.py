"""Unit tests for cherenkov/divergence/coverage.py."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cherenkov.divergence.coverage import (
    CoverageReport,
    EndpointCoverage,
    compute_coverage,
)
from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceReport,
    Severity,
    StageMeta,
)


# ── fixtures ───────────────────────────────────────────────────────────────────

_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test", "version": "1.0"},
    "paths": {
        "/pets": {
            "get": {"operationId": "listPets", "responses": {"200": {"description": "ok"}}},
            "post": {"operationId": "createPet", "responses": {"201": {"description": "created"}}},
        },
        "/pets/{id}": {
            "get": {"operationId": "getPet", "responses": {"200": {"description": "ok"}}},
            "delete": {"operationId": "deletePet", "responses": {"204": {"description": "deleted"}}},
        },
    },
}


def _report(endpoint: str, sev: Severity = Severity.HIGH) -> DivergenceReport:
    ev = DivergenceEvidence(
        request_summary=f"{endpoint} → 500",
        diff="status mismatch",
        response_actual="500",
        response_expected="400",
    )
    return DivergenceReport(
        id="test-001",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="spec says 400",
        claim_b="impl returns 500",
        severity=sev,
        endpoint=endpoint,
        evidence=ev,
        repro_steps=[endpoint],
        metadata=StageMeta(stage="proof_run"),
    )


# ── TestComputeCoverage ────────────────────────────────────────────────────────

class TestComputeCoverage:
    def test_empty_spec_returns_zero_total(self):
        cov = compute_coverage({}, [])
        assert cov.total_endpoints == 0
        assert cov.coverage_pct == 100.0  # vacuously true

    def test_empty_reports_all_untested(self):
        cov = compute_coverage(_SPEC, [])
        assert cov.total_endpoints == 4
        assert cov.tested_count == 0
        assert cov.untested_count == 4
        assert cov.coverage_pct == 0.0

    def test_one_report_marks_endpoint_tested(self):
        cov = compute_coverage(_SPEC, [_report("GET /pets")])
        assert cov.tested_count == 1
        assert cov.untested_count == 3

    def test_coverage_pct_calculation(self):
        reports = [_report("GET /pets"), _report("POST /pets")]
        cov = compute_coverage(_SPEC, reports)
        assert cov.coverage_pct == pytest.approx(50.0)

    def test_full_coverage(self):
        reports = [
            _report("GET /pets"),
            _report("POST /pets"),
            _report("GET /pets/{id}"),
            _report("DELETE /pets/{id}"),
        ]
        cov = compute_coverage(_SPEC, reports)
        assert cov.tested_count == 4
        assert cov.coverage_pct == pytest.approx(100.0)
        assert cov.gap_endpoints == []

    def test_operation_id_preserved(self):
        cov = compute_coverage(_SPEC, [])
        ids = {e.operation_id for e in cov.endpoints}
        assert "listPets" in ids
        assert "createPet" in ids

    def test_divergence_count_per_endpoint(self):
        reports = [_report("GET /pets"), _report("GET /pets", Severity.MEDIUM)]
        cov = compute_coverage(_SPEC, reports)
        ep = next(e for e in cov.endpoints if e.method == "GET" and e.path == "/pets")
        assert ep.divergence_count == 2

    def test_case_insensitive_method(self):
        # reports with lowercase method should still match
        r = _report("get /pets")
        cov = compute_coverage(_SPEC, [r])
        ep = next(e for e in cov.endpoints if e.path == "/pets" and e.method == "GET")
        assert ep.tested is True

    def test_gap_endpoints_list(self):
        cov = compute_coverage(_SPEC, [_report("GET /pets")])
        gaps = cov.gap_endpoints
        assert len(gaps) == 3
        methods = {e.method for e in gaps}
        assert "POST" in methods

    def test_tested_endpoints_list(self):
        cov = compute_coverage(_SPEC, [_report("GET /pets"), _report("POST /pets")])
        tested = cov.tested_endpoints
        assert len(tested) == 2
        assert all(e.tested for e in tested)

    def test_no_x_http_extension_keys(self):
        """x-extension keys in path items should not be parsed as methods."""
        spec = {
            "paths": {
                "/item": {
                    "get": {"responses": {"200": {"description": "ok"}}},
                    "x-custom": "ignored",
                    "summary": "also ignored",
                }
            }
        }
        cov = compute_coverage(spec, [])
        assert cov.total_endpoints == 1

    def test_non_dict_path_item_skipped(self):
        spec = {"paths": {"/bad": "not a dict", "/ok": {"get": {"responses": {}}}}}
        cov = compute_coverage(spec, [])
        assert cov.total_endpoints == 1


# ── TestVerifyCoverageFlag ─────────────────────────────────────────────────────

class TestVerifyCoverageFlag:
    def test_coverage_report_shown_when_spec_provided(self):
        from cherenkov.cli.commands.verify import verify_cmd
        runner = CliRunner()
        spec = json.dumps(_SPEC)
        with runner.isolated_filesystem():
            Path("spec.json").write_text(spec)
            with patch("cherenkov.cli.commands.verify.run_proof", return_value=[]):
                result = runner.invoke(
                    verify_cmd,
                    ["--url", "http://localhost:9", "--spec", "spec.json", "--coverage-report"],
                )
        assert result.exit_code == 0
        assert "Spec coverage" in result.output

    def test_coverage_report_warns_without_spec(self):
        from cherenkov.cli.commands.verify import verify_cmd
        runner = CliRunner()
        with patch("cherenkov.cli.commands.verify.run_proof", return_value=[]):
            result = runner.invoke(
                verify_cmd,
                ["--url", "http://localhost:9", "--coverage-report"],
            )
        assert result.exit_code == 0
        assert "requires --spec" in result.output

    def test_coverage_shows_gap_endpoints(self):
        from cherenkov.cli.commands.verify import verify_cmd
        runner = CliRunner()
        spec = json.dumps(_SPEC)
        with runner.isolated_filesystem():
            Path("spec.json").write_text(spec)
            # Only one endpoint tested → three gaps
            report = _report("GET /pets")
            with patch("cherenkov.cli.commands.verify.run_proof", return_value=[report]):
                result = runner.invoke(
                    verify_cmd,
                    ["--url", "http://localhost:9", "--spec", "spec.json", "--coverage-report"],
                )
        assert "Gap" in result.output
        assert "/pets/{id}" in result.output

    def test_coverage_shows_full_when_all_probed(self):
        from cherenkov.cli.commands.verify import verify_cmd
        runner = CliRunner()
        spec = json.dumps(_SPEC)
        reports = [
            _report("GET /pets"),
            _report("POST /pets"),
            _report("GET /pets/{id}"),
            _report("DELETE /pets/{id}"),
        ]
        with runner.isolated_filesystem():
            Path("spec.json").write_text(spec)
            with patch("cherenkov.cli.commands.verify.run_proof", return_value=reports):
                result = runner.invoke(
                    verify_cmd,
                    ["--url", "http://localhost:9", "--spec", "spec.json", "--coverage-report"],
                )
        assert "100.0%" in result.output
        assert "All spec endpoints were probed" in result.output


# ── TestCertifyCoverageFlag ────────────────────────────────────────────────────

class TestCertifyCoverageFlag:
    def test_coverage_report_in_certify(self):
        from cherenkov.cli.commands.certify import certify_cmd
        runner = CliRunner()
        spec = json.dumps(_SPEC)
        with runner.isolated_filesystem():
            Path("spec.json").write_text(spec)
            with patch("cherenkov.cli.commands.certify.run_proof", return_value=[]):
                result = runner.invoke(
                    certify_cmd,
                    ["--url", "http://localhost:9", "--spec", "spec.json", "--coverage-report"],
                )
        assert result.exit_code == 0
        assert "Spec coverage" in result.output
        assert "PASS" in result.output  # cert still shown

    def test_coverage_warns_without_spec_in_certify(self):
        from cherenkov.cli.commands.certify import certify_cmd
        runner = CliRunner()
        with patch("cherenkov.cli.commands.certify.run_proof", return_value=[]):
            result = runner.invoke(
                certify_cmd,
                ["--url", "http://localhost:9", "--coverage-report"],
            )
        assert result.exit_code == 0
        assert "requires --spec" in result.output
