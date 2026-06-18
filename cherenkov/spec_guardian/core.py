"""Core data models for spec drift detection."""

from __future__ import annotations

import dataclasses
import enum
from datetime import datetime, timezone
from typing import Any


class DriftType(enum.Enum):
    """Types of spec drift that can be detected."""

    SCHEMA_DRIFT = "schema_drift"
    STATUS_DRIFT = "status_drift"
    FIELD_MISSING = "field_missing"
    FIELD_EXTRA = "field_extra"
    TYPE_MISMATCH = "type_mismatch"
    RANGE_VIOLATION = "range_violation"
    PATTERN_VIOLATION = "pattern_violation"
    REQUIRED_MISSING = "required_missing"


class DriftSeverity(enum.Enum):
    """Severity levels for drift events."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclasses.dataclass
class DriftEvent:
    """A single drift detection event."""

    drift_type: DriftType
    severity: DriftSeverity
    endpoint: str
    method: str
    field_path: str | None
    expected: Any
    actual: Any
    message: str
    timestamp: datetime = dataclasses.field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "endpoint": self.endpoint,
            "method": self.method,
            "field_path": self.field_path,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DriftEvent:
        """Deserialize from dictionary."""
        return cls(
            drift_type=DriftType(data["drift_type"]),
            severity=DriftSeverity(data["severity"]),
            endpoint=data["endpoint"],
            method=data["method"],
            field_path=data.get("field_path"),
            expected=data["expected"],
            actual=data["actual"],
            message=data["message"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclasses.dataclass
class DriftReport:
    """Aggregated drift report for a monitoring session."""

    spec_path: str
    events: list[DriftEvent]
    start_time: datetime
    end_time: datetime
    total_checks: int
    compliant_checks: int

    @property
    def drift_rate(self) -> float:
        """Calculate drift rate (0.0 = fully compliant, 1.0 = all drifted)."""
        if self.total_checks == 0:
            return 0.0
        return 1.0 - (self.compliant_checks / self.total_checks)

    @property
    def critical_count(self) -> int:
        """Count of critical severity events."""
        return sum(1 for e in self.events if e.severity == DriftSeverity.CRITICAL)

    @property
    def warning_count(self) -> int:
        """Count of warning severity events."""
        return sum(1 for e in self.events if e.severity == DriftSeverity.WARNING)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "spec_path": self.spec_path,
            "events": [e.to_dict() for e in self.events],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_checks": self.total_checks,
            "compliant_checks": self.compliant_checks,
            "drift_rate": self.drift_rate,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DriftReport:
        """Deserialize from dictionary."""
        return cls(
            spec_path=data["spec_path"],
            events=[DriftEvent.from_dict(e) for e in data["events"]],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            total_checks=data["total_checks"],
            compliant_checks=data["compliant_checks"],
        )
