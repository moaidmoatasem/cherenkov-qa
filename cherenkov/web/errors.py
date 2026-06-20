"""
cherenkov/web/errors.py — Structured API error codes.

All API errors follow the schema:
    {
        "error": {
            "code":    "<UPPER_SNAKE_CASE machine-readable code>",
            "message": "<human-readable explanation>",
            "detail":  <any | null>   # optional extra context
        }
    }

Usage in route handlers:
    from cherenkov.web.errors import api_error, ErrorCode

    raise api_error(ErrorCode.SPEC_NOT_FOUND, detail={"path": spec_path})

Usage in FastAPI app (call once at startup):
    from cherenkov.web.errors import install_error_handlers
    install_error_handlers(app)
"""

from __future__ import annotations

import enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode(str, enum.Enum):
    # ── Input / validation ───────────────────────────────────────────────────
    INVALID_REQUEST = "INVALID_REQUEST"         # malformed request body / params
    MISSING_FIELD = "MISSING_FIELD"             # required field absent
    INVALID_URL = "INVALID_URL"                 # target URL rejected by SSRF guard
    SPEC_NOT_FOUND = "SPEC_NOT_FOUND"           # spec file / URL not reachable
    SPEC_PARSE_ERROR = "SPEC_PARSE_ERROR"       # spec is not valid JSON/YAML/proto/SDL

    # ── Resources ────────────────────────────────────────────────────────────
    NOT_FOUND = "NOT_FOUND"                     # resource does not exist
    CONFLICT = "CONFLICT"                       # duplicate / state conflict

    # ── Auth / authz ────────────────────────────────────────────────────────
    UNAUTHORIZED = "UNAUTHORIZED"               # missing / invalid token
    FORBIDDEN = "FORBIDDEN"                     # token valid but no permission

    # ── Rate / budget ────────────────────────────────────────────────────────
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"

    # ── Substrate / LLM ──────────────────────────────────────────────────────
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"     # provider returned an error
    CERTIFICATION_FAILED = "CERTIFICATION_FAILED"

    # ── Pipeline ─────────────────────────────────────────────────────────────
    GENERATE_FAILED = "GENERATE_FAILED"
    VALIDATE_FAILED = "VALIDATE_FAILED"
    NO_TESTS_GENERATED = "NO_TESTS_GENERATED"

    # ── Internal ─────────────────────────────────────────────────────────────
    INTERNAL_ERROR = "INTERNAL_ERROR"


_HTTP_STATUS_MAP: dict[ErrorCode, int] = {
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.MISSING_FIELD: 400,
    ErrorCode.INVALID_URL: 400,
    ErrorCode.SPEC_NOT_FOUND: 404,
    ErrorCode.SPEC_PARSE_ERROR: 422,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.BUDGET_EXCEEDED: 402,
    ErrorCode.MODEL_UNAVAILABLE: 503,
    ErrorCode.CERTIFICATION_FAILED: 503,
    ErrorCode.GENERATE_FAILED: 500,
    ErrorCode.VALIDATE_FAILED: 500,
    ErrorCode.NO_TESTS_GENERATED: 422,
    ErrorCode.INTERNAL_ERROR: 500,
}


class APIError(Exception):
    """Structured API error raised inside route handlers."""

    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        detail: Any = None,
        status_code: int | None = None,
    ) -> None:
        self.code = code
        self.message = message or code.value.replace("_", " ").title()
        self.detail = detail
        self.status_code = status_code or _HTTP_STATUS_MAP.get(code, 500)
        super().__init__(self.message)

    def to_response(self) -> JSONResponse:
        body: dict[str, Any] = {"error": {"code": self.code.value, "message": self.message}}
        if self.detail is not None:
            body["error"]["detail"] = self.detail
        return JSONResponse(status_code=self.status_code, content=body)


def api_error(
    code: ErrorCode,
    message: str | None = None,
    detail: Any = None,
    status_code: int | None = None,
) -> APIError:
    """Convenience factory — raise the returned exception in route handlers."""
    return APIError(code=code, message=message, detail=detail, status_code=status_code)


def install_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(APIError)
    async def _api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        return exc.to_response()

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Map Starlette HTTP codes to our error schema
        _code_map = {
            400: ErrorCode.INVALID_REQUEST,
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.CONFLICT,
            422: ErrorCode.INVALID_REQUEST,
            429: ErrorCode.RATE_LIMIT_EXCEEDED,
        }
        code = _code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        detail_str = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        body = {"error": {"code": code.value, "message": detail_str}}
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        body = {
            "error": {
                "code": ErrorCode.INVALID_REQUEST.value,
                "message": "Request validation failed",
                "detail": {"errors": errors, "first": first},
            }
        }
        return JSONResponse(status_code=422, content=body)
