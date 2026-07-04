from __future__ import annotations

from typing import Protocol, Any

from cherenkov.core.events import CHERENKOVEvent

class NotifierPort(Protocol):
    name: str

    def send(self, report: dict[str, Any]) -> bool: ...

    def notify_event(self, event: CHERENKOVEvent) -> None: ...

class ExporterPort(Protocol):
    name: str

    def export(self, report: dict[str, Any]) -> dict[str, Any]: ...
