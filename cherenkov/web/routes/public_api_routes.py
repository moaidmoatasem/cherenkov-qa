"""Public API routes for programmatic test generation and validation."""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Security, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from cherenkov.core.settings import get_settings

router = APIRouter(prefix="/api/v1/public", tags=["Public API"])

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify incoming X-API-Key header against configured settings.

    Args:
        api_key: Provided API key from request header.

    Returns:
        Validated API key string.

    Raises:
        HTTPException: 403 Forbidden if API key is invalid or missing.
    """
    # In a real scenario, this would check against a DB of provisioned keys.
    # For Phase 16, we use a single configured key or bootstrap key.
    expected_key = get_settings().BOOTSTRAP_KEY or get_settings().DB_KEY
    if not expected_key or api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return api_key


class GenerateRequest(BaseModel):
    """Request payload for programmatic test generation."""
    spec_content: str
    endpoint: str
    method: str


@router.post("/generate", summary="Generate tests for an endpoint")
def generate_test(request: GenerateRequest, key: str = Depends(verify_api_key)) -> dict[str, Any]:
    """Programmatic test generation for OpenAPI spec endpoints.

    Args:
        request: GenerateRequest containing spec_content, endpoint, and method.
        key: Authenticated API key string.

    Returns:
        Dictionary containing generation status, scenario ID, generated test code, and duration.
    """
    # Stub implementation for Phase 16 SDK/Marketplace integration
    return {
        "status": "success",
        "scenario_id": "gen_123",
        "test_code": f"test('{request.method.upper()} {request.endpoint}', async () => {{}});",
        "duration_ms": 150
    }


class ValidateRequest(BaseModel):
    """Request payload for programmatic test suite validation."""
    spec_content: str
    target_url: str


@router.post("/validate", summary="Validate a suite against a live server")
def validate_suite(request: ValidateRequest, key: str = Depends(verify_api_key)) -> dict[str, Any]:
    """Programmatic validation of an existing spec against a live server.

    Args:
        request: ValidateRequest containing spec_content and target_url.
        key: Authenticated API key string.

    Returns:
        Dictionary payload containing verdict, divergence count, coverage percentage, and duration.
    """
    # Stub implementation for Phase 16 SDK/Marketplace integration
    return {
        "status": "success",
        "verdict": "PASS",
        "divergence_count": 0,
        "coverage_pct": 100.0,
        "duration_ms": 1200
    }
