# CHERENKOV-QA Error Handling & Graceful Degradation

**Date:** 2026-06-08
**Status:** Active
**Related EPIC:** #277 (Phase -1), #279 (Phase 0b)

---

## Principle

**Never crash on infrastructure failure, always degrade.** Every external dependency has a fallback chain. The system should work in L0 mode (bare CLI, no Docker, no Redis, no LLM) on any laptop.

---

## Graceful Degradation Matrix

| Dependency | Down Scenario | Degradation |
|------------|---------------|-------------|
| LocalAI unavailable | Docker not running / model not pulled | Fall back to Ollama. If neither, run in demo mode (no LLM) |
| Redis unavailable | Redis server down | Fall back to SQLite for all stores. No vector search, no pub/sub, no session cache |
| Ollama unavailable | Ollama not on PATH | Skip VLM tier. Use `pixel_diff_only` for visual. Chat agent falls back to text-only |
| VLM confidence < 0.7 | Model uncertain | Escalate to HITL. Never auto-approve |
| ADB not installed | `adb` not on PATH | Skip mobile testing. Run in API-only mode |
| Maestro not installed | `maestro` not on PATH | Skip mobile execution. Can still generate YAML |
| Docker not available | Docker not installed | Run in bare CLI mode (L0). All Python-only features work |

---

## Error Response Format

All API errors follow this format:

```json
{
  "error": {
    "code": "dependency_unavailable",
    "message": "LocalAI is not available",
    "detail": {
      "dependency": "localai",
      "fallback": "ollama",
      "suggestion": "Start LocalAI with: docker compose -f docker-compose.ai.yml up"
    }
  }
}
```

### Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `dependency_unavailable` | External dependency not available | 503 |
| `fallback_active` | Using fallback instead of primary | 200 (with warning) |
| `rate_limit_exceeded` | Too many requests | 429 |
| `input_too_large` | Input exceeds size limit | 413 |
| `invalid_input` | Input validation failed | 400 |
| `unauthorized` | Missing or invalid API key | 401 |
| `forbidden` | Insufficient permissions | 403 |
| `not_found` | Resource not found | 404 |
| `internal_error` | Unexpected error | 500 |

---

## /healthz Endpoint

The `/healthz` endpoint returns structured health status:

```json
{
  "status": "degraded",
  "dependencies": {
    "localai": {
      "available": false,
      "fallback": "ollama",
      "message": "LocalAI is not running"
    },
    "redis": {
      "available": false,
      "fallback": "sqlite",
      "message": "Redis is not running"
    },
    "ollama": {
      "available": true,
      "fallback": null,
      "message": "Ollama is running"
    },
    "docker": {
      "available": true,
      "fallback": null,
      "message": "Docker is running"
    }
  },
  "vlm_tier": "pixel_diff_only",
  "mode": "demo"
}
```

### Health Status Values

| Status | Description | HTTP Status |
|--------|-------------|-------------|
| `healthy` | All dependencies available | 200 |
| `degraded` | Some dependencies unavailable, using fallbacks | 200 |
| `unhealthy` | Critical dependencies unavailable | 503 |

---

## Implementation

### GracefulDegradation Utility

```python
# cherenkov/core/error_handling.py
from dataclasses import dataclass
from typing import Literal, Any
from enum import Enum

class DependencyStatus(Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

@dataclass
class DependencyCheck:
    name: str
    status: DependencyStatus
    fallback: str | None = None
    message: str = ""

@dataclass
class ErrorResponse:
    code: str
    message: str
    detail: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "detail": self.detail
            }
        }

class GracefulDegradation:
    def __init__(self):
        self.dependencies: dict[str, DependencyCheck] = {}

    def check_dependency(self, name: str, check_fn: callable, fallback: str | None = None) -> DependencyCheck:
        try:
            check_fn()
            status = DependencyStatus.AVAILABLE
            message = f"{name} is available"
        except Exception as e:
            status = DependencyStatus.UNAVAILABLE if not fallback else DependencyStatus.DEGRADED
            message = f"{name} is unavailable: {str(e)}"

        check = DependencyCheck(
            name=name,
            status=status,
            fallback=fallback,
            message=message
        )
        self.dependencies[name] = check
        return check

    def get_health_status(self) -> dict[str, Any]:
        overall = "healthy"
        if any(d.status == DependencyStatus.UNAVAILABLE for d in self.dependencies.values()):
            overall = "unhealthy"
        elif any(d.status == DependencyStatus.DEGRADED for d in self.dependencies.values()):
            overall = "degraded"

        return {
            "status": overall,
            "dependencies": {
                name: {
                    "status": check.status.value,
                    "fallback": check.fallback,
                    "message": check.message
                }
                for name, check in self.dependencies.items()
            }
        }

# Global instance
degradation = GracefulDegradation()
```

### /healthz Endpoint

```python
# cherenkov/web/api.py
from cherenkov.core.error_handling import degradation

@app.get("/healthz")
async def healthz():
    degradation.check_dependency("localai", check_localai, fallback="ollama")
    degradation.check_dependency("redis", check_redis, fallback="sqlite")
    degradation.check_dependency("ollama", check_ollama)
    degradation.check_dependency("docker", check_docker)

    status = degradation.get_health_status()

    http_status = 200
    if status["status"] == "unhealthy":
        http_status = 503

    return Response(
        content=json.dumps(status),
        status_code=http_status,
        media_type="application/json"
    )

def check_localai():
    import requests
    response = requests.get("http://localhost:8080/health", timeout=5)
    response.raise_for_status()

def check_redis():
    import redis
    r = redis.from_url("redis://localhost:6379")
    r.ping()

def check_ollama():
    import requests
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    response.raise_for_status()

def check_docker():
    import subprocess
    result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
    if result.returncode != 0:
        raise Exception("Docker not available")
```

---

## Fallback Chains

### VLM Provider Fallback

```python
# cherenkov/substrate/router.py
def get_vlm_provider(self):
    if self.vlm_tier == VLMTier.PIXEL_DIFF_ONLY:
        return None

    # Try LocalAI first
    if self.localai.is_available():
        return self.localai

    # Fallback to Ollama
    if self.ollama.is_available():
        return self.ollama

    # Fallback to OpenAI (if egress allowed)
    if self.openai.is_available():
        return self.openai

    # No VLM available
    return None
```

### Knowledge Repository Fallback

```python
# cherenkov/knowledge/factory.py
def get_knowledge_repository() -> KnowledgeRepository:
    try:
        import redis
        r = redis.from_url("redis://localhost:6379")
        r.ping()
        return RedisKnowledgeRepository(r)
    except:
        return SQLiteKnowledgeRepository()
```

### Event Bus Fallback

```python
# cherenkov/core/events.py
def get_event_bus() -> EventBus:
    try:
        import redis
        r = redis.from_url("redis://localhost:6379")
        r.ping()
        return RedisStreamsEventBus(r)
    except:
        return AsyncQueueEventBus()
```

---

## Error Handling in Use Cases

```python
# cherenkov/knowledge/use_cases/query.py
from cherenkov.core.error_handling import ErrorResponse

def query_knowledge(repo: KnowledgeRepository, query: str) -> KnowledgeResult:
    try:
        knowledge_query = KnowledgeQuery(query=query)
        return repo.query(knowledge_query)
    except Exception as e:
        # Log error
        logger.error(f"Knowledge query failed: {e}")

        # Return empty result instead of crashing
        return KnowledgeResult(
            data=[],
            source="error",
            confidence=0.0,
            metadata={"error": str(e)}
        )
```

---

## Error Handling in API Routes

```python
# cherenkov/knowledge/api/routes.py
from fastapi import HTTPException
from cherenkov.core.error_handling import ErrorResponse

@router.get("/api/v1/knowledge/query")
async def get_knowledge(q: str, source: str | None = None):
    try:
        repo = get_knowledge_repository()
        result = query_knowledge(repo, q)
        return result.to_dict()
    except Exception as e:
        error = ErrorResponse(
            code="internal_error",
            message="Knowledge query failed",
            detail={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=error.to_dict())
```

---

## Testing Error Handling

```python
# tests/unit/test_error_handling.py
from cherenkov.core.error_handling import GracefulDegradation, DependencyStatus

def test_graceful_degradation_healthy():
    degradation = GracefulDegradation()
    degradation.check_dependency("test", lambda: None)

    status = degradation.get_health_status()
    assert status["status"] == "healthy"

def test_graceful_degradation_degraded():
    degradation = GracefulDegradation()
    degradation.check_dependency("test", lambda: 1/0, fallback="fallback")

    status = degradation.get_health_status()
    assert status["status"] == "degraded"
    assert status["dependencies"]["test"]["fallback"] == "fallback"

def test_graceful_degradation_unhealthy():
    degradation = GracefulDegradation()
    degradation.check_dependency("test", lambda: 1/0)

    status = degradation.get_health_status()
    assert status["status"] == "unhealthy"
```

---

## References

- EPIC #279 (Phase 0b: Foundations)
- Issue #320 (Error handling framework)
- `cherenkov/core/error_handling.py` (to be created)
- `cherenkov/web/api.py` (to be extended)
