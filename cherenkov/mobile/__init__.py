"""
CHERENKOV mobile — domain types and device registry for mobile testing.

Inspired by Astur (Astur-mobile/Astur): device-native automation without Appium,
protocol types defined first, per-session isolation.
"""

from cherenkov.mobile.contracts import (
    DeviceInfo,
    DeviceKind,
    DeviceState,
    MobileLocatorStrategy,
    MobileSession,
    MobileSessionStatus,
    PlatformName,
)
from cherenkov.mobile.registry import DeviceRegistry

__all__ = [
    "DeviceInfo",
    "DeviceKind",
    "DeviceState",
    "MobileLocatorStrategy",
    "MobileSession",
    "MobileSessionStatus",
    "PlatformName",
    "DeviceRegistry",
]
