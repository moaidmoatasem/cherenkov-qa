"""Tests for cherenkov/web/errors.py"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cherenkov.web.errors import (
    APIError,
    ErrorCode,
    api_error,
    install_error_handlers,
)


@pytest.fixture()
def app_with_errors():
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/raise-api-error")
    async def raise_api():
        raise api_error(ErrorCode.SPEC_NOT_FOUND, detail={"path": "/missing.yaml"})

    @app.get("/raise-budget")
    async def raise_budget():
        raise api_error(ErrorCode.BUDGET_EXCEEDED, message="Cap of $0.10 exceeded")

    @app.get("/raise-http")
    async def raise_http():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="item not found")

    @app.get("/raise-validation")
    async def raise_val(q: int):
        return {"q": q}

    return app


@pytest.fixture()
def client(app_with_errors):
    return TestClient(app_with_errors, raise_server_exceptions=False)


class TestAPIError:
    def test_raises_correct_type(self):
        err = api_error(ErrorCode.NOT_FOUND)
        assert isinstance(err, APIError)

    def test_status_code_from_map(self):
        err = api_error(ErrorCode.SPEC_NOT_FOUND)
        assert err.status_code == 404

    def test_custom_status_code(self):
        err = api_error(ErrorCode.INTERNAL_ERROR, status_code=503)
        assert err.status_code == 503

    def test_to_response_structure(self):
        err = api_error(ErrorCode.INVALID_URL, message="SSRF blocked", detail={"url": "http://169.254.x"})
        resp = err.to_response()
        assert resp.status_code == 400
        import json
        body = json.loads(resp.body)
        assert body["error"]["code"] == "INVALID_URL"
        assert "SSRF" in body["error"]["message"]
        assert body["error"]["detail"]["url"] == "http://169.254.x"

    def test_no_detail_omitted_from_body(self):
        err = api_error(ErrorCode.NOT_FOUND)
        import json
        body = json.loads(err.to_response().body)
        assert "detail" not in body["error"]


class TestErrorHandlers:
    def test_api_error_returns_json_schema(self, client):
        resp = client.get("/raise-api-error")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "SPEC_NOT_FOUND"
        assert data["error"]["detail"] == {"path": "/missing.yaml"}

    def test_http_exception_wrapped_in_schema(self, client):
        resp = client.get("/raise-http")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert "item not found" in data["error"]["message"]

    def test_validation_error_wrapped(self, client):
        resp = client.get("/raise-validation")  # missing required int q
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "INVALID_REQUEST"
        assert "errors" in data["error"]["detail"]

    def test_budget_exceeded_returns_402(self, client):
        resp = client.get("/raise-budget")
        assert resp.status_code == 402
        data = resp.json()
        assert data["error"]["code"] == "BUDGET_EXCEEDED"


class TestErrorCodeCoverage:
    def test_all_codes_have_http_status(self):
        from cherenkov.web.errors import _HTTP_STATUS_MAP
        for code in ErrorCode:
            assert code in _HTTP_STATUS_MAP, f"{code} missing from _HTTP_STATUS_MAP"

    def test_error_codes_are_upper_snake(self):
        for code in ErrorCode:
            assert code.value == code.value.upper()
            assert " " not in code.value
