# CHERENKOV Agent Memory Wiki

Welcome to the Agent Memory Wiki (gent_memory/). This directory solves "AI amnesia" by serving as a persistent, compounding knowledge base for CHERENKOV autonomous agents.

## Standard Operating Procedure

1. **Read Before Crawling**: Agents MUST read this index and relevant sub-pages before beginning an exploration or testing task to understand historical context, known bugs, and current application state.
2. **Write After Task**: Agents MUST document their findings, updated states, and newly discovered endpoints/UI components back into this directory upon task completion.
3. **Link Everything**: Build cross-references between pages (e.g., linking a discovered 500 Server Error to an endpoint-auth.md concept page).

## Seeded Memory Files

| File | Contents | Source |
|------|----------|--------|
| [endpoints.md](endpoints.md) | API endpoint inventory, mutation menu, DAST payloads | cherenkov/stages/ingest.py, stub/target_spec.json |
| [known-bugs.md](known-bugs.md) | Conformance drift patterns (422 vs 400, auth expiry, contract drift) | smoke_test*.py, 	ests/eject_fixtures/ |
| [test-patterns.md](test-patterns.md) | Generated test code, ejected fixtures, scoring metadata | stub/generated_tests/, 	ests/eject_fixtures/ |
| [dashboard-states.md](dashboard-states.md) | UI component inventory, screen states, E2E test coverage | cherenkov/web/ui/src/components/, dashboard_e2e.spec.ts |
| [validation-gate.md](validation-gate.md) | Gate status (0/5), demo kit, evidence ledger | docs/QA_DEMO_KIT.md, docs/process/VALIDATION_EVIDENCE_LEDGER.md |

## Global Context
*   **Current Framework Focus**: PydanticAI for orchestration, DeepEval for testing, Logfire for tracing.
*   **Vision Model**: Ready for MiniGPT/Qwen-VL integration for UI audits.
*   **Design Invariants**: D7 (no auto-edit), anti-lock-in (eject strips imports), suggest-only healing, spec-derived HTTP status.

*(Agents: read relevant memory files before starting a new task; write findings back after completion.)*
