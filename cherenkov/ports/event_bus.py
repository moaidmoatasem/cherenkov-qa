from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from cherenkov.core.events import CHERENKOVEvent


class EventBus(Protocol):
    def publish(self, event: CHERENKOVEvent) -> None: ...

    def subscribe(
        self, event_name: str, handler: Callable[[CHERENKOVEvent], None]
    ) -> None: ...

    def unsubscribe(
        self, event_name: str, handler: Callable[[CHERENKOVEvent], None]
    ) -> None: ...

    @property
    def handlers(self) -> dict[str, list[Callable[[CHERENKOVEvent], None]]]: ...
