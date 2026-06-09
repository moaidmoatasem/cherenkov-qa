#!/usr/bin/env python3
"""smoke_test_golden_path.py — Golden-path E2E smoke (Issue 177).

Uses FastAPI TestClient against cherenkov/web/api.py. Exercises every
review API endpoint against a live HitlQueue. Exit 0 = all checks pass.
"""
from __future__ import annotations

import os, sys, json
from fastapi.testclient import TestClient

import tempfile
_db_dir = tempfile.mkdtemp()
_db_path = os.path.join(_db_dir, "gp.db")
os.environ["CHERENKOV_HITL_DB"] = _db_path

from cherenkov.hitl import HitlItem, HitlQueue
from cherenkov.web.api import app

client = TestClient(app)


def main() -> int:
    c: dict[str, bool] = {}

    # Seed via a direct HitlQueue before touching the API
    q = HitlQueue(db_path=_db_path)
    for item in [
        HitlItem(id="g1", endpoint="/pet/findByStatus", method="GET",
                 confidence=0.78, confidence_reason="Accepted invalid status",
                 review_gate_failed="gate_assertions", run_id="r1"),
        HitlItem(id="g2", endpoint="/pet/{petId}", method="GET",
                 confidence=0.65, confidence_reason="404 body missing",
                 review_gate_failed="gate_ast", run_id="r1"),
        HitlItem(id="g3", endpoint="/store/order", method="POST",
                 confidence=0.92, confidence_reason="Unexpected status",
                 review_gate_failed="gate_quality", run_id="r1"),
    ]:
        q.enqueue(item)
    c["seed: 3 items"] = len(q.list()) == 3

    r = client.get("/api/v1/health")
    c["health: 200"] = r.status_code == 200
    c["health: body ok"] = r.json().get("status") == "online"

    r = client.get("/api/v1/review/queue?status=pending")
    c["queue: 200"] = r.status_code == 200
    d = r.json()
    c["queue: is list"] = isinstance(d, list)
    c["queue: 3 items"] = len(d) == 3
    if d:
        it = d[0]
        c["queue: has id"] = "id" in it
        c["queue: has endpoint"] = "endpoint" in it
        c["queue: has method"] = "method" in it
        c["queue: has confidence"] = "confidence" in it
        c["queue: has confidence_reason"] = "confidence_reason" in it

    r = client.post("/api/v1/review/approve", json={"scenario_id": "g1"})
    c["approve: 200"] = r.status_code == 200
    c["approve: approved"] = r.json().get("status") == "approved"

    r = client.get("/api/v1/review/queue?status=pending")
    c["approve: 2 pending"] = len(r.json()) == 2

    r = client.post("/api/v1/review/reject", json={
        "scenario_id": "g2", "reason": "Intended"
    })
    c["reject: 200"] = r.status_code == 200
    c["reject: rejected"] = r.json().get("status") == "rejected"

    r = client.get("/api/v1/review/queue?status=pending")
    c["reject: 1 pending"] = len(r.json()) == 1

    r = client.post("/api/v1/review/classify", json={
        "item_id": "g3", "classification": "regression"
    })
    c["classify: 200"] = r.status_code == 200
    c["classify: classified"] = r.json().get("status") == "classified"

    r = client.get("/api/v1/review/queue?status=pending")
    c["classify: 0 pending"] = len(r.json()) == 0

    r = client.get("/api/v1/divergences")
    c["divergences: 200"] = r.status_code == 200
    c["divergences: non-empty"] = len(r.json()) > 0

    r = client.post("/api/v1/review/edit", json={
        "scenario_id": "golden_edit", "test_code": "// test\n"
    })
    c["edit: 200"] = r.status_code == 200

    r = client.post("/api/v1/divergences/act", json={
        "divergence_id": "D-01", "action": "close_with_test"
    })
    c["act: 200"] = r.status_code == 200
    c["act: ok"] = r.json().get("status") == "ok"

    r = client.get("/api/v1/tests")
    c["tests: 200"] = r.status_code == 200
    c["tests: is list"] = isinstance(r.json(), list)

    import shutil
    shutil.rmtree(_db_dir, ignore_errors=True)

    fails = [k for k, v in c.items() if not v]
    n = len(c)
    if fails:
        print(f"\nFAIL: {len(fails)}/{n} checks failed:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"\nPASS: all {n} checks passed - golden path OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
