"""
CHERENKOV mobile/contracts.py — domain types for mobile testing.

Mirrors Astur's @astur-mobile/protocol package: all wire types defined here
with zero driver dependencies so consumers can import without pulling in ADB
or Appium code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlatformName(str, Enum):
    ANDROID = "android"
    IOS = "ios"


class DeviceKind(str, Enum):
    EMULATOR = "emulator"
    SIMULATOR = "simulator"
    REAL = "real"


class DeviceState(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BOOTING = "booting"
    UNAUTHORIZED = "unauthorized"
    UNKNOWN = "unknown"


class MobileSessionStatus(str, Enum):
    IDLE = "idle"
    CLAIMED = "claimed"
    RUNNING = "running"
    FAILED = "failed"
    CLOSED = "closed"


class MobileLocatorStrategy(str, Enum):
    """Selector strategies ordered by preference (cross-platform first)."""
    TEXT = "by.text"           # content text / accessibility label — cross-platform
    TEST_ID = "by.testId"     # data-testid / accessibilityIdentifier — cross-platform
    ROLE = "by.role"          # semantic role — cross-platform
    LABEL = "by.label"        # accessibility label — cross-platform
    RESOURCE_ID = "by.id"     # Android resource-id (com.pkg:id/name) — Android only
    XPATH = "by.xpath"        # UIAutomator XPath — Android only, fragile


@dataclass
class DeviceInfo:
    device_id: str
    platform: PlatformName
    kind: DeviceKind
    state: DeviceState = DeviceState.UNKNOWN
    name: str = ""
    os_version: str = ""
    api_level: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "platform": self.platform.value,
            "kind": self.kind.value,
            "state": self.state.value,
            "name": self.name,
            "os_version": self.os_version,
            "api_level": self.api_level,
        }


@dataclass
class MobileSession:
    session_id: str
    device: DeviceInfo
    status: MobileSessionStatus = MobileSessionStatus.IDLE
    app_package: str = ""
    app_activity: str = ""
    artifacts_dir: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "device": self.device.to_dict(),
            "status": self.status.value,
            "app_package": self.app_package,
            "app_activity": self.app_activity,
            "artifacts_dir": self.artifacts_dir,
            "steps": self.steps,
            "error": self.error,
        }
