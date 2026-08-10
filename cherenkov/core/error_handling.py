"""
cherenkov/core/error_handling.py — Graceful degradation and health status monitoring.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DegradationLevel(str, Enum):
    """System degradation status level enumeration (HEALTHY, DEGRADED, CRITICAL, DOWN)."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    DOWN = "down"


@dataclass
class HealthStatus:
    """Tracks overall health level and underlying component health checks."""

    level: DegradationLevel = DegradationLevel.HEALTHY
    checks: dict[str, bool] = field(default_factory=dict)
    last_checked: float = 0.0
    detail: str = ""

    def update(self, check_name: str, ok: bool) -> None:
        """Update a specific component health check status.

        Args:
            check_name (str): Identifier name for health check.
            ok (bool): True if check passed, False otherwise.

        Returns:
            None
        """
        self.checks[check_name] = ok
        self.last_checked = time.time()
        failed = sum(1 for v in self.checks.values() if not v)
        total = len(self.checks)
        if failed == 0:
            self.level = DegradationLevel.HEALTHY
        elif failed <= total // 2:
            self.level = DegradationLevel.DEGRADED
        elif failed < total:
            self.level = DegradationLevel.CRITICAL
        else:
            self.level = DegradationLevel.DOWN

    def to_dict(self) -> dict[str, Any]:
        """Convert health status into a dictionary.

        Returns:
            dict[str, Any]: Dictionary representation of current health state.
        """
        return {
            "level": self.level.value,
            "checks": dict(self.checks),
            "last_checked": self.last_checked,
            "detail": self.detail,
        }


class GracefulDegradation:
    """Manager for checking component health and wrapping calls with degradation policies."""

    def __init__(self):
        """Initialize GracefulDegradation instance."""
        self._health = HealthStatus()

    @property
    def health(self) -> HealthStatus:
        """Return the current HealthStatus instance.

        Returns:
            HealthStatus: Active health status object.
        """
        return self._health

    def degraded_or_worse(self) -> bool:
        """Check if health level is degraded or worse.

        Returns:
            bool: True if degraded, critical, or down, False otherwise.
        """
        return self._health.level in (
            DegradationLevel.DEGRADED,
            DegradationLevel.CRITICAL,
            DegradationLevel.DOWN,
        )

    def critical_or_worse(self) -> bool:
        """Check if health level is critical or worse.

        Returns:
            bool: True if critical or down, False otherwise.
        """
        return self._health.level in (DegradationLevel.CRITICAL, DegradationLevel.DOWN)

    def check(self, name: str, fn: Callable[[], bool]) -> bool:
        """Execute a health check function safely and update status.

        Args:
            name (str): Health check identifier.
            fn (Callable[[], bool]): Health check predicate function.

        Returns:
            bool: True if check passed cleanly, False on failure or exception.
        """
        try:
            ok = fn()
        except Exception as e:
            logger.warning(
                "health check failed", extra={"check": name, "error": str(e)}
            )
            ok = False
        self._health.update(name, ok)
        return ok

    def wrap(self, name: str, fn: Callable) -> Callable:
        """Wrap a function to execute only when degradation level permits.

        Args:
            name (str): Operation identifier.
            fn (Callable): Function to wrap.

        Returns:
            Callable: Wrapped function handling degradation fallback.
        """
        def wrapper(*args, **kwargs):
            if self.critical_or_worse():
                logger.warning("call blocked by degradation", extra={"check": name})
                return None
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                logger.error("call failed", extra={"check": name, "error": str(e)})
                self._health.update(name, False)
                return None

        return wrapper


_DEGRADATION = GracefulDegradation()


def get_degradation() -> GracefulDegradation:
    """Return global GracefulDegradation manager instance.

    Returns:
        GracefulDegradation: Global degradation manager singleton.
    """
    return _DEGRADATION

