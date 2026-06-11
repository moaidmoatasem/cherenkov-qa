from cherenkov.knowledge.api.routes import router


def test_router_has_route():
    routes = [r.path for r in router.routes]
    assert "/api/v1/knowledge/query" in routes


def test_router_is_apirouter():
    from fastapi import APIRouter
    assert isinstance(router, APIRouter)
