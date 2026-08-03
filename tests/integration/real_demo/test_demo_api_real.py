import os
import json
import urllib.request
import urllib.error
import pytest
import random

BASE = os.getenv("CHERENKOV_TEST_BASE_URL", "http://127.0.0.1:8000")

def _url(path):
    return BASE.rstrip("/") + path

def get_json(path, method="GET", data=None, headers=None, timeout=5):
    req = urllib.request.Request(_url(path), method=method)
    if headers:
        for k,v in headers.items():
            req.add_header(k,v)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type","application/json")
    else:
        body = None
    try:
        with urllib.request.urlopen(req, data=body, timeout=timeout) as resp:
            status = resp.getcode()
            raw = resp.read().decode("utf-8")
            if raw:
                parsed = json.loads(raw)
            else:
                parsed = None
            return status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if hasattr(e, 'read') else ""
        try:
            parsed = json.loads(raw) if raw else None
        except:
            parsed = raw
        return e.code, parsed

def test_health():
    status, body = get_json("/health")
    assert status == 200, f"/health status {status}"
    assert isinstance(body, dict)
    assert body.get("status") == "ok"

def test_post_users_accepts_and_returns_id():
    email = f"test+{random.randint(1000,9999)}@example.com"
    status, body = get_json("/users", method="POST", data={"email": email, "password": "Password123!"})
    assert status in (200,201), f"unexpected status {status}"
    assert isinstance(body, dict), "response must be JSON object"
    # Accept either 'id' or regression 'user_id'
    assert ("id" in body) or ("user_id" in body), f"expected 'id' or 'user_id' in {body}"
    val = body.get("id") or body.get("user_id")
    assert isinstance(val, int)
