"""Unit tests for cherenkov/core/feedback_store.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cherenkov.core.feedback_store import FeedbackStore, FeedbackEntry, RejectionReason


class TestFeedbackStoreInit:
    def test_creates_store_file_on_init(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sub" / "feedback.json"
            store = FeedbackStore(path)
            assert path.exists()
            assert json.loads(path.read_text()) == []

    def test_existing_store_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "feedback.json"
            path.write_text(json.dumps([{"hitl_item_id": "existing"}]))
            store = FeedbackStore(path)
            data = json.loads(path.read_text())
            assert len(data) == 1


class TestRecordFeedback:
    def _store(self):
        d = tempfile.mkdtemp()
        return FeedbackStore(Path(d) / "feedback.json"), d

    def test_record_approve(self):
        store, _ = self._store()
        entry = FeedbackEntry(hitl_item_id="item-1", action="approve")
        store.record_feedback(entry)
        entries = store.get_all()
        assert len(entries) == 1
        assert entries[0].action == "approve"

    def test_record_reject_with_reason(self):
        store, _ = self._store()
        entry = FeedbackEntry(
            hitl_item_id="item-2",
            action="reject",
            reason=RejectionReason.TOO_NOISY,
            notes="False positive on /health",
        )
        store.record_feedback(entry)
        entries = store.get_all()
        assert entries[0].reason == RejectionReason.TOO_NOISY
        assert entries[0].notes == "False positive on /health"

    def test_multiple_entries_accumulate(self):
        store, _ = self._store()
        for i in range(5):
            store.record_feedback(FeedbackEntry(hitl_item_id=f"item-{i}", action="approve"))
        assert len(store.get_all()) == 5

    def test_entries_persisted_across_instances(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "feedback.json"
            store1 = FeedbackStore(path)
            store1.record_feedback(FeedbackEntry(hitl_item_id="x", action="reject"))
            store2 = FeedbackStore(path)
            assert len(store2.get_all()) == 1


class TestGetAll:
    def test_empty_store_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            store = FeedbackStore(Path(d) / "feedback.json")
            assert store.get_all() == []

    def test_returns_feedback_entry_objects(self):
        with tempfile.TemporaryDirectory() as d:
            store = FeedbackStore(Path(d) / "feedback.json")
            store.record_feedback(FeedbackEntry(hitl_item_id="a", action="approve"))
            entries = store.get_all()
            assert all(isinstance(e, FeedbackEntry) for e in entries)


class TestRejectionReason:
    def test_constants_defined(self):
        assert RejectionReason.INTENDED_CHANGE == "intended_change"
        assert RejectionReason.TOO_NOISY == "too_noisy"
        assert RejectionReason.WRONG_ASSERTION == "wrong_assertion"
        assert RejectionReason.OTHER == "other"
