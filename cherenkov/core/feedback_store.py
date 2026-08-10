"""
cherenkov/core/feedback_store.py

Records structured feedback for rejected or approved HITL findings to seed the learning loop.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RejectionReason:
    """Standard enumeration of rejection reason codes for feedback processing."""

    INTENDED_CHANGE = "intended_change"
    TOO_NOISY = "too_noisy"
    WRONG_ASSERTION = "wrong_assertion"
    ENV_ISSUE = "env_issue"
    OTHER = "other"

    @classmethod
    def choices(cls) -> list[str]:
        """Return list of valid rejection reason strings.

        Returns:
            list[str]: List of valid choice strings.
        """
        return [cls.INTENDED_CHANGE, cls.TOO_NOISY, cls.WRONG_ASSERTION, cls.ENV_ISSUE, cls.OTHER]


@dataclass
class FeedbackEntry:
    """Feedback entry record for an approved or rejected HITL item."""

    hitl_item_id: str
    action: str  # "reject" or "approve"
    reason: str | None = None
    notes: str | None = None


class FeedbackStore:
    """JSON-backed persistent store for HITL user feedback entries."""

    def __init__(self, store_path: str | Path = ".cherenkov/feedback.json"):
        """Initialize FeedbackStore.

        Args:
            store_path (str | Path, optional): Path to JSON feedback storage file. Defaults to ".cherenkov/feedback.json".
        """
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def record_feedback(self, entry: FeedbackEntry) -> None:
        """Record a new feedback entry to disk.

        Args:
            entry (FeedbackEntry): Feedback entry data object.

        Returns:
            None
        """
        try:
            with open(self.store_path, encoding="utf-8") as f:
                data = json.load(f)

            data.append(asdict(entry))

            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info(
                "Recorded feedback for %s (action: %s)", entry.hitl_item_id, entry.action
            )
        except Exception as e:
            logger.error("Failed to record feedback: %s", e)

    def get_all(self) -> list[FeedbackEntry]:
        """Retrieve all recorded feedback entries.

        Returns:
            list[FeedbackEntry]: List of feedback entry instances.
        """
        try:
            if not self.store_path.exists():
                return []
            with open(self.store_path, encoding="utf-8") as f:
                data = json.load(f)
            return [FeedbackEntry(**item) for item in data]
        except Exception as e:
            logger.error("Failed to read feedback store: %s", e)
            return []

