from __future__ import annotations

from typing import Protocol, Any

from cherenkov.core.devices import DeviceInfo


class DeviceRegistry(Protocol):
    def register(self, device: DeviceInfo) -> str: ...

    def get(self, device_id: str) -> DeviceInfo | None: ...

    def list(self) -> list[dict[str, Any]]: ...

    def unregister(self, device_id: str) -> bool: ...
