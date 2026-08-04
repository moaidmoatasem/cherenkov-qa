# Baseline re-certification — 2026-08-04

**Head:** `main` at `530468a1` (33 commits ahead of prior handover anchor `d9a161f`)
**Command (HANDOVER filter):**
```
pytest tests/ -m "not slow and not e2e and not integration and not k8s and not ollama and not mobile"
```

## Result

```
============ 2 failed, 2138 passed, 6 skipped in 510.08s (0:08:30) ============
```

Raw log: `C:\Users\moaid\AppData\Local\Temp\opencode\baseline-pr7d.txt` (local).

## The 2 failures — network-only, not regressions

```
FAILED tests/integration/real_demo/test_demo_api_real.py::test_health
FAILED tests/integration/real_demo/test_demo_api_real.py::test_post_users_accepts_and_returns_id
```

Both are `urllib.error.URLError: [Errno 10061] Connection refused` against
`http://127.0.0.1:8000` (or `CHERENKOV_TEST_BASE_URL`). These were added in
PR #854 and are **not** marked `integration`, so the HANDOVER baseline filter
collects and runs them even though they require a live demo server. They are
environment-only failures, not code regressions.

## The 6 skipped — service-gated

`slow` / `integration` / `e2e` / `k8s` / `ollama` / `mobile` markers.

## Reconciles three conflicting prior claims

| Source | Claimed | Status |
|---|---|---|
| root `HANDOVER.md:4` | 2064 passed, 2 failed (#819 `test_verify_cmd.py` drift) | **Stale** — #819 drift is fixed (no longer fails); suite grew |
| `docs/HANDOVER.md:19` | 2076 passed | **Stale** — suite grew |
| `docs/ROADMAP_2026H2.md:18` | 1746 passed, 1 skipped | **Stale** — suite grew |

Verified truth at `530468a1`: **2138 passed, 2 failed (network-only), 6 skipped.**

## Note

The prior claims were all written before the suite grew (mobile tests, MCP
auth, real_demo integration, etc.). None of the prior counts is wrong for the
HEAD it described — they are all stale for today's tree. The handover and
ROADMAP rows now carry the verified count.
