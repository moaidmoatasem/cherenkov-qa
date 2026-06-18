import subprocess
from cherenkov.ports.event_bus import EventBus

class QwenCodeChannelAdapter(EventBus):
    """
    Publishes CHERENKOV divergence events to Qwen Code's IM channels
    (Telegram, DingTalk, WeChat) via Qwen Code's headless CLI.
    """
    
    def __init__(self):
        super().__init__()
        
    def publish(self, topic: str, payload: dict) -> None:
        if topic == "divergence_detected":
            self._notify_qwen_channel(payload)
            
    def _notify_qwen_channel(self, payload: dict) -> None:
        """Send notification via Qwen Code channel hook."""
        endpoint = payload.get("endpoint", "unknown")
        severity = payload.get("severity", "low")
        message = f"🚨 Spec Divergence Detected: {endpoint} (Severity: {severity})"
        
        # Use Qwen Code CLI to send notification through configured channels
        # E.g., qwen channel send --message "..."
        cmd = ["qwen", "channel", "send", "--message", message]
        
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
        except Exception:
            # Fallback or log if Qwen Code is unreachable
            pass
