"""Tests for `cherenkov guardian` CLI command (issue #811)."""
from __future__ import annotations

import signal
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cherenkov.cli.commands.guardian_cmd import guardian_cmd
from cherenkov.spec_guardian.daemon import SpecGuardianDaemon

# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_spec(tmp_path: Path) -> Path:
    """Create a small OpenAPI spec with two GET endpoints."""
    import yaml
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {"get": {"responses": {"200": {"description": "OK"}}}},
            "/health": {"get": {"responses": {"200": {"description": "OK"}}}},
        },
    }
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(yaml.dump(spec))
    return spec_path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class StubDaemon:
    """Captures constructor kwargs; records whether start() was called."""

    instances: list["StubDaemon"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False
        StubDaemon.instances.append(self)

    def start(self) -> None:
        self.started = True


# ── CLI wiring ────────────────────────────────────────────────────────────────

class TestGuardianCli:
    def test_group_help(self, runner: CliRunner):
        result = runner.invoke(guardian_cmd, ["--help"])
        assert result.exit_code == 0
        assert "guardian" in result.output
        assert "OpenAPI spec drift" in result.output

    def test_start_help(self, runner: CliRunner):
        result = runner.invoke(guardian_cmd, ["start", "--help"])
        assert result.exit_code == 0
        assert "Start the Spec Guardian daemon" in result.output
        assert "--spec" in result.output
        assert "--base-url" in result.output
        assert "--interval" in result.output
        assert "--endpoint" in result.output

    def test_start_requires_spec_and_base_url(self, runner: CliRunner):
        result = runner.invoke(guardian_cmd, ["start"])
        assert result.exit_code == 2
        assert "Missing option" in result.output

    def test_start_wires_daemon(self, runner: CliRunner, sample_spec: Path):
        StubDaemon.instances.clear()
        with patch("cherenkov.spec_guardian.daemon.SpecGuardianDaemon", StubDaemon):
            result = runner.invoke(guardian_cmd, [
                "start",
                "--spec", str(sample_spec),
                "--base-url", "http://localhost:8080",
                "--interval", "5",
                "--endpoint", "GET:/health",
                "--db", "/tmp/guardian.db",
            ])
        assert result.exit_code == 0
        stub = StubDaemon.instances[-1]
        assert stub.started is True
        assert stub.kwargs["check_interval"] == 5
        assert stub.kwargs["base_url"] == "http://localhost:8080"
        assert stub.kwargs["endpoints"] == [{"method": "GET", "path": "/health"}]
        assert stub.kwargs["db_path"] == Path("/tmp/guardian.db")

    def test_endpoints_default_to_spec_paths(self, runner: CliRunner, sample_spec: Path):
        StubDaemon.instances.clear()
        with patch("cherenkov.spec_guardian.daemon.SpecGuardianDaemon", StubDaemon):
            result = runner.invoke(guardian_cmd, [
                "start",
                "--spec", str(sample_spec),
                "--base-url", "http://localhost:8080",
            ])
        assert result.exit_code == 0
        stub = StubDaemon.instances[-1]
        by_path = {e["path"]: e for e in stub.kwargs["endpoints"]}
        assert by_path == {
            "/users": {"method": "GET", "path": "/users"},
            "/health": {"method": "GET", "path": "/health"},
        }

    def test_invalid_endpoint_format_exits_2(self, runner: CliRunner, sample_spec: Path):
        StubDaemon.instances.clear()
        with patch("cherenkov.spec_guardian.daemon.SpecGuardianDaemon", StubDaemon):
            result = runner.invoke(guardian_cmd, [
                "start",
                "--spec", str(sample_spec),
                "--base-url", "http://localhost:8080",
                "--endpoint", "no-method-separator",
            ])
        assert result.exit_code == 2
        assert "METHOD:PATH" in result.output


# ── smoke: daemon start/stop ──────────────────────────────────────────────────

class TestGuardianDaemonSmoke:
    def test_daemon_start_then_stop(self, tmp_path: Path, sample_spec: Path):
        """Start the real daemon loop, stop it from another thread, verify exit."""
        sigint_prev = signal.getsignal(signal.SIGINT)
        sigterm_prev = signal.getsignal(signal.SIGTERM)
        try:
            daemon = SpecGuardianDaemon(
                spec_path=str(sample_spec),
                base_url="http://127.0.0.1:1",
                check_interval=1,
                db_path=tmp_path / "guardian.db",
            )
            stopper = threading.Timer(0.5, daemon.stop)
            stopper.start()
            daemon.start()
            stopper.cancel()
            assert daemon.running is False
            assert daemon.session_start is not None
            assert daemon.total_checks == 0
        finally:
            signal.signal(signal.SIGINT, sigint_prev)
            signal.signal(signal.SIGTERM, sigterm_prev)
