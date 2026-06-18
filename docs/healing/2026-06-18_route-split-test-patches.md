# Healing Suggestion: Route-split test patches

**Date:** 2026-06-18
**Cause:** `refactor/api-route-split` moved `get_queue` and `verify_api_key` from `cherenkov/web/api.py` to `cherenkov/web/routes/deps.py`. Tests still patch/import the old module paths.

---

## Changes needed

### 1. `tests/test_hitl_auth.py:33`

**Current:**
```python
from cherenkov.web.api import verify_api_key
```

**Suggested:**
```python
from cherenkov.web.routes.deps import verify_api_key
```

### 2. `tests/integration/test_api_endpoints.py` — 10 patch targets

All instances of:
```python
patch("cherenkov.web.api.get_queue")
```
should become:
```python
patch("cherenkov.web.routes.deps.get_queue")
```

Affected lines: 92, 108, 129, 139, 154, 171, 181, 239, 248, 259.

---

## Why not auto-applied

Per D7 invariant: test code is never auto-edited. Validation and healing produce reports/suggestions only.
