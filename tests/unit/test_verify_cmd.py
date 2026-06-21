"""Unit tests for `cherenkov verify` CLI command (E1.1)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cherenkov.cli.commands.verify import verify_cmd
from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceReport,
    Severity,
    StageMeta,
)


def _make_report(
    dc: DivergenceClass = DivergenceClass.D1_SPEC_CODE,
    sev: Severity = Severity.HIGH,
    endpoint: str = "POST /pet",
) -> DivergenceReport:
    ev = DivergenceEvidence(
        request_summary=f"POST https://example.com{endpoint.split(' ', 1)[-1]} → 500",
        diff="status mismatch: expected=400, actual=500",
        response_actual="500",
        response_expected="400",
    )
    return DivergenceReport(
        id="abc123",
        divergence_class=dc,
        claim_a="spec says 400",
        claim_b="impl returns 500",
        severity=sev,
        endpoint=endpoint,
        evidence=ev,
        repro_steps=["Send POST /pet", "Expect 400"],
        metadata=StageMeta(stage="proof_run"),
    )


class TestVerifyCmd:
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(verify_cmd, ["--help"])
        assert result.exit_code == 0
        assert "--url" in result.output
        assert "--spec" in result.output

    def test_zero_config_uses_petstore_default(self) -> None:
        """E1.1: no --url should probe the Petstore demo, not error."""
        from cherenkov.divergence.proof_run import PETSTORE_BASE_URL
        runner = CliRunner()
        with patch("cherenkov.cli.commands.verify.run_proof", return_value=[]) as mock:
            result = runner.invoke(verify_cmd, [])
        assert result.exit_code == 0, result.output
        assert "demo mode" in result.output
        mock.assert_called_once_with(
            base_url=PETSTORE_BASE_URL, spec=None, use_llm=False
        )

    def test_no_divergences_exits_0(self) -> None:
        runner = CliRunner()
        with patch("cherenkov.cli.commands.verify.run_proof", return_value=[]) as mock:
            result = runner.invoke(verify_cmd, ["--url", "http://localhost:9999"])
        assert result.exit_code == 0
        assert "No divergences found" in result.output
        mock.assert_called_once_with(
            base_url="http://localhost:9999", spec=None, use_llm=False
        )

    def test_divergences_printed(self) -> None:
        runner = CliRunner()
        reports = [_make_report()]
        with patch("cherenkov.cli.commands.verify.run_proof", return_value=reports):
            result = runner.invoke(verify_cmd, ["--url", "http://localhost:9999"])
        assert result.exit_code == 0
        assert "1 divergence(s) found" in result.output
        assert "D1_spec_code" in result.output
        assert "spec says 400" in result.output
        assert "impl returns 500" in result.output

    def test_fail_on_divergence(self) -> None:
        runner = CliRunner()
        reports = [_make_report()]
        with patch("cherenkov.cli.commands.verify.run_proof", return_value=reports):
            result = runner.invoke(
                verify_cmd,
                ["--url", "http://localhost:9999", "--fail-on-divergence"],
            )
        assert result.exit_code == 1

    def test_no_fail_when_clean(self) -> None:
        runner = CliRunner()
        with patch("cherenkov.cli.commands.verify.run_proof", return_value=[]):
            result = runner.invoke(
                verify_cmd,
                ["--url", "http://localhost:9999", "--fail-on-divergence"],
            )
        assert result.exit_code == 0

    def test_json_output_written(self, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        runner = CliRunner()
        reports = [_make_report()]
        with patch("cherenkov.cli.commands.verify.run_proof", return_value=reports):
            result = runner.invoke(
                verify_cmd,
                ["--url", "http://localhost:9999", "--output", str(out)],
            )
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["endpoint"] == "POST /pet"

    def test_llm_flag_passed(self) -> None:
        runner = CliRunner()
        with patch("cherenkov.cli.commands.verify.run_proof", return_value=[]) as mock:
            runner.invoke(verify_cmd, ["--url", "http://localhost:9999", "--llm"])
        mock.assert_called_once_with(
            base_url="http://localhost:9999", spec=None, use_llm=True
        )

    def test_multiple_severities_displayed(self) -> None:
        runner = CliRunner()
        reports = [
            _make_report(sev=Severity.HIGH),
            _make_report(sev=Severity.MEDIUM, dc=DivergenceClass.D2_CODE_PROD, endpoint="GET /store"),
            _make_report(sev=Severity.LOW, dc=DivergenceClass.D5_SPEC_PROD, endpoint="GET /pet/0"),
        ]
        with patch("cherenkov.cli.commands.verify.run_proof", return_value=reports):
            result = runner.invoke(verify_cmd, ["--url", "http://localhost:9999"])
        assert result.exit_code == 0
        assert "3 divergence(s) found" in result.output
        assert "[HIGH]" in result.output
        assert "[MEDIUM]" in result.output
        assert "[LOW]" in result.output
