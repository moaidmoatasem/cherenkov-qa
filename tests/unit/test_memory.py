"""Tests for cherenkov.memory — auto-memory engine (CC-1, ADR-011)."""
from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cherenkov.memory.adapters.sqlite_memory import SQLiteMemoryRepository, get_default_repository
from cherenkov.memory.domain.models import (
    EntryKind,
    MemoryEntry,
    MemoryPattern,
    MemoryQuery,
    PromotionRule,
)
from cherenkov.memory.use_cases.collect import collect_from_findings
from cherenkov.memory.use_cases.promote import run_promotion


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_repo(tmp_path: Path) -> SQLiteMemoryRepository:
    """Fresh in-memory-like repo backed by a tmp file."""
    return SQLiteMemoryRepository(tmp_path / "test_memory.db")


def _entry(
    content: str = "test finding",
    kind: EntryKind = EntryKind.FINDING,
    session_id: str = "sess_test_001",
    task_type: str = "unit_test",
) -> MemoryEntry:
    return MemoryEntry(
        id=str(uuid.uuid4()),
        session_id=session_id,
        task_type=task_type,
        kind=kind,
        content=content,
        created_at=datetime.now(tz=timezone.utc),
    )


# ── SQLiteMemoryRepository ────────────────────────────────────────────


class TestSQLiteMemoryRepository:
    def test_save_and_search_by_keyword(self, tmp_repo: SQLiteMemoryRepository) -> None:
        """Saved entries are retrievable via FTS5 search."""
        entry = _entry("ollama client fails on cold start")
        tmp_repo.save_entry(entry)

        results = tmp_repo.search(MemoryQuery(query="ollama cold"))
        assert len(results) == 1
        assert results[0].id == entry.id

    def test_search_returns_empty_on_miss(self, tmp_repo: SQLiteMemoryRepository) -> None:
        tmp_repo.save_entry(_entry("completely unrelated content"))
        results = tmp_repo.search(MemoryQuery(query="xyzzy_nonexistent"))
        assert results == []

    def test_filter_by_task_type(self, tmp_repo: SQLiteMemoryRepository) -> None:
        tmp_repo.save_entry(_entry("api test finding", task_type="api_test"))
        tmp_repo.save_entry(_entry("mobile finding", task_type="mobile"))

        results = tmp_repo.search(MemoryQuery(task_type="mobile"))
        assert all(e.task_type == "mobile" for e in results)
        assert len(results) == 1

    def test_filter_by_kind(self, tmp_repo: SQLiteMemoryRepository) -> None:
        tmp_repo.save_entry(_entry("pitfall: always use timeout", kind=EntryKind.PITFALL))
        tmp_repo.save_entry(_entry("decision: use sqlite", kind=EntryKind.DECISION))

        results = tmp_repo.search(MemoryQuery(kind=EntryKind.PITFALL))
        assert len(results) == 1
        assert results[0].kind == EntryKind.PITFALL

    def test_save_and_retrieve_promoted_pattern(self, tmp_repo: SQLiteMemoryRepository) -> None:
        pattern = MemoryPattern(
            fingerprint="abc123",
            content="Always run ruff before commit",
            first_seen_session="sess_001",
            last_seen_session="sess_003",
            session_count=3,
            task_types=["review"],
            is_auto_loaded=False,
        )
        tmp_repo.upsert_pattern(pattern)
        tmp_repo.promote_pattern("abc123")

        promoted = tmp_repo.get_promoted()
        assert len(promoted) == 1
        assert promoted[0].fingerprint == "abc123"
        assert promoted[0].is_auto_loaded is True

    def test_upsert_pattern_merges_session_count(self, tmp_repo: SQLiteMemoryRepository) -> None:
        """Upserting the same fingerprint twice increments session count."""
        pattern = MemoryPattern(
            fingerprint="dup001",
            content="test pattern",
            first_seen_session="sess_001",
            last_seen_session="sess_001",
            session_count=2,
            task_types=["task_a"],
        )
        tmp_repo.upsert_pattern(pattern)

        updated = MemoryPattern(
            fingerprint="dup001",
            content="test pattern",
            first_seen_session="sess_001",
            last_seen_session="sess_004",
            session_count=4,
            task_types=["task_b"],
        )
        tmp_repo.upsert_pattern(updated)

        result = tmp_repo.get_pattern("dup001")
        assert result is not None
        assert result.session_count == 4
        assert set(result.task_types) == {"task_a", "task_b"}

    def test_apply_promotion_rules_promotes_eligible(self, tmp_repo: SQLiteMemoryRepository) -> None:
        """Patterns with session_count >= threshold are auto-promoted."""
        for i, count in enumerate([1, 2, 3, 5]):
            tmp_repo.upsert_pattern(
                MemoryPattern(
                    fingerprint=f"p{i}",
                    content=f"pattern {i}",
                    first_seen_session=f"sess_{i}",
                    last_seen_session=f"sess_{i}",
                    session_count=count,
                    task_types=["t"],
                )
            )

        promoted = tmp_repo.apply_promotion_rules(PromotionRule(min_session_count=3))
        assert set(promoted) == {"p2", "p3"}

        # Confirm they are now auto-loaded
        auto_loaded = tmp_repo.get_promoted()
        fingerprints = {p.fingerprint for p in auto_loaded}
        assert fingerprints == {"p2", "p3"}

    def test_get_default_repository_creates_db(self, tmp_path: Path) -> None:
        repo = get_default_repository(tmp_path)
        db_path = tmp_path / "agent_memory" / "cherenkov_memory.db"
        assert db_path.exists()


# ── collect_from_findings ─────────────────────────────────────────────


class TestCollectFromFindings:
    def test_saves_all_findings_as_entries(self, tmp_repo: SQLiteMemoryRepository) -> None:
        findings = [
            {"type": "finding", "message": "endpoint returns 400 not 422"},
            {"type": "decision", "message": "use openapi-fetch only"},
            {"type": "pitfall", "message": "never run git add -A blindly"},
        ]
        saved = collect_from_findings(
            session_id="sess_001",
            task_type="cc1_test",
            findings=findings,
            repo=tmp_repo,
        )
        assert len(saved) == 3

        all_entries = tmp_repo.search(MemoryQuery(limit=50))
        assert len(all_entries) == 3

    def test_extracts_pattern_for_pitfall_and_decision(
        self, tmp_repo: SQLiteMemoryRepository
    ) -> None:
        """Pitfalls and decisions are auto-extracted into patterns."""
        findings = [
            {"type": "pitfall", "message": "ollama cold start takes 2s, add retry"},
            {"type": "finding", "message": "plain finding, no pattern"},
        ]
        collect_from_findings(
            session_id="sess_002",
            task_type="api",
            findings=findings,
            repo=tmp_repo,
        )
        patterns = tmp_repo.list_patterns()
        assert len(patterns) == 1
        assert "ollama" in patterns[0].content


# ── run_promotion ─────────────────────────────────────────────────────


class TestRunPromotion:
    def test_promotes_above_threshold(self, tmp_repo: SQLiteMemoryRepository) -> None:
        tmp_repo.upsert_pattern(
            MemoryPattern(
                fingerprint="eligible",
                content="runs ruff before every commit",
                first_seen_session="s1",
                last_seen_session="s3",
                session_count=3,
                task_types=["review"],
            )
        )
        promoted = run_promotion(tmp_repo, PromotionRule(min_session_count=3))
        assert "eligible" in promoted

    def test_does_not_promote_below_threshold(self, tmp_repo: SQLiteMemoryRepository) -> None:
        tmp_repo.upsert_pattern(
            MemoryPattern(
                fingerprint="too_few",
                content="only seen twice",
                first_seen_session="s1",
                last_seen_session="s2",
                session_count=2,
                task_types=["any"],
            )
        )
        promoted = run_promotion(tmp_repo, PromotionRule(min_session_count=3))
        assert promoted == []

    def test_already_promoted_not_re_promoted(self, tmp_repo: SQLiteMemoryRepository) -> None:
        tmp_repo.upsert_pattern(
            MemoryPattern(
                fingerprint="already",
                content="already promoted",
                first_seen_session="s1",
                last_seen_session="s5",
                session_count=10,
                task_types=["x"],
                is_auto_loaded=True,
            )
        )
        promoted = run_promotion(tmp_repo)
        assert "already" not in promoted
