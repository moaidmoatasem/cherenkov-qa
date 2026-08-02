"""Tests for `cherenkov guardian` CLI command (issue #811)."""
from __future__ import annotations

import signal
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cherenkov.cli.commands.guardian_cmd import (
    _default_endpoints,
    _parse_endpoint_opts,
    guardian_cmd,
)
from cherenkov.spec_guardian.daemon import SpecGuardianDaemon

# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_spec(tmp_path: Path) -> Path:
    """Create a small OpenAPI spec with GET and parameterized/POST endpoints."""
    import yaml
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {"get": {"responses": {"200": {"description": "OK"}}}},
            "/health": {"get": {"responses": {"200": {"description": "OK"}}}},
            "/users/{id}": {"get": {"responses": {"200": {"description": "OK"}}}},
            "/users_post": {"post": {"responses": {"201": {"description": "Created"}}}},
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
    instances: list[StubDaemon] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False
        StubDaemon.instances.append(self)

    def start(self) -> None:
        self.started = True

    def run_once(self) -> MagicMock:
        report = MagicMock()
        report.total_checks = 1
        report.events = []
        return report

    def stop(self) -> None:
        pass

# ── CLI wiring ────────────────────────────────────────────────────────────────

class TestEndpointDefaults:
    def test_default_endpoints_only_concrete_get_paths(self, sample_spec: Path) -> None:
        endpoints = _default_endpoints(str(sample_spec))
        # should not include parameterized paths or POST endpoints
        assert {"method": "GET", "path": "/users"} in endpoints
        assert {"method": "GET", "path": "/health"} in endpoints
        assert len(endpoints) == 2

    def test_parse_endpoint_opts(self) -> None:
        parsed = _parse_endpoint_opts(("GET:/health", "post:/users"))
        assert parsed == [
            {"method": "GET", "path": "/health"},
            {"method": "POST", "path": "/users"},
        ]


class TestGuardianCli:
    def test_group_help(self, runner: CliRunner):
        result = runner.invoke(guardian_cmd, ["--help"])
        assert result.exit_code == 0
        assert "guardian" in result.output

    def test_start_help(self, runner: CliRunner):
        result = runner.invoke(guardian_cmd, ["start", "--help"])
        assert result.exit_code == 0
        assert "--spec" in result.output
        assert "--base-url" in result.output

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

    def test_runs_bounded_cycles_and_exits_cleanly(self, runner: CliRunner, sample_spec: Path):
        StubDaemon.instances.clear()
        with patch("cherenkov.spec_guardian.daemon.SpecGuardianDaemon", StubDaemon):
            result = runner.invoke(guardian_cmd, [
                "start",
                "--spec", str(sample_spec),
                "--base-url", "http://example.test",
                "--max-loops", "2",
                "--db", "/tmp/guardian.db",
            ])
        assert result.exit_code == 0, result.output
        assert "cycle 1/2" in result.output
        assert "cycle 2/2" in result.output
        stub = StubDaemon.instances[-1]
        assert stub.started is False # Because max-loops exits early

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
        paths = [e["path"] for e in stub.kwargs["endpoints"]]
        assert "/users" in paths
        assert "/health" in paths

    def test_invalid_endpoint_format_exits_2(self, runner: CliRunner, sample_spec: Path):
        StubDaemon.instances.clear()
        with patch("cherenkov.spec_guardian.daemon.SpecGuardianDaemon", StubDaemon):
            result = runner.invoke(guardian_cmd, [
                "start",
                "--spec", str(sample_spec),
                "--base-url", "http://localhost:8080",
                "--endpoint", "no-method-separator",
            ])
        assert result.exit_code != 0


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
            # Override endpoints to just /health to avoid calling other mocked stuff
            daemon.endpoints = [{"method": "GET", "path": "/health"}]

            stopper = threading.Timer(0.5, daemon.stop)
            stopper.start()
            # mock request so we don't actually hit 127.0.0.1
            with patch("cherenkov.spec_guardian.daemon.requests.request") as mock_req:
                mock_req.return_value.status_code = 200
                mock_req.return_value.json.return_value = {}
                mock_req.return_value.headers = {}
                mock_req.return_value.content = b"{}"
                daemon.start()
            stopper.cancel()
            assert daemon.running is False
            assert daemon.session_start is not None
        finally:
            signal.signal(signal.SIGINT, sigint_prev)
            signal.signal(signal.SIGTERM, sigterm_prev)
