from __future__ import annotations

from typing import Protocol, Any, Dict

from cherenkov.core.events import CHERENKOVEvent


class NotifierPort(Protocol):
    name: str

    def send(self, report: Dict[str, Any]) -> bool: ...

    def notify_event(self, event: CHERENKOVEvent) -> None: ...


class ExporterPort(Protocol):
    name: str

    def export(self, report: Dict[str, Any]) -> Dict[str, Any]: ...
