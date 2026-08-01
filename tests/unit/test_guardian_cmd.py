"""Smoke tests for `cherenkov guardian start` (issue #811).

`SpecGuardianDaemon` (cherenkov/spec_guardian/daemon.py) was a complete,
tested-in-isolation polling loop with zero callers. These tests cover the
new CLI wiring and prove the daemon can actually be started and stopped.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cherenkov.cli.commands.guardian_cmd import (
    _default_endpoints,
    _parse_endpoint_opts,
    guardian_cmd,
)
from cherenkov.spec_guardian.daemon import SpecGuardianDaemon

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "paths": {
        "/health": {
            "get": {"responses": {"200": {"description": "OK"}}},
        },
        "/users/{id}": {
            "get": {"responses": {"200": {"description": "OK"}}},
        },
        "/users": {
            "post": {"responses": {"201": {"description": "Created"}}},
        },
    },
}


def _write_spec(tmp_path: Path) -> Path:
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(SPEC))
    return spec_path


def _mock_response(status_code: int = 200, body: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {}
    resp.content = b"{}"
    resp.json.return_value = body or {}
    return resp


class TestEndpointDefaults:
    def test_default_endpoints_only_concrete_get_paths(self, tmp_path: Path) -> None:
        spec_path = _write_spec(tmp_path)
        endpoints = _default_endpoints(str(spec_path))
        assert endpoints == [{"method": "GET", "path": "/health"}]

    def test_parse_endpoint_opts(self) -> None:
        parsed = _parse_endpoint_opts(("GET:/health", "post:/users"))
        assert parsed == [
            {"method": "GET", "path": "/health"},
            {"method": "POST", "path": "/users"},
        ]


class TestGuardianStartCli:
    def test_runs_bounded_cycles_and_exits_cleanly(self, tmp_path: Path) -> None:
        spec_path = _write_spec(tmp_path)
        db_path = tmp_path / "drift.db"

        with patch(
            "cherenkov.spec_guardian.daemon.requests.request",
            return_value=_mock_response(200),
        ):
            result = CliRunner().invoke(
                guardian_cmd,
                [
                    "start",
                    "--spec", str(spec_path),
                    "--url", "http://example.test",
                    "--max-loops", "2",
                    "--db", str(db_path),
                ],
            )

        assert result.exit_code == 0, result.output
        assert "Watching 1 endpoint(s)" in result.output
        assert "cycle 1/2" in result.output
        assert "cycle 2/2" in result.output
        assert db_path.exists()

    def test_no_endpoints_fails_fast(self, tmp_path: Path) -> None:
        spec_path = tmp_path / "openapi.json"
        spec_path.write_text(json.dumps({"paths": {}}))

        result = CliRunner().invoke(
            guardian_cmd,
            ["start", "--spec", str(spec_path), "--url", "http://example.test"],
        )

        assert result.exit_code == 1
        assert "No endpoints to monitor" in result.output


class TestDaemonLifecycle:
    def test_daemon_starts_and_stops(self, tmp_path: Path) -> None:
        spec_path = _write_spec(tmp_path)
        daemon = SpecGuardianDaemon(
            spec_path=str(spec_path),
            base_url="http://example.test",
            check_interval=0,
            endpoints=[{"method": "GET", "path": "/health"}],
            db_path=tmp_path / "drift.db",
        )

        with (
            patch(
                "cherenkov.spec_guardian.daemon.requests.request",
                return_value=_mock_response(200),
            ),
            # SIGINT/SIGTERM registration only works in the main thread;
            # the CLI always runs the daemon there, so it's a no-op here.
            patch("cherenkov.spec_guardian.daemon.signal.signal"),
        ):
            thread = threading.Thread(target=daemon.start, daemon=True)
            thread.start()
            for _ in range(50):
                if daemon.total_checks > 0:
                    break
                time.sleep(0.05)

            daemon.stop()
            thread.join(timeout=5)

        assert not thread.is_alive()
        assert daemon.running is False
        assert daemon.total_checks > 0
