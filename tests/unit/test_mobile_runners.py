import os
import json
import tempfile
import pytest
from unittest.mock import patch

from cherenkov.execution.maestro_runner import MaestroRunner
from cherenkov.execution.appium_runner import AppiumRunner
from cherenkov.sources.mobile.parsers import HARParser, HILParser
from cherenkov.sources.mobile.contracts import MobileApp, MobileFlow


# Other test modules (e.g. test_golden_path GP-9) mutate this env var, so set
# it per-test rather than at import time to stay order-independent.
@pytest.fixture(autouse=True)
def _mobile_dry_run(monkeypatch):
    monkeypatch.setenv("CHERENKOV_MOBILE_DRY_RUN", "1")


# Test dry-run mode
def test_maestro_dry_run_passes():
    runner = MaestroRunner()
    result = runner.run_test("/nonexistent/test.yaml")
    assert result["status"] == "passed"
    assert result.get("dry_run") is True


def test_maestro_health_check_dry_run():
    runner = MaestroRunner()
    assert runner.health_check() is True


def test_appium_dry_run_passes():
    runner = AppiumRunner()
    result = runner.run_test("/nonexistent/test.py")
    assert result["status"] == "passed"
    assert result.get("dry_run") is True


def test_appium_health_check_dry_run():
    runner = AppiumRunner()
    assert runner.health_check() is True


# Test HAR parser
def test_har_parser_valid():
    har = {"log": {"entries": [{"request": {"url": "https://api.example.com/users", "method": "GET"}, "response": {"status": 200}}]}}
    with tempfile.NamedTemporaryFile(suffix=".har", mode="w", delete=False) as f:
        json.dump(har, f)
        fname = f.name
    result = HARParser().parse(fname)
    assert len(result) == 1
    assert result[0]["method"] == "GET"
    os.unlink(fname)


def test_har_parser_empty():
    har = {"log": {"entries": []}}
    with tempfile.NamedTemporaryFile(suffix=".har", mode="w", delete=False) as f:
        json.dump(har, f)
        fname = f.name
    result = HARParser().parse(fname)
    assert result == []
    os.unlink(fname)


def test_hil_parser_valid():
    hil = [{"flow_id": "f1", "name": "Login", "screens": [], "actions": ["tap login"]}]
    with tempfile.NamedTemporaryFile(suffix=".hil", mode="w", delete=False) as f:
        json.dump(hil, f)
        fname = f.name
    flows = HILParser().parse(fname)
    assert len(flows) == 1
    assert flows[0].flow_id == "f1"
    os.unlink(fname)


def test_maestro_run_directory_dry_run():
    runner = MaestroRunner()
    result = runner.run_directory("/nonexistent/dir")
    assert result["status"] == "passed"
    assert result.get("dry_run") is True


# Test that real mode would call subprocess (without running it)
def test_maestro_real_mode_calls_subprocess(monkeypatch):
    monkeypatch.delenv("CHERENKOV_MOBILE_DRY_RUN", raising=False)
    runner = MaestroRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
        result = runner.run_test("/some/test.yaml")
        assert mock_run.called
