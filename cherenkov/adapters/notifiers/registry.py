from __future__ import annotations

import os
from typing import Any, Dict, Optional

from cherenkov.core.events import CHERENKOVEvent
from cherenkov.ports.notifier import NotifierPort


class NotifierRegistry:
    def __init__(self) -> None:
        self._notifiers: dict[str, NotifierPort] = {}

    def register(self, notifier: NotifierPort) -> None:
        self._notifiers[notifier.name] = notifier

    def notify_all(self, report: Dict[str, Any]) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for name, notifier in self._notifiers.items():
            try:
                results[name] = notifier.send(report)
            except Exception:
                results[name] = False
        return results

    def notify_event_all(self, event: CHERENKOVEvent) -> None:
        for notifier in self._notifiers.values():
            try:
                notifier.notify_event(event)
            except Exception:
                pass

    def get(self, name: str) -> Optional[NotifierPort]:
        return self._notifiers.get(name)

    def list_notifiers(self) -> list[str]:
        return list(self._notifiers.keys())

    @classmethod
    def from_env(cls) -> NotifierRegistry:
        registry = cls()
        env_map = {
            "slack": ("CHERENKOV_SLACK_WEBHOOK_URL", "cherenkov.adapters.notifiers.slack", "SlackNotifier"),
            "teams": ("CHERENKOV_TEAMS_WEBHOOK_URL", "cherenkov.adapters.notifiers.teams", "TeamsNotifier"),
            "linear": ("CHERENKOV_LINEAR_API_KEY", "cherenkov.adapters.notifiers.linear", "LinearNotifier"),
            "webhook": ("CHERENKOV_WEBHOOK_URL", "cherenkov.adapters.notifiers.webhook", "WebhookNotifier"),
            "opsgenie": ("CHERENKOV_OPSGENIE_API_KEY", "cherenkov.adapters.notifiers.opsgenie", "OpsGenieNotifier"),
            "pagerduty": ("CHERENKOV_PAGERDUTY_ROUTING_KEY", "cherenkov.adapters.notifiers.pagerduty", "PagerDutyNotifier"),
        }
        for key, (env_var, module_path, class_name) in env_map.items():
            if os.environ.get(env_var):
                import importlib
                module = importlib.import_module(module_path)
                notifier_cls = getattr(module, class_name)
                registry.register(notifier_cls())
        return registry