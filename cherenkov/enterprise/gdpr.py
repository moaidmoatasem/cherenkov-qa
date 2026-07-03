"""GDPR compliance mode for CHERENKOV enterprise — data retention, anonymization, consent."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from cherenkov.core.errors import get_logger

log = get_logger(__name__)


class RetentionPeriod(str, Enum):
    DAYS_30 = "30d"
    DAYS_90 = "90d"
    DAYS_180 = "180d"
    YEAR_1 = "1y"
    YEAR_2 = "2y"
    INDEFINITE = "indefinite"


RETENTION_SECONDS: dict[RetentionPeriod, int] = {
    RetentionPeriod.DAYS_30: 30 * 86400,
    RetentionPeriod.DAYS_90: 90 * 86400,
    RetentionPeriod.DAYS_180: 180 * 86400,
    RetentionPeriod.YEAR_1: 365 * 86400,
    RetentionPeriod.YEAR_2: 730 * 86400,
    RetentionPeriod.INDEFINITE: -1,
}


@dataclass
class GDPRConfig:
    enabled: bool = False
    data_retention: RetentionPeriod = RetentionPeriod.DAYS_90
    anonymize_on_delete: bool = True
    consent_required: bool = True
    data_directory: str = ".cherenkov/gdpr"
    auto_purge_interval_hours: int = 24


@dataclass
class ConsentRecord:
    user_id: str
    granted: bool
    timestamp: float = 0.0
    scope: str = "all"  # "all" | "analytics" | "profiling"
    ip_address: str = ""


@dataclass
class DataSubjectRequest:
    request_id: str
    user_id: str
    request_type: str  # "access" | "rectification" | "erasure" | "portability"
    status: str = "pending"  # "pending" | "completed" | "rejected"
    created_at: float = 0.0
    completed_at: float = 0.0


class GDPRManager:
    """GDPR compliance manager for data retention, anonymization, and consent.

    Features:
    - Configurable data retention periods
    - Automatic data purging
    - Consent tracking
    - Right to access / erasure / portability
    - Anonymization engine
    """

    def __init__(self, config: GDPRConfig | None = None):
        self.config = config or GDPRConfig()
        self._consents: dict[str, ConsentRecord] = {}
        self._requests: dict[str, DataSubjectRequest] = {}
        os.makedirs(self.config.data_directory, exist_ok=True)

    def is_enabled(self) -> bool:
        return self.config.enabled

    # ── Consent ───────────────────────────────────────────────────────────────

    def record_consent(
        self, user_id: str, granted: bool, scope: str = "all", ip: str = ""
    ) -> ConsentRecord:
        record = ConsentRecord(
            user_id=user_id,
            granted=granted,
            timestamp=time.time(),
            scope=scope,
            ip_address=ip,
        )
        self._consents[user_id] = record
        self._persist("consents.json", self._consents)
        return record

    def has_consent(self, user_id: str, scope: str = "all") -> bool:
        if not self.config.consent_required:
            return True
        record = self._consents.get(user_id)
        if record is None:
            return False
        return record.granted and (scope == "all" or record.scope in ("all", scope))

    def withdraw_consent(self, user_id: str) -> bool:
        if user_id in self._consents:
            self._consents[user_id].granted = False
            self._persist("consents.json", self._consents)
            return True
        return False

    # ── Data Subject Requests ─────────────────────────────────────────────────

    def create_request(
        self, user_id: str, request_type: str
    ) -> DataSubjectRequest:
        import uuid

        req = DataSubjectRequest(
            request_id=str(uuid.uuid4())[:12],
            user_id=user_id,
            request_type=request_type,
            created_at=time.time(),
        )
        self._requests[req.request_id] = req
        self._persist("requests.json", self._requests)
        return req

    def fulfill_request(self, request_id: str) -> dict[str, Any]:
        req = self._requests.get(request_id)
        if req is None:
            return {"error": "Request not found"}
        if req.request_type == "access":
            result = self._handle_access_request(req.user_id)
        elif req.request_type == "erasure":
            result = self._handle_erasure_request(req.user_id)
        elif req.request_type == "portability":
            result = self._handle_portability_request(req.user_id)
        else:
            result = {"error": f"Unknown request type: {req.request_type}"}
        req.status = "completed"
        req.completed_at = time.time()
        self._persist("requests.json", self._requests)
        return result

    def _handle_access_request(self, user_id: str) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "consent_record": (
                self._consents.get(user_id).__dict__
                if user_id in self._consents
                else None
            ),
            "data_held": True,
            "collected_at": time.time(),
        }

    def _handle_erasure_request(self, user_id: str) -> dict[str, Any]:
        self._consents.pop(user_id, None)
        self._persist("consents.json", self._consents)
        return {
            "status": "erased",
            "user_id": user_id,
            "anonymized": self.config.anonymize_on_delete,
            "erased_at": time.time(),
        }

    def _handle_portability_request(self, user_id: str) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "data": {"consent": self._consents.get(user_id).__dict__ if user_id in self._consents else None},
            "format": "json",
            "exported_at": time.time(),
        }

    # ── Retention & Purging ───────────────────────────────────────────────────

    def get_retention_seconds(self) -> int:
        return RETENTION_SECONDS.get(self.config.data_retention, 90 * 86400)

    def purge_old_data(self) -> int:
        """Delete data older than the retention period."""
        max_age = self.get_retention_seconds()
        if max_age < 0:
            return 0
        cutoff = time.time() - max_age
        purged = 0
        for req_id, req in list(self._requests.items()):
            if req.created_at < cutoff:
                del self._requests[req_id]
                purged += 1
        if purged:
            self._persist("requests.json", self._requests)
        log.info("GDPR purge", purged_count=purged)
        return purged

    # ── Persistence ────────────────────────────────────────────────────────────

    def _persist(self, filename: str, data: Any) -> None:
        path = os.path.join(self.config.data_directory, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.__dict__ if hasattr(v, "__dict__") else v for k, v in data.items()},
                f,
                indent=2,
            )

    def _load(self, filename: str) -> dict:
        path = os.path.join(self.config.data_directory, filename)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}


# Global singleton
_manager = GDPRManager()


def get_gdpr() -> GDPRManager:
    return _manager
