# CHERENKOV-QA Best Practices

**Date:** 2026-06-08  
**Status:** Active  
**Related EPIC:** #277 (Phase -1)

---

## Coding Standards

### Python

- **PEP 8**: Follow PEP 8 style guide
- **Type hints**: All functions must have type hints
- **Docstrings**: All public functions must have docstrings
- **Line length**: Max 100 characters
- **Imports**: Use absolute imports, not relative

### Example

```python
from typing import Any
from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeResult

def query_knowledge(repo: KnowledgeRepository, query: str, limit: int = 10) -> KnowledgeResult:
    """Query knowledge repository.
    
    Args:
        repo: Knowledge repository instance
        query: Search query string
        limit: Maximum number of results
    
    Returns:
        KnowledgeResult with matching items
    
    Raises:
        ValueError: If query is empty
    """
    if not query:
        raise ValueError("Query cannot be empty")
    
    knowledge_query = KnowledgeQuery(query=query, limit=limit)
    return repo.query(knowledge_query)
```

---

## Clean Architecture

### Module Structure

Every new feature module follows:

```
cherenkov/{module}/
├── domain/          # Pure business logic, no I/O
│   └── models.py    # Pydantic models, enums
├── ports/           # Protocol interfaces (the "what")
│   ├── repository.py
│   └── event_bus.py
├── adapters/        # I/O implementations (the "how")
│   ├── sqlite_{module}.py
│   └── redis_{module}.py
├── use_cases/       # Orchestration
│   └── {action}.py
└── api/             # FastAPI routes / CLI commands
    └── routes.py
```

### Dependency Rules

```
domain/ ← ports/ ← adapters/ ← use_cases/ ← api/
```

**Key rule**: Arrows point inward. Outer layers depend on inner layers, never the reverse.

### Example: Knowledge Repository

**Domain (pure business logic):**
```python
@dataclass
class KnowledgeQuery:
    query: str
    source: str | None = None
    limit: int = 10
```

**Ports (Protocol interfaces):**
```python
class KnowledgeRepository(Protocol):
    def query(self, query: KnowledgeQuery) -> KnowledgeResult: ...
```

**Adapters (I/O implementations):**
```python
class SQLiteKnowledgeRepository:
    def query(self, query: KnowledgeQuery) -> KnowledgeResult:
        # SQLite implementation
        pass
```

---

## Testing

### Test Structure

```
tests/
├── unit/            # Unit tests (500+)
├── contracts/       # Contract tests (50+)
├── integration/     # Integration tests (50-100)
├── e2e/             # E2E tests (5-10)
└── smoke/           # Smoke tests (10+)
```

### Unit Tests

Test domain logic without I/O:

```python
def test_knowledge_query_defaults():
    query = KnowledgeQuery(query="auth timeout")
    assert query.limit == 10
    assert query.source is None
```

### Contract Tests

Test that all adapters implement the same Protocol:

```python
@pytest.fixture(params=[SQLiteKnowledgeRepository, RedisKnowledgeRepository])
def repo(request):
    return request.param()

def test_query_returns_knowledge_result(repo: KnowledgeRepository):
    query = KnowledgeQuery(query="auth timeout")
    result = repo.query(query)
    assert hasattr(result, "data")
    assert hasattr(result, "source")
```

### Integration Tests

Test cross-module integration:

```python
def test_hitl_decision_feeds_reflector():
    queue = HitlQueue()
    reflector = Reflector()
    
    item_id = queue.enqueue(endpoint="/users", method="POST", confidence=0.85)
    queue.approve(item_id, actor="user", reason="Looks good")
    
    idioms = reflector.get_idioms()
    assert any("users" in idiom.pattern for idiom in idioms)
```

---

## Error Handling

### Graceful Degradation

Never crash on infrastructure failure, always degrade:

```python
def get_vlm_provider(self):
    if self.localai.is_available():
        return self.localai
    
    if self.ollama.is_available():
        return self.ollama
    
    return None  # No VLM available
```

### Error Response Format

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

---

## Logging

### Structured Logging

Use structlog for JSON structured logs:

```python
from cherenkov.core.logging import get_logger

logger = get_logger()

def run_pipeline(spec_path: str, trace_id: str | None = None):
    trace_id = trace_id or str(uuid.uuid4())
    log = logger.bind(trace_id=trace_id, spec_path=spec_path)
    
    log.info("pipeline_start")
    # ... pipeline logic ...
    log.info("pipeline_end", tests_generated=42)
```

### Log Levels

| Level | When |
|-------|------|
| `DEBUG` | SQL queries, individual event emissions |
| `INFO` | Phase transitions, pipeline start/end |
| `WARNING` | Degradation, VLM confidence below 0.7 |
| `ERROR` | LLM timeout, Docker unavailable |

---

## Security

### Input Validation

Validate all inputs:

```python
def validate_message(message: str) -> None:
    if len(message) > 10000:
        raise HTTPException(status_code=413, detail="Message too long")
    
    if re.search(r'[\x00-\x1F\x7F]', message):
        raise HTTPException(status_code=400, detail="Message contains control characters")
```

### Rate Limiting

Rate limit all endpoints:

```python
class RateLimiter:
    def check(self, client_ip: str) -> None:
        if len(self.requests[client_ip]) >= 20:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

### Egress Policy

Respect egress policy:

```python
if config.egress == "none":
    # No outbound network calls
    pass
elif config.egress == "internal":
    # Localhost only
    pass
elif config.egress == "any":
    # Allow cloud APIs
    pass
```

---

## Performance

### Caching

Cache expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def query_knowledge(query: str) -> KnowledgeResult:
    # Expensive query
    pass
```

### Async I/O

Use async for I/O-bound operations:

```python
async def stream_chat(session_id: str, message: str):
    async for token in agent.chat(session_id, message):
        yield token
```

### Connection Pooling

Use connection pools for databases:

```python
import redis

pool = redis.ConnectionPool.from_url("redis://localhost:6379", max_connections=10)
r = redis.Redis(connection_pool=pool)
```

---

## Documentation

### Docstrings

All public functions must have docstrings:

```python
def query_knowledge(repo: KnowledgeRepository, query: str) -> KnowledgeResult:
    """Query knowledge repository.
    
    Args:
        repo: Knowledge repository instance
        query: Search query string
    
    Returns:
        KnowledgeResult with matching items
    
    Raises:
        ValueError: If query is empty
    """
    pass
```

### README Updates

Update README.md when adding new features:

```markdown
## New Features

### Second Brain (Phase 1)
- Unified knowledge query across all stores
- GraphRAG for multi-domain retrieval
- CLI: `cherenkov knowledge query "auth timeout"`
```

---

## Code Review

### Checklist

- [ ] Follows Clean Architecture (domain/ports/adapters)
- [ ] Has type hints
- [ ] Has docstrings
- [ ] Has unit tests
- [ ] Has contract tests (if adapter)
- [ ] Has integration tests (if cross-module)
- [ ] Handles errors gracefully
- [ ] Logs appropriately
- [ ] Respects egress policy
- [ ] No secrets in code
- [ ] Performance considered

### Review Process

1. **Self-review**: Review your own code before requesting review
2. **Automated checks**: CI runs tests, linters, type checkers
3. **Human review**: At least 1 maintainer approval required
4. **Squash merge**: Squash commits on merge to main

---

## Git Workflow

### Branch Naming

```
feat/123-add-knowledge-repository
fix/456-fix-hitl-bridge
docs/789-update-readme
```

### Commit Messages

```
feat(knowledge): add SQLiteKnowledgeRepository

- Implements KnowledgeRepository Protocol
- Supports query, store, search, get_by_id
- Adds unit tests and contract tests

Closes #123
```

### Pull Requests

- **One concern per PR**: Don't mix features and refactors
- **Small PRs**: Prefer multiple small PRs over one large PR
- **Raw evidence**: Show terminal output, not summaries
- **Link issues**: Use `Closes #123` to auto-close issues

---

## Design Invariants

### D7: Never Auto-Edit Test Code

Validate and healing produce reports/suggestions only:

```python
def suggest_heal(failure: FailureRecord) -> DiagnosisResult:
    # Returns suggestion, never edits test code
    return DiagnosisResult(
        failure_class=FailureClass.AUTH_EXPIRY,
        suggested_fix="Add token refresh before request"
    )
```

### Anti-Lock-In

Tests must run without CHERENKOV:

```python
# Ejected tests have ZERO CHERENKOV imports
# User can run: npx playwright test
```

### Suggest-Only Healing

Healing never auto-commits or auto-applies:

```python
def heal(failure: FailureRecord) -> str:
    # Returns suggestion, never applies it
    return "Try adding a retry mechanism"
```

### Spec-Derived

Expected HTTP status comes from OpenAPI spec:

```python
expected_status = spec.paths[endpoint].get(method).responses.keys()
# Not hardcoded assumptions
```

---

## References

- `docs/PHASE_PLAN.md` (Consolidated plan)
- `docs/adr/ADR-004-clean-architecture.md` (Clean Architecture)
- `docs/TESTING.md` (Testing strategy)
- `docs/ERROR_HANDLING.md` (Error handling)
- `docs/LOGGING.md` (Logging strategy)
