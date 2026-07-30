"""Unit tests for cherenkov/stages/doctor_cmd.py — run_doctor's device status reporting.

Regression coverage for: `detect_ollama_device()` returns "UNKNOWN" when Ollama
itself isn't reachable (not installed, or installed but not running) -- distinct
from "CPU" (Ollama reachable, just not GPU-accelerated). `run_doctor` used to
treat both the same way and print "CPU mode - generation ~10x slower. GPU
recommended.", which is actively misleading when Ollama isn't running at all,
and also double-counted the same root cause as two separate issues in the
summary tally.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def _mocked_environment(monkeypatch):
    """Mock every environment probe run_doctor makes except the Ollama ones,
    so the summary issue count is fully deterministic and independent of the
    sandbox this test happens to run in.
    """
    import cherenkov.stages.doctor_cmd as doctor_cmd

    monkeypatch.setattr(doctor_cmd, "check_node", lambda: (True, "v22.0.0"))
    monkeypatch.setattr(doctor_cmd, "check_npx_playwright", lambda: (True, "Version 1.56.1"))
    monkeypatch.setattr(doctor_cmd, "check_prism_docker", lambda: (True, "available"))
    monkeypatch.setattr(doctor_cmd, "check_egress_blocked", lambda cfg: (True, "egress policy consistent"))

    cfg = MagicMock()
    cfg.to_dict.return_value = {}
    cfg.get_with_provenance.return_value = []
    cfg.get.side_effect = lambda key, default=None: default
    cfg.errors.return_value = []
    cfg.autodetect_spec.return_value = ["openapi.json"]
    monkeypatch.setattr(doctor_cmd, "load_effective_config", lambda: cfg)
    return doctor_cmd


def _run_and_capture(capsys, device: str, ollama_bin: bool):
    import cherenkov.stages.doctor_cmd as doctor_cmd

    settings = MagicMock()
    settings.detect_ollama_device.return_value = device
    with patch.object(doctor_cmd, "check_ollama_binary", return_value=(ollama_bin, "detail")):
        with patch.object(doctor_cmd, "get_settings", return_value=settings):
            exit_code = doctor_cmd.run_doctor()
    return exit_code, capsys.readouterr().out


class TestDeviceStatusReporting:
    def test_unknown_device_does_not_claim_cpu_mode(self, _mocked_environment, capsys):
        _, out = _run_and_capture(capsys, device="UNKNOWN", ollama_bin=False)
        assert "CPU mode" not in out
        assert "GPU recommended" not in out
        assert "Ollama not reachable" in out

    def test_unknown_device_not_double_counted_as_separate_issue(self, _mocked_environment, capsys):
        # Ollama absent is exactly one root cause -- the missing binary --
        # and must be reported as exactly one issue, not two.
        _, out = _run_and_capture(capsys, device="UNKNOWN", ollama_bin=False)
        assert "1 issue(s) detected" in out

    def test_cpu_device_still_warns_with_gpu_recommendation(self, _mocked_environment, capsys):
        # Ollama IS reachable here, just running on CPU -- the original
        # message is accurate and should be preserved.
        _, out = _run_and_capture(capsys, device="CPU", ollama_bin=True)
        assert "CPU mode - generation ~10x slower. GPU recommended." in out
        assert "Ollama not reachable" not in out

    def test_gpu_device_reports_ok(self, _mocked_environment, capsys):
        exit_code, out = _run_and_capture(capsys, device="GPU", ollama_bin=True)
        assert "CPU mode" not in out
        assert "Ollama not reachable" not in out
        assert "device" in out and "[OK]" in out
        assert exit_code == 0
