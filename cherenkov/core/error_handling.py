from __future__ import annotations

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DegradationLevel(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    DOWN = "down"


@dataclass
class HealthStatus:
    level: DegradationLevel = DegradationLevel.HEALTHY
    checks: dict[str, bool] = field(default_factory=dict)
    last_checked: float = 0.0
    detail: str = ""

    def update(self, check_name: str, ok: bool) -> None:
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
        return {
            "level": self.level.value,
            "checks": dict(self.checks),
            "last_checked": self.last_checked,
            "detail": self.detail,
        }


class GracefulDegradation:
    def __init__(self):
        self._health = HealthStatus()

    @property
    def health(self) -> HealthStatus:
        return self._health

    def degraded_or_worse(self) -> bool:
        return self._health.level in (
            DegradationLevel.DEGRADED,
            DegradationLevel.CRITICAL,
            DegradationLevel.DOWN,
        )

    def critical_or_worse(self) -> bool:
        return self._health.level in (DegradationLevel.CRITICAL, DegradationLevel.DOWN)

    def check(self, name: str, fn: Callable[[], bool]) -> bool:
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
    return _DEGRADATION
