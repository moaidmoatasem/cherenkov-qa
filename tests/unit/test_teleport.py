"""Tests for Teleport Session Store (CC-5)."""
from __future__ import annotations

import datetime

import pytest

from cherenkov.continuity.sessions.adapters.sqlite_sessions import SQLiteSessionStore
from cherenkov.continuity.sessions.domain.models import SessionSnapshot, TeleportToken
from cherenkov.continuity.sessions.use_cases.resume import ResumeSessionUseCase
from cherenkov.continuity.sessions.use_cases.snapshot import SnapshotSessionUseCase


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_sessions.db"
    return SQLiteSessionStore(db_path=str(db_path))


def test_snapshot_and_resume_lifecycle(store):
    snapshot_uc = SnapshotSessionUseCase(store)
    resume_uc = ResumeSessionUseCase(store)

    session_id = "sess_12345"
    state_data = {"key": "value"}

    # Take snapshot
    snapshot = snapshot_uc.execute(session_id, state_data)
    assert snapshot.id == session_id
    assert snapshot.state_data == state_data
    assert snapshot.token is not None
    assert snapshot.token.token is not None

    # Load via ID
    loaded_by_id = store.load(session_id)
    assert loaded_by_id is not None
    assert loaded_by_id.id == session_id

    # List
    sessions = store.list_sessions()
    assert len(sessions) == 1

    # Resume via Token
    resumed = resume_uc.execute_by_token(snapshot.token.token)
    assert resumed is not None
    assert resumed.id == session_id
    assert resumed.state_data == state_data

    # Token should be invalidated
    resumed_again = resume_uc.execute_by_token(snapshot.token.token)
    assert resumed_again is None


def test_expired_token(store):
    # Manually create snapshot with expired token
    session_id = "sess_expired"
    token = TeleportToken(token="expired_token", expires_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=1))
    snapshot = SessionSnapshot(id=session_id, token=token, state_data={})
    store.save(snapshot)

    resume_uc = ResumeSessionUseCase(store)
    resumed = resume_uc.execute_by_token("expired_token")
    assert resumed is None

