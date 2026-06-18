"""Tests for spec_guardian module."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cherenkov.spec_guardian.core import (
    DriftEvent,
    DriftReport,
    DriftSeverity,
    DriftType,
)
from cherenkov.spec_guardian.detector import SpecDriftDetector
from cherenkov.spec_guardian.store import DriftStore


@pytest.fixture
def sample_spec(tmp_path: Path) -> Path:
    """Create a sample OpenAPI spec for testing."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "email": {
                                                    "type": "string",
                                                    "pattern": "^[^@]+@[^@]+$",
                                                },
                                            },
                                            "required": ["id", "name"],
                                        },
                                    }
                                }
                            },
                        }
                    }
                },
                "post": {
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                        },
                                        "required": ["id", "name"],
                                    }
                                }
                            },
                        }
                    }
                },
            },
            "/users/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                            "age": {
                                                "type": "integer",
                                                "minimum": 0,
                                                "maximum": 150,
                                            },
                                        },
                                        "required": ["id", "name"],
                                    }
                                }
                            },
                        }
                    }
                }
            },
        },
    }

    spec_path = tmp_path / "spec.yaml"
    import yaml

    spec_path.write_text(yaml.dump(spec))
    return spec_path


@pytest.fixture
def detector(sample_spec: Path) -> SpecDriftDetector:
    """Create a detector with the sample spec."""
    return SpecDriftDetector(str(sample_spec))


@pytest.fixture
def store(tmp_path: Path) -> DriftStore:
    """Create a temporary drift store."""
    db_path = tmp_path / "test_drift.db"
    return DriftStore(db_path)


class TestDriftEvent:
    """Tests for DriftEvent dataclass."""

    def test_create_event(self):
        """Test creating a drift event."""
        event = DriftEvent(
            drift_type=DriftType.TYPE_MISMATCH,
            severity=DriftSeverity.CRITICAL,
            endpoint="/users",
            method="GET",
            field_path="name",
            expected="string",
            actual="integer",
            message="Type mismatch",
        )
        assert event.drift_type == DriftType.TYPE_MISMATCH
        assert event.severity == DriftSeverity.CRITICAL
        assert event.endpoint == "/users"

    def test_event_to_dict(self):
        """Test serializing event to dict."""
        event = DriftEvent(
            drift_type=DriftType.FIELD_MISSING,
            severity=DriftSeverity.WARNING,
            endpoint="/users",
            method="POST",
            field_path="email",
            expected="present",
            actual="missing",
            message="Field missing",
        )
        d = event.to_dict()
        assert d["drift_type"] == "field_missing"
        assert d["severity"] == "warning"
        assert d["endpoint"] == "/users"

    def test_event_from_dict(self):
        """Test deserializing event from dict."""
        d = {
            "drift_type": "status_drift",
            "severity": "critical",
            "endpoint": "/users",
            "method": "GET",
            "field_path": None,
            "expected": "200",
            "actual": "500",
            "message": "Status mismatch",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        event = DriftEvent.from_dict(d)
        assert event.drift_type == DriftType.STATUS_DRIFT
        assert event.severity == DriftSeverity.CRITICAL


class TestDriftReport:
    """Tests for DriftReport dataclass."""

    def test_drift_rate_calculation(self):
        """Test drift rate calculation."""
        report = DriftReport(
            spec_path="spec.yaml",
            events=[],
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc),
            total_checks=100,
            compliant_checks=90,
        )
        assert abs(report.drift_rate - 0.1) < 1e-9

    def test_drift_rate_zero_checks(self):
        """Test drift rate with zero checks."""
        report = DriftReport(
            spec_path="spec.yaml",
            events=[],
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            total_checks=0,
            compliant_checks=0,
        )
        assert report.drift_rate == 0.0

    def test_critical_count(self):
        """Test counting critical events."""
        events = [
            DriftEvent(
                drift_type=DriftType.TYPE_MISMATCH,
                severity=DriftSeverity.CRITICAL,
                endpoint="/users",
                method="GET",
                field_path="id",
                expected="integer",
                actual="string",
                message="Type mismatch",
            ),
            DriftEvent(
                drift_type=DriftType.FIELD_EXTRA,
                severity=DriftSeverity.WARNING,
                endpoint="/users",
                method="GET",
                field_path="extra",
                expected="not present",
                actual="present",
                message="Extra field",
            ),
        ]
        report = DriftReport(
            spec_path="spec.yaml",
            events=events,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            total_checks=2,
            compliant_checks=0,
        )
        assert report.critical_count == 1
        assert report.warning_count == 1


class TestSpecDriftDetector:
    """Tests for SpecDriftDetector."""

    def test_compliant_response(self, detector: SpecDriftDetector):
        """Test a fully compliant response."""
        events = detector.check_response(
            endpoint="/users",
            method="GET",
            status_code=200,
            response_body=[
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
            ],
        )
        assert len(events) == 0

    def test_missing_required_field(self, detector: SpecDriftDetector):
        """Test detection of missing required field."""
        events = detector.check_response(
            endpoint="/users",
            method="GET",
            status_code=200,
            response_body=[
                {"id": 1},  # Missing required 'name'
            ],
        )
        assert len(events) == 1
        assert events[0].drift_type == DriftType.REQUIRED_MISSING
        assert events[0].severity == DriftSeverity.CRITICAL
        assert "name" in events[0].message

    def test_extra_field(self, detector: SpecDriftDetector):
        """Test detection of extra field not in spec."""
        events = detector.check_response(
            endpoint="/users",
            method="POST",
            status_code=201,
            response_body={
                "id": 1,
                "name": "Alice",
                "extra_field": "value",  # Not in spec
            },
        )
        assert len(events) == 1
        assert events[0].drift_type == DriftType.FIELD_EXTRA
        assert events[0].severity == DriftSeverity.INFO

    def test_type_mismatch(self, detector: SpecDriftDetector):
        """Test detection of type mismatch."""
        events = detector.check_response(
            endpoint="/users",
            method="POST",
            status_code=201,
            response_body={
                "id": "not-an-integer",  # Should be integer
                "name": "Alice",
            },
        )
        assert len(events) == 1
        assert events[0].drift_type == DriftType.TYPE_MISMATCH
        assert events[0].severity == DriftSeverity.CRITICAL

    def test_range_violation(self, detector: SpecDriftDetector):
        """Test detection of range violation."""
        events = detector.check_response(
            endpoint="/users/1",
            method="GET",
            status_code=200,
            response_body={
                "id": 1,
                "name": "Alice",
                "age": 200,  # Exceeds maximum of 150
            },
        )
        assert len(events) == 1
        assert events[0].drift_type == DriftType.RANGE_VIOLATION
        assert events[0].severity == DriftSeverity.WARNING

    def test_pattern_violation(self, detector: SpecDriftDetector):
        """Test detection of pattern violation."""
        events = detector.check_response(
            endpoint="/users",
            method="GET",
            status_code=200,
            response_body=[
                {"id": 1, "name": "Alice", "email": "not-an-email"},
            ],
        )
        assert len(events) == 1
        assert events[0].drift_type == DriftType.PATTERN_VIOLATION
        assert events[0].severity == DriftSeverity.WARNING

    def test_status_code_not_in_spec(self, detector: SpecDriftDetector):
        """Test detection of status code not in spec."""
        events = detector.check_response(
            endpoint="/users",
            method="GET",
            status_code=500,  # Not defined in spec
            response_body=None,
        )
        assert len(events) == 1
        assert events[0].drift_type == DriftType.STATUS_DRIFT
        assert events[0].severity == DriftSeverity.WARNING

    def test_endpoint_not_in_spec(self, detector: SpecDriftDetector):
        """Test detection of endpoint not in spec."""
        events = detector.check_response(
            endpoint="/unknown",
            method="GET",
            status_code=200,
            response_body={},
        )
        assert len(events) == 1
        assert events[0].drift_type == DriftType.SCHEMA_DRIFT
        assert events[0].severity == DriftSeverity.CRITICAL

    def test_path_parameter_matching(self, detector: SpecDriftDetector):
        """Test that path parameters are matched correctly."""
        events = detector.check_response(
            endpoint="/users/123",
            method="GET",
            status_code=200,
            response_body={"id": 123, "name": "Alice"},
        )
        assert len(events) == 0


class TestDriftStore:
    """Tests for DriftStore."""

    def test_save_and_retrieve_event(self, store: DriftStore):
        """Test saving and retrieving a drift event."""
        event = DriftEvent(
            drift_type=DriftType.TYPE_MISMATCH,
            severity=DriftSeverity.CRITICAL,
            endpoint="/users",
            method="GET",
            field_path="id",
            expected="integer",
            actual="string",
            message="Type mismatch",
        )

        event_id = store.save_event(event)
        assert event_id > 0

        events = store.recent_events(limit=10)
        assert len(events) == 1
        assert events[0].drift_type == DriftType.TYPE_MISMATCH
        assert events[0].endpoint == "/users"

    def test_save_and_retrieve_report(self, store: DriftStore):
        """Test saving and retrieving a drift report."""
        report = DriftReport(
            spec_path="spec.yaml",
            events=[],
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc),
            total_checks=10,
            compliant_checks=8,
        )

        report_id = store.save_report(report)
        assert report_id > 0

        retrieved = store.latest_report()
        assert retrieved is not None
        assert retrieved.spec_path == "spec.yaml"
        assert retrieved.total_checks == 10
        assert retrieved.compliant_checks == 8

    def test_drift_trend(self, store: DriftStore):
        """Test drift trend calculation."""
        # Add some events
        for i in range(5):
            event = DriftEvent(
                drift_type=DriftType.TYPE_MISMATCH,
                severity=DriftSeverity.CRITICAL if i < 2 else DriftSeverity.WARNING,
                endpoint="/users",
                method="GET",
                field_path=f"field_{i}",
                expected="expected",
                actual="actual",
                message=f"Event {i}",
            )
            store.save_event(event)

        trend = store.drift_trend(hours=24)
        assert trend["total_events"] == 5
        assert trend["critical_events"] == 2
        assert trend["warning_events"] == 3
