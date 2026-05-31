"""
CHERENKOV Week 0 — Controllable Target API
The "test range." A clean OpenAPI spec + a bug toggle so you can prove green->red.

Run NORMAL (Days 1-3):   uvicorn target_api:app --reload --port 8000
Run REGRESSION (Day 4):  REGRESSION_MODE=true uvicorn target_api:app --reload --port 8000
Get the spec:            curl http://localhost:8000/openapi.json > ../stub/target_spec.json
"""
import os
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="CHERENKOV Week 0 Target",
    version="1.0.0",
    description="Controllable API for proving AI test generation catches regressions.",
)

REGRESSION_MODE = os.getenv("REGRESSION_MODE", "false").lower() == "true"


# FastAPI returns 422 for validation errors by default. We normalize to 400,
# and in regression mode we inject BUG 1: swallow the error and return 200.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if REGRESSION_MODE:
        # BUG 1 — wrong status: returns 200 instead of 400.
        # A test asserting toBe(400) will FAIL. A shallow test (status < 500) passes.
        return JSONResponse(status_code=200, content={"message": "ok (mock)"})
    errors = [
        {"field": str(e["loc"][-1]) if e["loc"] else "unknown", "error": e["type"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=400, content={"detail": "Validation failed", "errors": errors}
    )


class UserCreate(BaseModel):
    email: str = Field(..., max_length=50, description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class UserResponse(BaseModel):
    id: int
    email: str


@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    if REGRESSION_MODE:
        # BUG 2 — body shape: returns 'user_id' instead of 'id'.
        # A test asserting toHaveProperty('id') will FAIL.
        return {"user_id": 42, "email": user.email}
    return UserResponse(id=42, email=user.email)


@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok", "regression_mode": REGRESSION_MODE}
