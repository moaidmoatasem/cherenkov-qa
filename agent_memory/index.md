# CHERENKOV Agent Memory Wiki

Welcome to the Agent Memory Wiki (`agent_memory/`). This directory solves "AI amnesia" by serving as a persistent, compounding knowledge base for CHERENKOV autonomous agents.

## Standard Operating Procedure

1. **Read Before Crawling**: Agents MUST read this index and relevant sub-pages before beginning an exploration or testing task to understand historical context, known bugs, and current application state.
2. **Write After Task**: Agents MUST document their findings, updated states, and newly discovered endpoints/UI components back into this directory upon task completion.
3. **Link Everything**: Build cross-references between pages (e.g., linking a discovered `500 Server Error` to an `endpoint-auth.md` concept page).

## Seeded Memory Files

| File | Contents | Source |
|------|----------|--------|
| [endpoints.md](endpoints.md) | API endpoint inventory, mutation menu, DAST payloads | `cherenkov/stages/ingest.py`, `stub/target_spec.json` |
| [known-bugs.md](known-bugs.md) | Conformance drift patterns (422 vs 400, auth expiry, contract drift) | `smoke_test*.py`, `tests/eject_fixtures/` |
| [test-patterns.md](test-patterns.md) | Generated test code, ejected fixtures, scoring metadata | `stub/generated_tests/`, `tests/eject_fixtures/` |
| [dashboard-states.md](dashboard-states.md) | UI component inventory, screen states, E2E test coverage | `cherenkov/web/ui/src/components/`, `dashboard_e2e.spec.ts` |
| [snyk-findings.md](snyk-findings.md) | Snyk vulnerability scan results for agent remediation | `cherenkov/security/snyk_bridge.py` |
| [validation-gate.md](validation-gate.md) | Gate status (0/5), demo kit, evidence ledger | `docs/QA_DEMO_KIT.md`, `docs/process/VALIDATION_EVIDENCE_LEDGER.md` |

## Agent Skills (MCP Tools)
The following skills have been re-integrated from Track B/C and are exposed via MCP for openCode clients and autonomous agents:
- [Visual Diff Baseline](../skills/visual-diff.md)
- [K6 Perf Runner](../skills/k6-perf.md)
- [RAG Index Query](../skills/rag-query.md)
- [Jira Exporter](../skills/jira-exporter.md)
- [MENA Compliance Scanner](../skills/mena-compliance.md)

## Global Context
*   **Current Framework Focus**: `PydanticAI` for orchestration, `DeepEval` for testing, `Logfire` for tracing.
*   **Vision Model**: Ready for MiniGPT/Qwen-VL integration for UI audits.
*   **Design Invariants**: D7 (no auto-edit), anti-lock-in (eject strips imports), suggest-only healing, spec-derived HTTP status.

*(Agents: read relevant memory files before starting a new task; write findings back after completion.)*
