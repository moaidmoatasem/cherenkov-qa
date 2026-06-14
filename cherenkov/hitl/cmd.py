"""
CHERENKOV hitl/cmd.py — terminal CLI command handlers for the HITL queue.

Called by the top-level `cherenkov hitl <sub>` subcommand.
All output paths support --json for machine-readable `hitl/v1` envelope emission.

Design:
  - Thin wrappers over HitlQueue; no business logic here.
  - --json flag prints the frozen hitl/v1 HitlEnvelope as JSON.
  - Human output is a simple table/detail view; no colour codes (stays greppable).
  - Actor defaults to $USER environment variable if --actor is omitted.
"""

from __future__ import annotations

import json
import os
import sys

from cherenkov.hitl.contracts import (
    HitlEnvelope,
    HitlItem,
    err_envelope,
    ok_envelope,
)
from cherenkov.hitl.store import HitlQueue


# ── helpers ───────────────────────────────────────────────────────────────────


def _default_actor() -> str:
    """Return $USER env var, or 'unknown' if not set."""
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))


def _emit(envelope: HitlEnvelope, json_out: bool) -> None:
    """Print envelope as JSON or human-readable."""
    if json_out:
        print(json.dumps(envelope.model_dump(), indent=2, default=str))
    else:
        if envelope.ok:
            print(f"[OK] {envelope.command}")
            if envelope.payload:
                for k, v in envelope.payload.items():
                    print(f"  {k}: {v}")
        else:
            print(
                f"[ERROR] {envelope.command} — {envelope.error.code}: {envelope.error.message}",
                file=sys.stderr,
            )
            if envelope.error.detail:
                for k, v in envelope.error.detail.items():
                    print(f"  {k}: {v}", file=sys.stderr)


def _item_row(item: HitlItem) -> str:
    """One-line summary of a HitlItem for list output."""
    conf = f"{item.confidence:.2f}" if item.confidence is not None else "—"
    gate = item.review_gate_failed or "—"
    return (
        f"  {item.id:<36}  {item.status.value:<10}  "
        f"conf={conf}  gate={gate}  "
        f"{item.method or '?'} {item.endpoint or '?'}"
    )


def _item_detail(item: HitlItem) -> None:
    """Multi-line item detail for `show`."""
    print(f"  id              : {item.id}")
    print(f"  status          : {item.status.value}")
    print(f"  endpoint        : {item.method} {item.endpoint}")
    print(f"  mutation_id     : {item.mutation_id}")
    print(f"  mutation_label  : {item.mutation_label}")
    print(f"  confidence      : {item.confidence}")
    print(f"  confidence_reason: {item.confidence_reason}")
    print(f"  review_gate_failed: {item.review_gate_failed}")
    print(f"  run_id          : {item.run_id}")
    print(f"  spec_hash       : {item.spec_hash}")
    print(f"  created_at      : {item.created_at}")
    print(f"  approved_by     : {item.approved_by}")
    print(f"  approved_at     : {item.approved_at}")
    print(f"  reject_reason   : {item.reject_reason}")


# ── public command handlers ────────────────────────────────────────────────────


def run_list(
    status: str | None = "pending", json_out: bool = False, db_path: str | None = None
) -> int:
    """
    List HITL queue items.

    Args:
        status:   Filter by status string; None means all statuses.
        json_out: Emit JSON envelope instead of human table.
        db_path:  Override default DB path (used in tests).

    Returns:
        0 on success.
    """
    q = HitlQueue(db_path=db_path)
    items = q.list(status=status)

    if json_out:
        payload = {
            "status_filter": status,
            "count": len(items),
            "items": [i.model_dump() for i in items],
        }
        env = ok_envelope("hitl.list", payload)
        print(json.dumps(env.model_dump(), indent=2, default=str))
    else:
        label = status or "all"
        print(f"HITL queue — {label} ({len(items)} item(s))")
        if items:
            print(f"  {'id':<36}  {'status':<10}  info")
            print(f"  {'-'*36}  {'-'*10}  ----")
            for item in items:
                print(_item_row(item))
        else:
            print("  (empty)")
    return 0


def run_show(item_id: str, json_out: bool = False, db_path: str | None = None) -> int:
    """
    Show details of a single HITL item.

    Returns:
        0 if found, 1 if not found.
    """
    q = HitlQueue(db_path=db_path)
    item = q.get(item_id)

    if json_out:
        if item is None:
            env = err_envelope(
                "hitl.show", "not_found", f"{item_id} not found.", {"id": item_id}
            )
            print(json.dumps(env.model_dump(), indent=2, default=str))
            return 1
        env = ok_envelope("hitl.show", {"id": item_id, "item": item.model_dump()})
        print(json.dumps(env.model_dump(), indent=2, default=str))
    else:
        if item is None:
            print(f"[ERROR] Item not found: {item_id}", file=sys.stderr)
            return 1
        print(f"HITL item: {item_id}")
        _item_detail(item)
    return 0


def run_approve(
    item_id: str,
    actor: str | None = None,
    json_out: bool = False,
    db_path: str | None = None,
) -> int:
    """
    Approve a pending HITL item.

    Returns:
        0 on success, 1 on conflict/not_found.
    """
    resolved_actor = actor or _default_actor()
    q = HitlQueue(db_path=db_path)
    env = q.approve(item_id=item_id, actor=resolved_actor, source="cli")
    _emit(env, json_out)
    return 0 if env.ok else 1


def run_reject(
    item_id: str,
    reason: str,
    actor: str | None = None,
    json_out: bool = False,
    db_path: str | None = None,
) -> int:
    """
    Reject a pending HITL item with a reason.

    Returns:
        0 on success, 1 on conflict/not_found.
    """
    resolved_actor = actor or _default_actor()
    q = HitlQueue(db_path=db_path)
    env = q.reject(item_id=item_id, actor=resolved_actor, reason=reason, source="cli")
    _emit(env, json_out)
    return 0 if env.ok else 1


def run_classify(
    item_id: str,
    classification: str,
    actor: str | None = None,
    detail: str = "",
    json_out: bool = False,
    db_path: str | None = None,
) -> int:
    """
    Classify a HITL item as regression, intended, or ignore (Tier-2 #150).

    Uses the OpenClaw adapter's classify_envelope for CQRS threshold tracking.
    """
    from cherenkov.openclaw.adapter import OpenClawAdapter
    from cherenkov.openclaw.contracts import ClassificationRequest

    resolved_actor = actor or _default_actor()
    adapter = OpenClawAdapter()
    req = ClassificationRequest(
        item_id=item_id,
        classification=classification,
        actor=resolved_actor,
        detail=detail,
    )
    env = adapter.classify_envelope(req)
    _emit(env, json_out)
    return 0 if env.ok else 1


def run_explain(
    item_id: str, json_out: bool = False, db_path: str | None = None
) -> int:
    """
    Get an AI explanation for why the HITL item was flagged.
    """
    from cherenkov.openclaw.adapter import OpenClawAdapter
    from cherenkov.openclaw.feedback import HealingFeedbackStore

    q = HitlQueue(db_path=db_path)
    if db_path:
        feedback_store = HealingFeedbackStore(db_path=":memory:")
        adapter = OpenClawAdapter(queue=q, feedback_store=feedback_store)
    else:
        adapter = OpenClawAdapter(queue=q)

    env = adapter.explain_envelope(item_id)
    if json_out:
        print(json.dumps(env.model_dump(), indent=2, default=str))
    else:
        if env.ok:
            print(env.payload["explanation"])
        else:
            print(f"[ERROR] {env.error.message}", file=sys.stderr)
    return 0 if env.ok else 1
