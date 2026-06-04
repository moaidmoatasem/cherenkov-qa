# CHERENKOV — Scope Ledger (honest map of what is live vs built-ahead)

**Date:** 2026-06-05 · **Status:** Authoritative for *scope* (pairs with [HANDOVER.md](HANDOVER.md) for *project status*).

This file exists to end a standing contradiction: the governing docs say **"Track A
only; no build-ahead-of-validation; Track B/C is quarantined"**, but the live
`cherenkov/` tree contains Track B/C **and** a whole wave of Horizon 2 modules. That
expansion happened on the strength of a **fabricated validation gate** (see
[HANDOVER.md §5](HANDOVER.md)).

This ledger does **not** bless that expansion and does **not** delete it. It states
the truth so decisions can be made with eyes open:

> **The validation gate is NOT passed. Therefore nothing below — Track A core or
> built-ahead — is "shipped" or "validated."** The only honest distinction today is
> *core product surface* vs *code built ahead of the gate*.

---

## A. Track A core surface (the product, per HANDOVER §3)

Design invariants proven by automated tests; this is what the tool *is*. Still
unvalidated by real users, but it is the intended product.

```
cherenkov/core/        contracts.py, errors.py, config.py, orchestrator.py
cherenkov/ai/          interface.py, ollama_client.py, __init__.py
cherenkov/stages/      ingest.py, plan.py, generate.py, review.py
cherenkov/execution/   prism_mock.py, playwright_invoke.py, trace_reader.py,
                       validate.py, eject.py
cherenkov/healing/     diagnose.py, auth_expiry.py, contract_drift.py
```

## B. Built-ahead, now LIVE in `cherenkov/` (NOT in HANDOVER §3, NOT validated)

Present and unit-tested, but added before the gate. Do not treat as shipped; do not
extend further until Track A validates with real evidence.

| Package | Origin | Notes |
|---|---|---|
| `ai/openai_client.py`, `ai/cache.py`, `ai/accounting.py` | Epoch 1 (Substrate) | provider abstraction + caching |
| `substrate/` | Epoch 1 (L0 router) | capability-tier routing, egress dials, certification |
| `hitl/` | Phase A | terminal review queue (SQLite) |
| `reflector/` | E7 | verdict memory + suppression |
| `divergence/` | E3 | witness/skeptic/explorer loops |
| `coverage/`, `sdet/` | — | coverage loop, assertion gate |
| `truth/`, `oracle/` | E9/E11 | truth model, emitters, sources, oracles |
| `copilot/` | E10 | intent/mentor/triage/autonomy |
| `governance/` | E12 | KPI panel |
| `continuity/` | — | pr-diff / daemon |
| `dashboard/` | Wk18-19 deferral | `render.py` (re-integrated) |
| `stages/visual/`, `stages/perf/` | **Track B re-integrated** | duplicate of deferred visual_diff/k6 |
| `mcp/` | X4 | JSON-RPC MCP server |
| `openclaw/` | Horizon 2 | chat HITL relay + healing feedback |
| `federation/` | Horizon 2 | multi-node sync + cross-check |
| extra `stages/*_cmd.py` | various | certify/governance/copilot/daemon/doctor/init/map/profile/vision |

## C. Still quarantined in `track-b-c-deferred/` (reference only)

Note the **duplication**: Track B (visual/perf/dashboard) exists BOTH here and re-built
in §B. This is debt to resolve when scope is formally decided.

```
track-b-c-deferred/cherenkov/  ai/rag_index.py, compliance/mena_scanner.py,
                               api/main.py, stages/diagnostics_stage.py,
                               stages/ui_generate.py, stages/ui_plan.py,
                               validate/jira_exporter.py, execution/k6_runner.py,
                               execution/perf_analyzer.py, execution/visual_diff.py
track-b-c-deferred/dashboard/  React UI
track-b-c-deferred/smoke_tests/
```

---

## The open decision (owner's call)

This ledger makes the contradiction legible; it does not resolve it. The two clean
end-states, to choose **after** the real validation gate:

1. **Re-quarantine** the §B built-ahead surface back out of the product until demand
   justifies it (restores the original invariant; large diff; resolves the §B/§C
   duplication by keeping one copy).
2. **Formally adopt** the expanded scope — rewrite HANDOVER/AGENTS to make Horizon 2
   in-scope (keeps the code; explicitly retires the "Track A only" rule).

Doing neither — the current state — is the actual problem: working code living in
permanent contradiction with its own governing docs. Until then: **validate Track A
first.**
