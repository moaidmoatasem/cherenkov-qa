from __future__ import annotations

from typing import Any, Protocol

from cherenkov.core.devices import DeviceInfo


class DeviceRegistry(Protocol):
    """Placeholder docstring.

<description>"""
    def register(self, device: DeviceInfo) -> str: ...
        """Placeholder docstring.

:param device: <description>
:return: <description>"""

    def get(self, device_id: str) -> DeviceInfo | None: ...
        """Placeholder docstring.

:param device_id: <description>
:return: <description>"""

    def list(self) -> list[dict[str, Any]]: ...
        """Placeholder docstring.

:return: <description>"""

    def unregister(self, device_id: str) -> bool: ...
        """Placeholder docstring.

:param device_id: <description>
:return: <description>"""
