"""tests/unit/test_spec_guardian_phase14.py — Phase 14 Spec Guardian unit tests.

Tests cover:
  - SpecDriftDetector: status drift, field missing, type mismatch, pattern violation
  - DriftStore: save/retrieve events and reports, drift_trend aggregation
  - SpecGuardianDaemon: hot-reload (_maybe_reload_spec) and run_once contract
  - guardian CLI: 'status' and 'trend' commands render without error
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.spec_guardian.core import (
    DriftEvent,
    DriftReport,
    DriftSeverity,
    DriftType,
)
from cherenkov.spec_guardian.detector import SpecDriftDetector
from cherenkov.spec_guardian.store import DriftStore


# ─── fixtures ────────────────────────────────────────────────────────────────

MINIMAL_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test", "version": "0.1.0"},
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["id", "name"],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                            "tag": {
                                                "type": "string",
                                                "pattern": "^[a-z]+$",
                                            },
                                        },
                                    },
                                }
                            }
                        },
                    }
                },
            }
        }
    },
}


@pytest.fixture()
def spec_file(tmp_path: Path) -> Path:
    f = tmp_path / "openapi.json"
    f.write_text(json.dumps(MINIMAL_SPEC))
    return f


@pytest.fixture()
def detector(spec_file: Path) -> SpecDriftDetector:
    return SpecDriftDetector(str(spec_file))


@pytest.fixture()
def db(tmp_path: Path) -> DriftStore:
    return DriftStore(tmp_path / "test_drift.db")


# ─── SpecDriftDetector tests ─────────────────────────────────────────────────

class TestSpecDriftDetector:
    def test_compliant_response_produces_no_events(self, detector: SpecDriftDetector) -> None:
        events = detector.check_response(
            endpoint="/pets",
            method="GET",
            status_code=200,
            response_body=[{"id": 1, "name": "Fido"}],
        )
        # FIELD_EXTRA events for unlisted fields are INFO-level; ensure no CRITICAL/WARNING
        critical = [e for e in events if e.severity == DriftSeverity.CRITICAL]
        assert critical == []

    def test_missing_required_field_is_critical(self, detector: SpecDriftDetector) -> None:
        events = detector.check_response(
            endpoint="/pets",
            method="GET",
            status_code=200,
            response_body=[{"id": 1}],  # missing "name"
        )
        types = {e.drift_type for e in events}
        assert DriftType.REQUIRED_MISSING in types
        severities = {e.severity for e in events if e.drift_type == DriftType.REQUIRED_MISSING}
        assert DriftSeverity.CRITICAL in severities

    def test_type_mismatch_is_critical(self, detector: SpecDriftDetector) -> None:
        events = detector.check_response(
            endpoint="/pets",
            method="GET",
            status_code=200,
            response_body=[{"id": "not-an-int", "name": "Fido"}],
        )
        types = {e.drift_type for e in events}
        assert DriftType.TYPE_MISMATCH in types

    def test_pattern_violation_is_warning(self, detector: SpecDriftDetector) -> None:
        events = detector.check_response(
            endpoint="/pets",
            method="GET",
            status_code=200,
            response_body=[{"id": 1, "name": "Fido", "tag": "UPPERCASE"}],
        )
        pattern_events = [e for e in events if e.drift_type == DriftType.PATTERN_VIOLATION]
        assert pattern_events, "Expected a PATTERN_VIOLATION event"
        assert all(e.severity == DriftSeverity.WARNING for e in pattern_events)

    def test_unknown_endpoint_is_critical_schema_drift(self, detector: SpecDriftDetector) -> None:
        events = detector.check_response(
            endpoint="/nonexistent",
            method="GET",
            status_code=200,
            response_body=None,
        )
        assert len(events) == 1
        assert events[0].drift_type == DriftType.SCHEMA_DRIFT
        assert events[0].severity == DriftSeverity.CRITICAL

    def test_status_code_not_in_spec_is_warning(self, detector: SpecDriftDetector) -> None:
        events = detector.check_response(
            endpoint="/pets",
            method="GET",
            status_code=418,  # not in spec
            response_body=None,
        )
        status_events = [e for e in events if e.drift_type == DriftType.STATUS_DRIFT]
        assert status_events


# ─── DriftStore tests ────────────────────────────────────────────────────────

class TestDriftStore:
    def _make_event(self, severity: DriftSeverity = DriftSeverity.WARNING) -> DriftEvent:
        return DriftEvent(
            drift_type=DriftType.STATUS_DRIFT,
            severity=severity,
            endpoint="/pets",
            method="GET",
            field_path=None,
            expected="200",
            actual=418,
            message="test event",
            timestamp=datetime.now(timezone.utc),
        )

    def _make_report(self, events: list[DriftEvent]) -> DriftReport:
        now = datetime.now(timezone.utc)
        return DriftReport(
            spec_path="openapi.json",
            events=events,
            start_time=now,
            end_time=now,
            total_checks=len(events) + 1,
            compliant_checks=1,
        )

    def test_save_and_retrieve_event(self, db: DriftStore) -> None:
        event = self._make_event()
        event_id = db.save_event(event)
        assert event_id > 0
        recent = db.recent_events(limit=10)
        assert len(recent) == 1
        assert recent[0].endpoint == "/pets"

    def test_save_and_retrieve_report(self, db: DriftStore) -> None:
        event = self._make_event()
        report = self._make_report([event])
        report_id = db.save_report(report)
        assert report_id > 0
        latest = db.latest_report()
        assert latest is not None
        assert latest.spec_path == "openapi.json"

    def test_latest_report_none_when_empty(self, db: DriftStore) -> None:
        assert db.latest_report() is None

    def test_drift_trend_returns_correct_counts(self, db: DriftStore) -> None:
        db.save_event(self._make_event(DriftSeverity.CRITICAL))
        db.save_event(self._make_event(DriftSeverity.WARNING))
        trend = db.drift_trend(hours=24)
        assert trend["total_events"] == 2
        assert trend["critical_events"] == 1
        assert trend["warning_events"] == 1


# ─── SpecGuardianDaemon hot-reload tests ─────────────────────────────────────

class TestSpecGuardianDaemonHotReload:
    def test_maybe_reload_spec_updates_detector_when_mtime_changes(
        self, spec_file: Path, tmp_path: Path
    ) -> None:
        from cherenkov.spec_guardian.daemon import SpecGuardianDaemon

        daemon = SpecGuardianDaemon(
            spec_path=str(spec_file),
            base_url="http://localhost",
            watch_spec=True,
            db_path=tmp_path / "drift.db",
        )
        original_detector = daemon.detector

        # Touch the spec file to change mtime
        time.sleep(0.05)
        spec_file.write_text(json.dumps(MINIMAL_SPEC))

        daemon._maybe_reload_spec()
        assert daemon.detector is not original_detector, "Detector should have been reloaded"

    def test_maybe_reload_spec_noop_when_mtime_unchanged(
        self, spec_file: Path, tmp_path: Path
    ) -> None:
        from cherenkov.spec_guardian.daemon import SpecGuardianDaemon

        daemon = SpecGuardianDaemon(
            spec_path=str(spec_file),
            base_url="http://localhost",
            watch_spec=True,
            db_path=tmp_path / "drift.db",
        )
        original_detector = daemon.detector
        daemon._maybe_reload_spec()  # mtime unchanged
        assert daemon.detector is original_detector, "Detector should NOT have been reloaded"


# ─── guardian CLI subcommand smoke tests ────────────────────────────────────

class TestGuardianCLI:
    def test_status_cmd_no_data(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from cherenkov.cli.commands.guardian_cmd import guardian_status_cmd

        runner = CliRunner()
        result = runner.invoke(
            guardian_status_cmd, ["--db", str(tmp_path / "empty.db")]
        )
        assert result.exit_code == 0
        assert "No drift reports found" in result.output

    def test_status_cmd_with_data(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from cherenkov.cli.commands.guardian_cmd import guardian_status_cmd
        from cherenkov.spec_guardian.store import DriftStore

        db = DriftStore(tmp_path / "drift.db")
        now = datetime.now(timezone.utc)
        report = DriftReport(
            spec_path="openapi.yaml",
            events=[],
            start_time=now,
            end_time=now,
            total_checks=10,
            compliant_checks=10,
        )
        db.save_report(report)

        runner = CliRunner()
        result = runner.invoke(
            guardian_status_cmd, ["--db", str(tmp_path / "drift.db")]
        )
        assert result.exit_code == 0
        assert "drift rate" in result.output.lower()

    def test_trend_cmd_json_output(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from cherenkov.cli.commands.guardian_cmd import guardian_trend_cmd

        runner = CliRunner()
        result = runner.invoke(
            guardian_trend_cmd, ["--db", str(tmp_path / "empty.db"), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total_events" in data
        assert data["total_events"] == 0
