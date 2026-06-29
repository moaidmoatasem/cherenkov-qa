---
title: Getting Started — Overview
description: What CHERENKOV-QA is, what it does, and which entry point is right for you.
---

# Getting Started

Welcome to CHERENKOV-QA. Pick the path that matches your goal:

| Goal | Go to |
|------|-------|
| Install and run in 5 minutes | [Installation →](installation.md) |
| Run against a real API now | [Quickstart →](quickstart.md) |
| Understand the cost/setup tiers | [Cost Tiers →](cost-tiers.md) |
| Browse CLI commands | [CLI Reference →](../cli/reference.md) |

---

## What CHERENKOV Does (30 seconds)

CHERENKOV turns this:

```yaml
# your-api.yaml (OpenAPI spec)
paths:
  /pets:
    get:
      responses:
        '200':
          description: A list of pets
```

Into this:

```typescript
// generated Playwright test
test('GET /pets returns 200', async ({ request }) => {
  const res = await request.get('/pets');
  expect(res.status()).toBe(200);
  // + type-safe assertions derived from your spec
});
```

And then runs it against your live server — catching drift between spec and reality.

---

## At a Glance

**Current status:** v1.1.0, production-ready core.

| Capability | Status |
|-----------|--------|
| OpenAPI → LLM → Playwright tests → Conformance | ✅ Complete |
| 6-gate review (syntax, AST, TypeScript, Prism) | ✅ Complete |
| Spec-drift detection + exit code `1` | ✅ Complete |
| Zero lock-in eject | ✅ Complete |
| LocalAI/Ollama tier routing | ✅ Complete |
| GraphRAG second brain | ✅ Complete |
| Chat agent with SSE streaming | ✅ Complete |
| React dashboard (9 screens) | ✅ Complete |
| K8s `ConformanceCheck` CRD + Go operator | ✅ Complete |
| Tauri 2 desktop app | ✅ Compiles |
| Mobile testing (Maestro/Appium) | ⏸ Needs device |

---

## Design Principles

CHERENKOV is built around four non-negotiable invariants:

!!! note "D7 — Never auto-edit test code"
    Validation and healing produce reports and suggestions only. Tests are yours. CHERENKOV never modifies them.

!!! note "Anti-lock-in"
    `cherenkov eject` strips all proprietary imports. Tests run with vanilla Playwright forever.

!!! note "Suggest-only healing"
    Healing never auto-commits or auto-applies changes. You decide.

!!! note "Spec-derived"
    Expected HTTP status codes come from the OpenAPI spec — never hardcoded assumptions.

---

## Next Steps

[Install CHERENKOV →](installation.md){ .md-button .md-button--primary }
[Run the Quickstart →](quickstart.md){ .md-button }
