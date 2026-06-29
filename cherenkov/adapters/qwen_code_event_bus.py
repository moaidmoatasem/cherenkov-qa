import contextlib
import subprocess
from collections.abc import Callable

from cherenkov.core.events import CHERENKOVEvent


class QwenCodeChannelAdapter:
    """
    Publishes CHERENKOV divergence events to Qwen Code's IM channels
    (Telegram, DingTalk, WeChat) via Qwen Code's headless CLI.
    """

    def __init__(self):
        self._handlers = {}

    def publish(self, event: CHERENKOVEvent) -> None:
        if event.name == "divergence_detected" or event.category == "DIVERGENCE":
            self._notify_qwen_channel(event)

    def subscribe(self, event_name: str, handler: Callable[[CHERENKOVEvent], None]) -> None:
        pass

    def unsubscribe(self, event_name: str, handler: Callable[[CHERENKOVEvent], None]) -> None:
        pass

    @property
    def handlers(self) -> dict[str, list[Callable[[CHERENKOVEvent], None]]]:
        return self._handlers

    def _notify_qwen_channel(self, event: CHERENKOVEvent) -> None:
        """Send notification via Qwen Code channel hook."""
        payload = event.payload or {}
        endpoint = payload.get("endpoint", "unknown")
        severity = payload.get("severity", "low")
        message = f"🚨 Spec Divergence Detected: {endpoint} (Severity: {severity})"

        # Use Qwen Code CLI to send notification through configured channels
        cmd = ["qwen", "channel", "--message", message]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
        except Exception:
            pass
