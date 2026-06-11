# Module Implementation Status

This document tracks the implementation status of each CHERENKOV-QA module.
Status: PRODUCTION | PARTIAL | STUB | PLANNED

## Core Pipeline (Track A)

| Module | Status | Notes |
|--------|--------|-------|
| cherenkov/core/contracts.py | PRODUCTION | Versioned Pydantic contracts |
| cherenkov/core/orchestrator.py | PRODUCTION | DAG pipeline execution |
| cherenkov/core/config.py | PRODUCTION | Environment-based config |
| cherenkov/stages/ingest.py | PRODUCTION | OpenAPI spec ingestion |
| cherenkov/stages/plan.py | PRODUCTION | Test scenario planning |
| cherenkov/stages/generate.py | PRODUCTION | LLM test generation |
| cherenkov/stages/review.py | PRODUCTION | Test review stage |
| cherenkov/execution/eject.py | PRODUCTION | Standalone test eject |
| cherenkov/execution/validate.py | PARTIAL | Runs suite; suggestion generation is heuristic-only |
| cherenkov/ai/ollama_client.py | PRODUCTION | Ollama LLM client |
| cherenkov/substrate/router.py | PRODUCTION | Tier-aware model routing |

## Oracle & Validation

| Module | Status | Notes |
|--------|--------|-------|
| cherenkov/oracle/spec_prism.py | PARTIAL | Status-code validation only; body/header validation not implemented |
| cherenkov/oracle/prod_snapshot.py | PARTIAL | |
| cherenkov/healing/diagnose.py | PRODUCTION | Suggest-only healing |

## MCP Tools

| Tool | Status | Notes |
|------|--------|-------|
| hitl_list / hitl_approve / hitl_reject | PRODUCTION | |
| validate_gate | PRODUCTION | |
| query_rag | PARTIAL | status_code filter not implemented |
| visual_diff | STUB | Requires visual oracle infrastructure |
| run_perf | STUB | Requires k6 >= 0.50 installed |
| export_jira | STUB | JIRA API not wired |
| scan_mena | STUB | MENA compliance scanner not implemented |

## Extended Features

| Module | Status | Notes |
|--------|--------|-------|
| cherenkov/chat/ | PRODUCTION | Chat agent with SSE streaming |
| cherenkov/reflector/ | PRODUCTION | Verdict memory + suppression |
| cherenkov/hitl/ | PRODUCTION | Human-in-the-loop review queue |
| cherenkov/governance/governance.py | PARTIAL | KPI collection; formula is approximate |
| cherenkov/governance/compliance/ | STUB | |
| cherenkov/federation/ | PARTIAL | |
| cherenkov/divergence/ | PARTIAL | |
| cherenkov/knowledge/ | PARTIAL | GraphRAG, KnowledgeRepository SPI |
| cherenkov/compliance/scanner.py | STUB | |
| cherenkov/web/ | PRODUCTION | FastAPI review API |

## Blocked (Requires External Tools)

| Module | Status | Blocker |
|--------|--------|---------|
| desktop/src-tauri/ | BLOCKED | Requires cargo (Tauri 2) |
| cherenkov/sources/mobile/ | BLOCKED | Requires ADB + Maestro |
| operator/ | IN PROGRESS | K8s operator (Phase 8) |
