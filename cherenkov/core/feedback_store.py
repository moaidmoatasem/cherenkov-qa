"""
cherenkov/core/feedback_store.py

Records structured feedback for rejected or approved HITL findings to seed the learning loop.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RejectionReason:
    INTENDED_CHANGE = "intended_change"
    TOO_NOISY = "too_noisy"
    WRONG_ASSERTION = "wrong_assertion"
    OTHER = "other"


@dataclass
class FeedbackEntry:
    hitl_item_id: str
    action: str  # "reject" or "approve"
    reason: str | None = None
    notes: str | None = None


class FeedbackStore:
    def __init__(self, store_path: str | Path = ".cherenkov/feedback.json"):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            with open(self.store_path, "w") as f:
                json.dump([], f)

    def record_feedback(self, entry: FeedbackEntry) -> None:
        try:
            with open(self.store_path) as f:
                data = json.load(f)

            data.append(asdict(entry))

            with open(self.store_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(
                "Recorded feedback for %s (action: %s)", entry.hitl_item_id, entry.action
            )
        except Exception as e:
            logger.error("Failed to record feedback: %s", e)

    def get_all(self) -> list[FeedbackEntry]:
        try:
            if not self.store_path.exists():
                return []
            with open(self.store_path) as f:
                data = json.load(f)
            return [FeedbackEntry(**item) for item in data]
        except Exception as e:
            logger.error("Failed to read feedback store: %s", e)
            return []
