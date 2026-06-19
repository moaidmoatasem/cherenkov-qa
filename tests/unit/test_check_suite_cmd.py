"""Unit tests for `cherenkov check-suite` command (E2.5)."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from cherenkov.cli.commands.check_suite import check_suite_cmd, check_integrity

DEMO = Path(__file__).parents[2] / "demos" / "catch-the-ai-cheating"
SPEC = DEMO / "openapi.yaml"
GOOD = DEMO / "suite_good.py"
WEAKENED = DEMO / "suite_cheat_weakened.py"
DELETED = DEMO / "suite_cheat_deleted.py"
HALLUCINATED = DEMO / "suite_cheat_hallucinated.py"


class TestCheckIntegrity:
    """Unit-test the pure Python analysis engine (no CLI)."""

    def test_clean_baseline_no_findings(self) -> None:
        code = GOOD.read_text()
        assert check_integrity(SPEC, code, code) == []

    def test_weakened_caught(self) -> None:
        base = GOOD.read_text()
        cand = WEAKENED.read_text()
        findings = check_integrity(SPEC, base, cand)
        assert any("WEAKENED" in f for f in findings)

    def test_deleted_test_caught(self) -> None:
        base = GOOD.read_text()
        cand = DELETED.read_text()
        findings = check_integrity(SPEC, base, cand)
        assert any("DELETED" in f for f in findings)

    def test_hallucinated_caught(self) -> None:
        base = GOOD.read_text()
        cand = HALLUCINATED.read_text()
        findings = check_integrity(SPEC, base, cand)
        assert any("HALLUCINATED" in f for f in findings)

    def test_no_spec_skips_hallucination(self) -> None:
        base = GOOD.read_text()
        cand = HALLUCINATED.read_text()
        findings = check_integrity(None, base, cand)
        assert not any("HALLUCINATED" in f for f in findings)


class TestCheckSuiteCmd:
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(check_suite_cmd, ["--help"])
        assert result.exit_code == 0
        assert "--candidate" in result.output

    def test_clean_exits_0(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            check_suite_cmd,
            ["-c", str(GOOD), "-b", str(GOOD), "-s", str(SPEC)],
        )
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_weakened_detected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            check_suite_cmd,
            ["-c", str(WEAKENED), "-b", str(GOOD), "-s", str(SPEC)],
        )
        assert result.exit_code == 0  # not --fail-on-finding
        assert "WEAKENED" in result.output
        assert "CAUGHT" in result.output

    def test_deleted_detected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            check_suite_cmd,
            ["-c", str(DELETED), "-b", str(GOOD), "-s", str(SPEC)],
        )
        assert "DELETED" in result.output

    def test_hallucinated_detected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            check_suite_cmd,
            ["-c", str(HALLUCINATED), "-b", str(GOOD), "-s", str(SPEC)],
        )
        assert "HALLUCINATED" in result.output

    def test_fail_on_finding_exits_1(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            check_suite_cmd,
            ["-c", str(WEAKENED), "-b", str(GOOD), "-s", str(SPEC), "--fail-on-finding"],
        )
        assert result.exit_code == 1

    def test_clean_fail_on_finding_exits_0(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            check_suite_cmd,
            ["-c", str(GOOD), "-b", str(GOOD), "-s", str(SPEC), "--fail-on-finding"],
        )
        assert result.exit_code == 0

    def test_json_output_written(self, tmp_path: Path) -> None:
        out = tmp_path / "findings.json"
        runner = CliRunner()
        runner.invoke(
            check_suite_cmd,
            ["-c", str(WEAKENED), "-b", str(GOOD), "-s", str(SPEC), "-o", str(out)],
        )
        assert out.exists()
        data = json.loads(out.read_text())
        assert "findings" in data
        assert len(data["findings"]) > 0
