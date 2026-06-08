# CHERENKOV-QA Testing Strategy

**Date:** 2026-06-08  
**Status:** Active  
**Related EPIC:** #277 (Phase -1)

---

## Testing Pyramid

| Category | Tool | Location | Target Count | Phase |
|----------|------|----------|--------------|-------|
| Unit | pytest | `tests/unit/` | 500+ | Every phase |
| Contract | pytest | `tests/contracts/` | 50+ | Phase 0b+ |
| Integration | pytest | `tests/integration/` | 50-100 | Phase 1+ |
| E2E | Playwright | `tests/e2e/` | 5-10 | Phase 7-8 |
| Smoke | make targets | `tests/smoke/` | 10+ | Phase 5+ |
| Mobile Smoke | ADB + Maestro | `tests/smoke/mobile/` | 5+ | Phase 6 |

---

## Unit Tests

**Location:** `tests/unit/`  
**Tool:** pytest  
**Target:** 500+ tests  
**Coverage:** >80%

### What to Test
- Domain models (Pydantic validation, serialization)
- Business logic (pure functions, no I/O)
- Port interfaces (Protocol compliance)
- Adapter implementations (SQLite, Redis)
- Use cases (orchestration logic)

### Example
```python
# tests/unit/test_knowledge_models.py
from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeResult

def test_knowledge_query_defaults():
    query = KnowledgeQuery(query="auth timeout")
    assert query.limit == 10
    assert query.source is None

def test_knowledge_result_to_dict():
    result = KnowledgeResult(
        data={"endpoint": "/users"},
        source="verdicts",
        confidence=0.95,
        metadata={"count": 1}
    )
    d = result.to_dict()
    assert d["source"] == "verdicts"
    assert d["confidence"] == 0.95
```

### Running Unit Tests
```bash
pytest tests/unit/ -v --cov=cherenkov --cov-report=term-missing
```

---

## Contract Tests

**Location:** `tests/contracts/`  
**Tool:** pytest  
**Target:** 50+ tests  
**Phase:** Phase 0b+

### What to Test
- Port interfaces (Protocol compliance)
- Adapter implementations (SQLite and Redis pass same tests)
- API contracts (request/response schemas)

### Example
```python
# tests/contracts/test_knowledge_repository.py
import pytest
from cherenkov.knowledge.ports.repository import KnowledgeRepository
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
from cherenkov.knowledge.adapters.redis_repository import RedisKnowledgeRepository
from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeItem

@pytest.fixture(params=[SQLiteKnowledgeRepository, RedisKnowledgeRepository])
def repo(request):
    """Test both SQLite and Redis adapters."""
    return request.param()

def test_query_returns_knowledge_result(repo: KnowledgeRepository):
    query = KnowledgeQuery(query="auth timeout")
    result = repo.query(query)
    assert hasattr(result, "data")
    assert hasattr(result, "source")
    assert hasattr(result, "confidence")

def test_store_returns_item_id(repo: KnowledgeRepository):
    item = KnowledgeItem(
        item_id="test_123",
        source="verdicts",
        data={"endpoint": "/users"}
    )
    item_id = repo.store(item)
    assert item_id == "test_123"
```

### Running Contract Tests
```bash
pytest tests/contracts/ -v
```

---

## Integration Tests

**Location:** `tests/integration/`  
**Tool:** pytest  
**Target:** 50-100 tests  
**Phase:** Phase 1+

### What to Test
- Cross-module integration (HITL → Reflector, Chat → Knowledge)
- External dependencies (LocalAI, Redis, Docker)
- API endpoints (FastAPI routes)
- CLI commands (cherenkov CLI)

### Example
```python
# tests/integration/test_hitl_reflector_bridge.py
from cherenkov.hitl.store import HitlQueue
from cherenkov.reflector.reflector import Reflector
from cherenkov.core.events import event_bus

def test_hitl_decision_feeds_reflector():
    """HITL approval should update Reflector idioms."""
    # Setup
    queue = HitlQueue()
    reflector = Reflector()
    
    # Create HITL item
    item_id = queue.enqueue(
        endpoint="/users",
        method="POST",
        confidence=0.85
    )
    
    # Approve item
    queue.approve(item_id, actor="user", reason="Looks good")
    
    # Verify Reflector updated
    idioms = reflector.get_idioms()
    assert any("users" in idiom.pattern for idiom in idioms)
```

### Running Integration Tests
```bash
# Requires Docker (LocalAI + Redis)
docker compose -f docker-compose.ai.yml up -d
pytest tests/integration/ -v
```

---

## E2E Tests

**Location:** `tests/e2e/`  
**Tool:** Playwright  
**Target:** 5-10 tests  
**Phase:** Phase 7-8

### What to Test
- Golden path (spec → generate → validate → review → eject)
- Dashboard UI (all screens render, data flows)
- Desktop app (setup wizard, device manager, settings)

### Example
```typescript
// tests/e2e/test_golden_path.spec.ts
import { test, expect } from '@playwright/test';

test('golden path: spec → generate → validate → review → eject', async ({ page }) => {
  // Upload spec
  await page.goto('/setup');
  await page.setInputFiles('input[type="file"]', 'tests/fixtures/petstore.yaml');
  await page.click('button:has-text("Next")');
  
  // Generate tests
  await page.click('button:has-text("Generate")');
  await expect(page.locator('.test-count')).toHaveText('42 tests generated');
  
  // Validate
  await page.click('button:has-text("Validate")');
  await expect(page.locator('.validation-status')).toHaveText('passed');
  
  // Review
  await page.click('button:has-text("Review")');
  await page.click('button:has-text("Approve All")');
  
  // Eject
  await page.click('button:has-text("Eject")');
  const download = await page.waitForEvent('download');
  expect(download.suggestedFilename()).toBe('cherenkov-tests.zip');
});
```

### Running E2E Tests
```bash
# Requires running dashboard
python -m cherenkov review --port 8000 &
npx playwright test tests/e2e/
```

---

## Smoke Tests

**Location:** `tests/smoke/`  
**Tool:** make targets  
**Target:** 10+ tests  
**Phase:** Phase 5+

### What to Test
- CLI commands work (`cherenkov --help`, `cherenkov doctor`)
- Pipeline runs end-to-end (spec → generate → validate)
- Eject produces standalone tests
- Mobile pipeline works (APK → Maestro YAML)

### Example
```python
# tests/smoke/test_cli.py
import subprocess

def test_cli_help():
    result = subprocess.run(["cherenkov", "--help"], capture_output=True)
    assert result.returncode == 0
    assert "usage:" in result.stdout.decode()

def test_cli_doctor():
    result = subprocess.run(["cherenkov", "doctor"], capture_output=True)
    assert result.returncode == 0
```

### Running Smoke Tests
```bash
make smoke
```

---

## Mobile Smoke Tests

**Location:** `tests/smoke/mobile/`  
**Tool:** ADB + Maestro  
**Target:** 5+ tests  
**Phase:** Phase 6

### What to Test
- Mobile source ingestion (APK/HAR/HIL)
- Maestro YAML generation
- Appium test generation
- Mobile test execution (emulator)

### Example
```python
# tests/smoke/mobile/test_mobile_pipeline.py
import subprocess

def test_mobile_ingest():
    result = subprocess.run(
        ["cherenkov", "mobile", "ingest", "tests/fixtures/test.apk"],
        capture_output=True
    )
    assert result.returncode == 0

def test_maestro_eject():
    result = subprocess.run(
        ["cherenkov", "eject", "--format", "maestro", "--output", "/tmp/maestro_tests"],
        capture_output=True
    )
    assert result.returncode == 0
```

### Running Mobile Smoke Tests
```bash
# Requires Android emulator
make mobile-smoke
```

---

## Performance Baselines

| Module | Baseline | Smoke Test | Phase |
|--------|----------|------------|-------|
| VLM request (LocalAI) | < 10s for 1280×720 PNG | `tests/smoke/perf_vlm.py` | Phase 2 |
| VLM request (Ollama fallback) | < 30s for 1280×720 PNG | `tests/smoke/perf_vlm.py` | Phase 2 |
| Knowledge query (SQLite) | < 500ms for 1000-record DB | `tests/smoke/perf_knowledge.py` | Phase 1 |
| Knowledge query (Redis) | < 100ms for 10000-record DB | `tests/smoke/perf_knowledge.py` | Phase 1 |
| Chat response (short, no tool) | < 5s first token, < 15s completion | `tests/smoke/perf_chat.py` | Phase 4 |
| Chat response (with tool call) | < 20s completion | `tests/smoke/perf_chat.py` | Phase 4 |
| Dashboard API (`/overview`) | < 200ms p95 | `tests/smoke/perf_api.py` | Phase 7 |
| Desktop startup (cold) | < 8s to window visible | Manual test | Phase 3 |
| Desktop startup (warm) | < 2s | Manual test | Phase 3 |
| Setup wizard (full walkthrough) | < 5 min for fresh user | Manual test | Phase 3 |

### Performance Test Example
```python
# tests/smoke/perf_vlm.py
import time
from cherenkov.substrate.providers.localai import LocalAIVLMProvider

def test_vlm_latency():
    provider = LocalAIVLMProvider()
    if not provider.is_available():
        pytest.skip("LocalAI not available")
    
    image = create_test_image(1280, 720)
    start = time.time()
    result = provider.analyze(image, "Describe this screenshot")
    elapsed = time.time() - start
    
    assert elapsed < 10.0, f"VLM latency {elapsed:.2f}s exceeds 10s baseline"
```

---

## Testing Rules

1. **Every new module must have unit tests before merge**
2. **Every port/adapter must have contract tests** (SQLite + Redis pass same contract)
3. **Every API endpoint must have integration tests**
4. **E2E tests cover golden paths only** (not every edge case)
5. **Smoke tests auto-skip if prerequisites missing** (Docker, ADB, etc.)
6. **Performance baselines degrade to WARNING (not FAIL) if exceeded**

---

## Kill Criteria Per Phase

| Phase | Kill Criteria |
|-------|---------------|
| Phase 0a | `pytest tests/unit/` + `pytest tests/smoke/` green |
| Phase 0b | `pytest tests/contracts/` green |
| Phase 1 | `pytest tests/unit/test_knowledge_repository.py` green |
| Phase 2 | `pytest tests/integration/test_localai_integration.py` green |
| Phase 3 | Desktop app opens on all 3 platforms |
| Phase 4 | `pytest tests/unit/test_chat_agent.py` green |
| Phase 5 | `pytest tests/unit/test_mobile_source_adapter.py` green |
| Phase 6 | `make mobile-smoke` green |
| Phase 7 | `npx playwright test tests/e2e/` green |
| Phase 8 | `make k3d-test` green |

---

## CI/CD Integration

### `.github/workflows/ci.yml`
```yaml
name: CI
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=cherenkov --cov-report=term-missing

  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run contract tests
        run: pytest tests/contracts/ -v

  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run smoke tests
        run: make smoke
```

### `.github/workflows/integration.yml`
```yaml
name: Integration Tests
on:
  push:
    branches: [main]

jobs:
  integration:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
        ports: ["6379:6379"]
      localai:
        image: localai/localai:latest
        ports: ["8080:8080"]
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: pytest tests/integration/ -v
```

---

## References

- EPIC #277 (Phase -1)
- `docs/adr/ADR-004-clean-architecture.md` (Clean Architecture)
- `docs/PHASE_PLAN.md` (Phase-by-phase kill criteria)
