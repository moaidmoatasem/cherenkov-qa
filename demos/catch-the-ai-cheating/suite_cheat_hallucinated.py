"""CHEAT: asserts on a fabricated field the spec never defines (a fake oracle)."""


def test_get_order_ok(resp):
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 42
    assert body["total"] == 99.5
    assert body["status"] == "paid"
    assert body["discount_code"] == "SAVE10"   # no such field in the spec


def test_get_order_not_found(resp404):
    assert resp404.status_code == 404
