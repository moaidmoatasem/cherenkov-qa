"""Audit logging for CHERENKOV enterprise mode."""

from __future__ import annotations

import json
import csv
from datetime import datetime, timezone
import uuid
from typing import Any
from pathlib import Path

from cherenkov.core.errors import get_logger

log = get_logger(__name__)


class AuditLog:
    """Append-only audit log for enterprise compliance."""

    def __init__(self, storage_dir: str = ".cherenkov/audit"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_file = self.storage_dir / "audit.jsonl"

    def log_event(
        self, actor: str, action: str, resource: str, details: dict[str, Any] = None
    ) -> str:
        """Records an event to the audit log."""
        event_id = f"evt_{uuid.uuid4().hex}"
        event = {
            "id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "resource": resource,
            "details": details or {},
        }
        
        with open(self.current_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
            
        log.info("Audit event logged", event_id=event_id, action=action, actor=actor)
        return event_id

    def export_json(self, output_path: str) -> None:
        """Exports the audit log to a JSON array."""
        events = []
        if self.current_log_file.exists():
            with open(self.current_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)

    def export_csv(self, output_path: str) -> None:
        """Exports the audit log to a CSV file."""
        events = []
        if self.current_log_file.exists():
            with open(self.current_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
        
        if not events:
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "timestamp", "actor", "action", "resource", "details"])
            return

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "timestamp", "actor", "action", "resource", "details"]
            )
            writer.writeheader()
            for evt in events:
                row = evt.copy()
                row["details"] = json.dumps(row["details"])
                writer.writerow(row)


# Global singleton
_audit_log = AuditLog()

def get_audit_log() -> AuditLog:
    return _audit_log
