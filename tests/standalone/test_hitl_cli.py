"""
test_hitl_cli.py — unit tests for cherenkov/hitl/cmd.py (A1 #109).

Tests the list/show/approve/reject handlers in isolation using an in-memory DB.
Verifies:
  - Human and JSON output paths
  - Actor defaulting to $USER
  - not_found and conflict error codes
  - Return code semantics (0=success, 1=error)
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from cherenkov.hitl import HitlItem, HitlQueue, SCHEMA_VERSION
from cherenkov.hitl.cmd import (
    run_list,
    run_show,
    run_approve,
    run_reject,
    _default_actor,
)


# ── fixture ───────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_db(tmp_path) -> str:
    return str(tmp_path / "hitl_test.db")


@pytest.fixture
def queue_with_items(tmp_db) -> tuple[HitlQueue, list[str]]:
    """Returns a HitlQueue with 2 pending items pre-loaded."""
    q = HitlQueue(db_path=tmp_db)
    ids = ["item_alpha", "item_beta"]
    q.enqueue(
        HitlItem(
            id=ids[0],
            endpoint="/users",
            method="POST",
            mutation_label="Missing required field",
            confidence=0.82,
            review_gate_failed="gate_ast",
            run_id="run_001",
        )
    )
    q.enqueue(
        HitlItem(
            id=ids[1],
            endpoint="/orders",
            method="GET",
            mutation_label="Status enum violation",
            confidence=0.75,
            review_gate_failed="gate_assertions",
            run_id="run_002",
        )
    )
    return q, ids


# ── _default_actor ─────────────────────────────────────────────────────────────


def test_default_actor_uses_user_env():
    with patch.dict(os.environ, {"USER": "tester_user"}):
        assert _default_actor() == "tester_user"


def test_default_actor_fallback_to_username():
    # Remove USER if set, set USERNAME
    env_copy = {k: v for k, v in os.environ.items() if k != "USER"}
    env_copy["USERNAME"] = "win_user"
    with patch.dict(os.environ, env_copy, clear=True):
        result = _default_actor()
    assert result in ("win_user", os.environ.get("USER", "win_user"))


# ── run_list ───────────────────────────────────────────────────────────────────


def test_list_empty_db(tmp_db, capsys):
    rc = run_list(status="pending", json_out=False, db_path=tmp_db)
    assert rc == 0
    out = capsys.readouterr().out
    assert "empty" in out or "0 item" in out


def test_list_pending_items(queue_with_items, capsys):
    q, ids = queue_with_items
    rc = run_list(status="pending", json_out=False, db_path=q.db_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "item_alpha" in out
    assert "item_beta" in out


def test_list_json_envelope_shape(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(HitlItem(id="j1", endpoint="/x", method="GET"))
    rc = run_list(status="pending", json_out=True, db_path=tmp_db)
    assert rc == 0
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["ok"] is True
    assert data["command"] == "hitl.list"
    assert data["payload"]["count"] == 1
    assert data["payload"]["items"][0]["id"] == "j1"


def test_list_all_statuses(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(HitlItem(id="a1", endpoint="/x", method="GET"))
    q.approve("a1", "@tester")
    q.enqueue(HitlItem(id="p1", endpoint="/y", method="POST"))

    # all statuses
    rc = run_list(status=None, json_out=True, db_path=tmp_db)
    assert rc == 0
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert data["payload"]["count"] == 2


# ── run_show ───────────────────────────────────────────────────────────────────


def test_show_found_human(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(
        HitlItem(id="show_me", endpoint="/pets", method="DELETE", confidence=0.78)
    )
    rc = run_show("show_me", json_out=False, db_path=tmp_db)
    assert rc == 0
    out = capsys.readouterr().out
    assert "show_me" in out
    assert "/pets" in out


def test_show_found_json(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(HitlItem(id="show_json", endpoint="/items", method="PUT"))
    rc = run_show("show_json", json_out=True, db_path=tmp_db)
    assert rc == 0
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert data["ok"] is True
    assert data["command"] == "hitl.show"
    assert data["payload"]["item"]["id"] == "show_json"


def test_show_not_found_returns_1(tmp_db, capsys):
    rc = run_show("does_not_exist", json_out=False, db_path=tmp_db)
    assert rc == 1


def test_show_not_found_json_envelope(tmp_db, capsys):
    rc = run_show("ghost", json_out=True, db_path=tmp_db)
    assert rc == 1
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert data["ok"] is False
    assert data["error"]["code"] == "not_found"


# ── run_approve ────────────────────────────────────────────────────────────────


def test_approve_success(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(HitlItem(id="appr_1", endpoint="/users", method="POST"))
    rc = run_approve("appr_1", actor="@alice", json_out=False, db_path=tmp_db)
    assert rc == 0
    # Verify DB state
    item = q.get("appr_1")
    assert item.status.value == "approved"
    assert item.approved_by == "@alice"


def test_approve_json_envelope(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(HitlItem(id="appr_j", endpoint="/x", method="GET"))
    rc = run_approve("appr_j", actor="@bob", json_out=True, db_path=tmp_db)
    assert rc == 0
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["ok"] is True
    assert data["command"] == "hitl.approve"
    assert data["payload"]["rows_affected"] == 1
    assert data["payload"]["actor"] == "@bob"


def test_approve_conflict_returns_1(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(HitlItem(id="appr_c", endpoint="/x", method="GET"))
    q.approve("appr_c", "@alice")
    # Bob tries to approve again
    rc = run_approve("appr_c", actor="@bob", json_out=True, db_path=tmp_db)
    assert rc == 1
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert data["ok"] is False
    assert data["error"]["code"] == "conflict"
    assert data["error"]["detail"]["current_actor"] == "@alice"


def test_approve_not_found_returns_1(tmp_db, capsys):
    rc = run_approve("ghost_id", actor="@x", json_out=True, db_path=tmp_db)
    assert rc == 1
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert data["error"]["code"] == "not_found"


def test_approve_uses_default_actor(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(HitlItem(id="default_actor_test", endpoint="/y", method="DELETE"))
    with patch.dict(os.environ, {"USER": "env_actor"}):
        rc = run_approve(
            "default_actor_test", actor=None, json_out=True, db_path=tmp_db
        )
    assert rc == 0
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert data["payload"]["actor"] == "env_actor"


# ── run_reject ─────────────────────────────────────────────────────────────────


def test_reject_success(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(HitlItem(id="rej_1", endpoint="/z", method="PATCH"))
    rc = run_reject(
        "rej_1",
        reason="spec_says_422_not_400",
        actor="@carol",
        json_out=False,
        db_path=tmp_db,
    )
    assert rc == 0
    item = q.get("rej_1")
    assert item.status.value == "rejected"
    assert item.reject_reason == "spec_says_422_not_400"
    assert item.approved_by == "@carol"


def test_reject_json_envelope(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(HitlItem(id="rej_j", endpoint="/a", method="GET"))
    rc = run_reject(
        "rej_j", reason="false_positive", actor="@dave", json_out=True, db_path=tmp_db
    )
    assert rc == 0
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert data["ok"] is True
    assert data["command"] == "hitl.reject"


def test_reject_conflict_returns_1(tmp_db, capsys):
    q = HitlQueue(db_path=tmp_db)
    q.enqueue(HitlItem(id="rej_c", endpoint="/b", method="POST"))
    q.reject("rej_c", "@alice", "fp")
    rc = run_reject(
        "rej_c", reason="also_fp", actor="@bob", json_out=True, db_path=tmp_db
    )
    assert rc == 1
    raw = capsys.readouterr().out
    data = json.loads(raw)
    assert data["error"]["code"] == "conflict"
