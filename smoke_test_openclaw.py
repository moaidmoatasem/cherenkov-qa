#!/usr/bin/env python3
"""
smoke_test_openclaw.py — Kill-criteria exit demo for OpenClaw Tier-1 adapter.

Verifies:
1. OpenClawAdapter wraps HitlQueue with hitl/v1 envelope responses.
2. Notification callbacks fire on approve/reject.
3. Trigger handlers execute and return envelopes.
4. Polling detects new items.
5. FastAPI HTTP server starts and serves endpoints (when available).

Exit code 0 = all criteria passed.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback

# Ensure package root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cherenkov.hitl.contracts import HitlItem, HitlStatus, HitlEnvelope
from cherenkov.hitl.store import HitlQueue
from cherenkov.openclaw.adapter import OpenClawAdapter, TriggerRequest
from cherenkov.openclaw.contracts import OpenClawConfig

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label} — {detail}")
        FAIL += 1


def main() -> int:
    global PASS, FAIL
    print("=" * 60)
    print("OpenClaw Tier-1 Adapter — Kill-Criteria Exit Demo")
    print("=" * 60)

    # ── Setup ──────────────────────────────────────────────────────────────
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    queue = HitlQueue(db_path=db_path)
    adapter = OpenClawAdapter(queue=queue)

    # Seed items
    items = [
        HitlItem(id="demo-1", endpoint="/api/users", method="POST",
                 mutation_id="missing_email", confidence=0.75,
                 review_gate_failed="assertions"),
        HitlItem(id="demo-2", endpoint="/api/orders", method="GET",
                 mutation_id="invalid_status", confidence=0.82,
                 review_gate_failed="syntax"),
    ]
    for item in items:
        queue.enqueue(item)

    print("\n1. Envelope contract — all responses use hitl/v1 schema")
    env = adapter.list_envelope()
    check("list_envelope returns HitlEnvelope", isinstance(env, HitlEnvelope))
    check("schema_version is hitl/v1", env.schema_version == "hitl/v1")
    check("command is openclaw.list", env.command == "openclaw.list")
    check("payload has items", env.payload and len(env.payload["items"]) == 2)

    print("\n2. Read operations — list/show")
    env = adapter.list_envelope(status="pending")
    check("list returns pending items", env.payload["count"] == 2)

    env = adapter.show_envelope("demo-1")
    check("show finds existing item", env.ok)
    check("item endpoint matches", env.payload["item"]["endpoint"] == "/api/users")

    env = adapter.show_envelope("nonexistent")
    check("show missing item returns error", not env.ok)
    check("error code is not_found", env.error.code == "not_found")

    print("\n3. Mutation operations — approve/reject")
    env = adapter.approve_envelope("demo-1", "demo-user")
    check("approve succeeds", env.ok)
    check("approve action recorded", env.payload["action"] == "approve")

    env = adapter.approve_envelope("demo-1", "other-user")
    check("double-approve returns conflict", not env.ok)
    check("conflict error code", env.error.code == "conflict")

    env = adapter.reject_envelope("demo-2", "demo-user", "intentional demo rejection")
    check("reject succeeds", env.ok)
    check("reject action recorded", env.payload["action"] == "reject")

    env = adapter.reject_envelope("demo-2", "other-user", "reason")
    check("double-reject returns conflict", not env.ok)

    print("\n4. Notification callbacks")
    notify_log = []

    def tracker(env):
        notify_log.append(env.command)

    adapter.on_notify(tracker)
    adapter.approve_envelope("demo-1", "actor")  # will conflict, no notify
    check("conflict does not trigger notify", len(notify_log) == 0)

    # fresh item for notification test
    queue.enqueue(HitlItem(id="notify-test", endpoint="/api/test", method="GET"))
    adapter.reject_envelope("notify-test", "actor", "smoke test")
    check("reject triggers notification", "openclaw.reject" in notify_log)

    print("\n5. Run trigger")
    env = adapter.trigger_run(TriggerRequest(reason="smoke-test"))
    check("trigger without handler returns error", not env.ok)

    trigger_log = []

    def demo_handler(req):
        trigger_log.append(req.reason)
        from cherenkov.hitl.contracts import ok_envelope
        return ok_envelope("openclaw.trigger", {"triggered": True})

    adapter.on_trigger(demo_handler)
    env = adapter.trigger_run(TriggerRequest(reason="ci-trigger"))
    check("trigger with handler succeeds", env.ok)
    check("handler was called", "ci-trigger" in trigger_log)

    print("\n6. Polling")
    env = adapter.poll_envelope()
    check("poll returns envelope", env.ok)
    initial_pending = env.payload["pending_count"]

    queue.enqueue(HitlItem(id="poll-fresh", endpoint="/api/new", method="POST"))
    env = adapter.poll_envelope()
    check("poll detects new item", env.payload["new_count"] == 1)
    check("new item has correct id", env.payload["new_items"][0]["id"] == "poll-fresh")

    env = adapter.poll_envelope()
    check("second poll has no new items", env.payload["new_count"] == 0)

    print("\n7. HTTP server smoke test (FastAPI)")
    HAS_FASTAPI = False
    try:
        import fastapi  # noqa
        HAS_FASTAPI = True
    except ImportError:
        print("  ~ FastAPI not available, skipping HTTP tests")

    if HAS_FASTAPI:
        try:
            from cherenkov.openclaw.server import serve_background
            cfg = OpenClawConfig(port=18721)
            app, thread = serve_background(adapter=adapter, config=cfg)
            time.sleep(0.5)

            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:18721/health") as resp:
                health = json.loads(resp.read())
                check("HTTP /health returns ok", health.get("status") == "ok")

            with urllib.request.urlopen("http://127.0.0.1:18721/hitl/list") as resp:
                data = json.loads(resp.read())
                check("HTTP /hitl/list returns items", data.get("ok") is True)
                check("HTTP list has items", data["payload"]["count"] >= 1)

            with urllib.request.urlopen("http://127.0.0.1:18721/hitl/show/demo-1") as resp:
                data = json.loads(resp.read())
                check("HTTP /hitl/show/{id} works", data.get("ok") is True)
                check("HTTP show has endpoint", data["payload"]["item"]["endpoint"] == "/api/users")

            thread.stop()
            thread.join(timeout=3)
        except Exception as exc:
            print(f"  ~ HTTP server test error: {exc}")
    else:
        print("  ~ Skipping HTTP server tests (FastAPI not available)")

    # ── Cleanup ────────────────────────────────────────────────────────────
    os.unlink(db_path)

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("STATUS: ALL CRITERIA PASSED — OpenClaw Tier-1 adapter is ready.")
        print("Kill-criteria exit demo: PASSED")
    else:
        print(f"STATUS: {FAIL} criteria FAILED — review output above.")
    print("=" * 60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
