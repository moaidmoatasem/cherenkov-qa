from cherenkov.web.sdd_routes import router


def test_sdd_router_has_routes():
    routes = [r.path for r in router.routes]
    assert "/api/v1/sdd/status" in routes
    assert "/api/v1/sdd/sessions" in routes
    assert "/api/v1/sdd/sessions/{session_id}" in routes
    assert "/api/v1/sdd/tokens" in routes
    assert "/api/v1/sdd/tokens/history" in routes
    assert "/api/v1/sdd/experience" in routes
    assert "/api/v1/sdd/experience/{exp_id}" in routes
    assert "/api/v1/sdd/context" in routes
    assert "/api/v1/sdd/compact" in routes
    assert "/api/v1/sdd/graph/status" in routes
    assert "/api/v1/sdd/graph/export" in routes
    assert "/api/v1/sdd/graph/patterns" in routes
    assert "/api/v1/sdd/wiki/tree" in routes
    assert "/api/v1/sdd/wiki/{path:path}" in routes
    assert "/api/v1/sdd/findings" in routes


def test_sdd_router_routes_count():
    assert len(router.routes) >= 15
