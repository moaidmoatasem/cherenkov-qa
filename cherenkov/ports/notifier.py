from __future__ import annotations

from typing import Any, Protocol

from cherenkov.core.events import CHERENKOVEvent


class NotifierPort(Protocol):
    name: str

    def send(self, report: dict[str, Any]) -> bool:
        pass

    def notify_event(self, event: CHERENKOVEvent) -> None:
        pass

class ExporterPort(Protocol):
    name: str

    def export(self, report: dict[str, Any]) -> dict[str, Any]:
        pass
