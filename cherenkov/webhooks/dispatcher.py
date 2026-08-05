from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests

from cherenkov.core.errors import get_logger

_log = get_logger("WEBHOOK_DISPATCHER")


# Domain
@dataclass
class WebhookEvent:
    event_type: str
    payload: dict[str, Any]

# Ports
class WebhookDispatcherPort(ABC):
    @abstractmethod
    def dispatch(self, event: WebhookEvent) -> bool:
        pass

# Adapters
class HttpWebhookDispatcher(WebhookDispatcherPort):
    def __init__(self, target_url: str, max_retries: int = 3):
        self.target_url = target_url
        self.max_retries = max_retries

    def dispatch(self, event: WebhookEvent) -> bool:
        last_error = "no attempt made"
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.target_url,
                    json={"type": event.event_type, "data": event.payload},
                    timeout=5
                )
                if response.status_code in (200, 201, 202, 204):
                    return True
                last_error = f"HTTP {response.status_code}"
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            _log.warning(
                "webhook delivery attempt failed",
                url=self.target_url,
                event_type=event.event_type,
                attempt=attempt + 1,
                max_retries=self.max_retries,
                error=last_error,
            )
        _log.error(
            "webhook delivery failed after all retries",
            url=self.target_url,
            event_type=event.event_type,
            attempts=self.max_retries,
            error=last_error,
        )
        return False
