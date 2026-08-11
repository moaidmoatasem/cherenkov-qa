from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from cherenkov.core.events import CHERENKOVEvent


class EventBus(Protocol):
    """Placeholder docstring.

<description>"""
    def publish(self, event: CHERENKOVEvent) -> None: ...
        """Placeholder docstring.

:param event: <description>
:return: <description>"""

    def subscribe(
        """Placeholder docstring.

:param event_name: <description>
:param handler: <description>
:return: <description>"""
        self, event_name: str, handler: Callable[[CHERENKOVEvent], None]
    ) -> None: ...

    def unsubscribe(
        """Placeholder docstring.

:param event_name: <description>
:param handler: <description>
:return: <description>"""
        self, event_name: str, handler: Callable[[CHERENKOVEvent], None]
    ) -> None: ...

    @property
    def handlers(self) -> dict[str, list[Callable[[CHERENKOVEvent], None]]]: ...
        """Placeholder docstring.

:return: <description>"""
