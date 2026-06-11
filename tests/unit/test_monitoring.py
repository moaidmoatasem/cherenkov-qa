import json

from cherenkov.web.monitoring import json_dumps, router


def test_json_dumps():
    data = {"status": "ok", "level": "healthy"}
    result = json_dumps(data)
    parsed = json.loads(result)
    assert parsed["status"] == "ok"
    assert parsed["level"] == "healthy"


def test_router_has_routes():
    routes = [r.path for r in router.routes]
    assert "/healthz" in routes
    assert "/metrics" in routes
    assert "/api/v1/health/detail" in routes


def test_router_routes_count():
    assert len(router.routes) >= 3
