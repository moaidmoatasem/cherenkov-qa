"""Unit tests for `cherenkov report` and `cherenkov self-test` CLI commands."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cherenkov.cli.commands.simple import report_cmd, self_test_cmd


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_events(run_dir: Path, events: list[dict]) -> None:
    events_file = run_dir / "events.jsonl"
    with open(events_file, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


# ── report command ─────────────────────────────────────────────────────────────

class TestReportCmd:
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(report_cmd, ["--help"])
        assert result.exit_code == 0
        assert "--output" in result.output or "-o" in result.output

    def test_no_runs_dir_exits_1(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(report_cmd, [])
        assert result.exit_code == 1
        assert "No runs found" in result.output

    def test_empty_runs_dir_exits_1(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            os.makedirs(os.path.join(td, ".cherenkov", "runs"), exist_ok=True)
            result = runner.invoke(report_cmd, [])
        assert result.exit_code == 1
        assert "No runs found" in result.output

    def test_missing_events_file_exits_1(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            run_dir = Path(td) / ".cherenkov" / "runs" / "run-001"
            run_dir.mkdir(parents=True)
            result = runner.invoke(report_cmd, [])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_empty_events_file_exits_0(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            run_dir = Path(td) / ".cherenkov" / "runs" / "run-001"
            run_dir.mkdir(parents=True)
            _write_events(run_dir, [])
            result = runner.invoke(report_cmd, [])
        assert result.exit_code == 0
        assert "0/0 passed" in result.output

    def test_review_events_counted(self, tmp_path: Path) -> None:
        runner = CliRunner()
        events = [
            {"stage": "REVIEW", "msg": "stage success", "verdict": "AUTO_APPROVE",
             "scenario_id": "s1", "quality_score": 0.9},
            {"stage": "REVIEW", "msg": "stage success", "verdict": "REJECT",
             "scenario_id": "s2", "quality_score": 0.3},
        ]
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            run_dir = Path(td) / ".cherenkov" / "runs" / "run-001"
            run_dir.mkdir(parents=True)
            _write_events(run_dir, events)
            result = runner.invoke(report_cmd, [])
        assert result.exit_code == 0
        assert "1/2 passed" in result.output

    def test_skipped_endpoints_reported(self, tmp_path: Path) -> None:
        runner = CliRunner()
        events = [
            {"stage": "INGEST", "msg": "skipping low richness endpoint",
             "path": "/foo", "method": "GET", "richness": 0.1},
        ]
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            run_dir = Path(td) / ".cherenkov" / "runs" / "run-001"
            run_dir.mkdir(parents=True)
            _write_events(run_dir, events)
            result = runner.invoke(report_cmd, [])
        assert result.exit_code == 0
        assert "Skipped low-richness endpoints: 1" in result.output
        assert "GET /foo" in result.output

    def test_output_writes_json(self, tmp_path: Path) -> None:
        runner = CliRunner()
        events = [
            {"stage": "REVIEW", "msg": "stage success", "verdict": "AUTO_APPROVE",
             "scenario_id": "s1", "quality_score": 0.8},
        ]
        out_file = str(tmp_path / "report.json")
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            run_dir = Path(td) / ".cherenkov" / "runs" / "run-001"
            run_dir.mkdir(parents=True)
            _write_events(run_dir, events)
            result = runner.invoke(report_cmd, ["-o", out_file])
        assert result.exit_code == 0
        assert os.path.exists(out_file)
        with open(out_file) as f:
            data = json.load(f)
        assert data["total_scenarios"] == 1
        assert data["passed_scenarios"] == 1
        assert data["success_rate"] == pytest.approx(1.0)

    def test_diff_report_missing_file_exits_1(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            run_dir = Path(td) / ".cherenkov" / "runs" / "run-001"
            run_dir.mkdir(parents=True)
            _write_events(run_dir, [])
            result = runner.invoke(report_cmd, ["-d", str(tmp_path / "nonexistent.json")])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_diff_report_compares_rates(self, tmp_path: Path) -> None:
        runner = CliRunner()
        events = [
            {"stage": "REVIEW", "msg": "stage success", "verdict": "AUTO_APPROVE",
             "scenario_id": "s1", "quality_score": 0.9},
        ]
        prev_data = {"success_rate": 0.5, "scenarios": []}
        prev_file = str(tmp_path / "prev.json")
        with open(prev_file, "w") as f:
            json.dump(prev_data, f)

        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            run_dir = Path(td) / ".cherenkov" / "runs" / "run-001"
            run_dir.mkdir(parents=True)
            _write_events(run_dir, events)
            result = runner.invoke(report_cmd, ["-d", prev_file])
        assert result.exit_code == 0
        assert "DIFF REPORT" in result.output
        assert "Previous Success Rate" in result.output


# ── self-test command ──────────────────────────────────────────────────────────

class TestSelfTestCmd:
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(self_test_cmd, ["--help"])
        assert result.exit_code == 0

    def test_ollama_unreachable_exits_1(self) -> None:
        runner = CliRunner()
        with patch("cherenkov.stages.self_test_cmd.requests.get") as mock_get:
            mock_get.side_effect = ConnectionError("refused")
            result = runner.invoke(self_test_cmd, [])
        assert result.exit_code == 1
        assert "FAILED" in result.output

    def test_full_pass(self) -> None:
        runner = CliRunner()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.complete_code.return_value = (
            "import { test } from '@playwright/test';\n"
            "import { client } from '../client';\n"
            "test('health', async () => {});\n"
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = ""

        with (
            patch("cherenkov.stages.self_test_cmd.requests.get", return_value=mock_resp),
            patch("cherenkov.stages.self_test_cmd.get_client", return_value=mock_client),
            patch("cherenkov.stages.self_test_cmd.subprocess.run", return_value=mock_proc),
            patch("cherenkov.stages.self_test_cmd.get_settings") as mock_settings,
        ):
            mock_settings.return_value.OLLAMA_URL = "http://localhost:11434/api/generate"
            mock_settings.return_value.GEN_MODEL = "codellama"
            result = runner.invoke(self_test_cmd, [])

        assert result.exit_code == 0
        assert "SELF-TEST PASSED" in result.output

    def test_bad_generated_code_exits_1(self) -> None:
        runner = CliRunner()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.complete_code.return_value = "// empty"

        with (
            patch("cherenkov.stages.self_test_cmd.requests.get", return_value=mock_resp),
            patch("cherenkov.stages.self_test_cmd.get_client", return_value=mock_client),
            patch("cherenkov.stages.self_test_cmd.get_settings") as mock_settings,
        ):
            mock_settings.return_value.OLLAMA_URL = "http://localhost:11434/api/generate"
            mock_settings.return_value.GEN_MODEL = "codellama"
            result = runner.invoke(self_test_cmd, [])

        assert result.exit_code == 1
        assert "missing required imports" in result.output

    def test_tsc_failure_exits_1(self) -> None:
        runner = CliRunner()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.complete_code.return_value = (
            "import { test } from '@playwright/test';\n"
            "import { client } from '../client';\n"
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "TS2304: Cannot find name 'foo'"

        with (
            patch("cherenkov.stages.self_test_cmd.requests.get", return_value=mock_resp),
            patch("cherenkov.stages.self_test_cmd.get_client", return_value=mock_client),
            patch("cherenkov.stages.self_test_cmd.subprocess.run", return_value=mock_proc),
            patch("cherenkov.stages.self_test_cmd.get_settings") as mock_settings,
        ):
            mock_settings.return_value.OLLAMA_URL = "http://localhost:11434/api/generate"
            mock_settings.return_value.GEN_MODEL = "codellama"
            result = runner.invoke(self_test_cmd, [])

        assert result.exit_code == 1
        assert "FAILED" in result.output
