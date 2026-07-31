import requests
from abc import ABC, abstractmethod
from typing import Dict, Any
from dataclasses import dataclass

# Domain
@dataclass
class WebhookEvent:
    event_type: str
    payload: Dict[str, Any]

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
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.target_url, 
                    json={"type": event.event_type, "data": event.payload},
                    timeout=5
                )
                if response.status_code in (200, 201, 202, 204):
                    return True
            except requests.RequestException:
                pass
        return False
