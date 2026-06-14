# ADR-001: Seam-Widening Architecture

**Date:** 2026-06-08
**Status:** Accepted
**Deciders:** Project Owner + AI Agents
**Related EPIC:** #277 (Phase -1)

---

## Context

CHERENKOV-QA currently supports API conformance testing via OpenAPI specs. The consolidated plan proposes extending the platform with:
- Mobile testing (Maestro/Appium)
- Chat agents (tool-calling)
- Second Brain (knowledge mesh)
- Desktop host (Tauri 2)
- VLM integration (LocalAI)

The key architectural decision is whether to:
1. **Extend existing Substrate/Stages/Oracle patterns** (seam-widening)
2. **Create separate modules** (e.g., `mobile/`, `chat/`, `knowledge/`)

## Decision

**Seam-widening**: Extend existing Substrate/Stages/Oracle patterns rather than creating separate modules.

### Rationale

1. **Consistency**: All testing types follow the same pipeline (Ingest → Plan → Generate → Review → Validate → Eject)
2. **Reusability**: Mobile testing reuses the same stages as API testing (just different sources and oracles)
3. **Maintainability**: One codebase, one set of patterns, one testing strategy
4. **Extensibility**: Future testing types (accessibility, security, performance) plug in via Source Adapter SPI without core modifications

### Implementation

#### Mobile Testing
- **Source**: `MobileSourceAdapter` implements `SourceAdapter` protocol
- **Stages**: `mobile_plan.py`, `mobile_generate.py`, `mobile_review.py` follow same pattern as API stages
- **Oracle**: `SemanticVisualOracle` extends `Oracle` protocol
- **Eject**: `mobile_eject_maestro.py`, `mobile_eject_appium.py` follow same pattern as Playwright eject

#### Chat Agents
- **Tools**: `query_verdicts`, `query_idioms`, `explain_divergence` call existing `KnowledgeRepository`
- **Agent**: `QAChatAgent` uses existing `SubstrateRouter` for LLM calls
- **Memory**: `ConversationMemory` follows same Repository pattern as `KnowledgeRepository`

#### Second Brain
- **Repository**: `KnowledgeRepository` extends existing `VerdictStore` pattern
- **Events**: `CHERENKOVEvent` extends existing event patterns
- **GraphRAG**: Extends existing RAG index pattern

#### Desktop Host
- **Sidecar**: Spawns existing `cherenkov` CLI as child process
- **IPC**: NDJSON protocol (same as launcher.py)
- **Config**: Extends existing `cherenkov.toml` with `[desktop]` section

#### VLM Integration
- **Provider**: `LocalAIVLMProvider` implements existing `VLMProvider` protocol
- **Router**: `SubstrateRouter` extends existing routing logic
- **Tier**: `DeviceClass` → `VLMTier` mapping extends existing device detection

### Consequences

**Positive:**
- Consistent architecture across all testing types
- Easier to maintain (one codebase, one set of patterns)
- Easier to extend (new testing types plug in via SPI)
- Easier to test (same testing strategy for all modules)

**Negative:**
- Larger codebase (more files, more complexity)
- Risk of over-abstraction (too many layers)
- Requires discipline to follow patterns consistently

**Mitigations:**
- Clear documentation (PHASE_PLAN.md, ADRs, vision docs)
- Contract tests (verify all adapters implement protocols)
- Code reviews (enforce patterns in PRs)

## Alternatives Considered

### Alternative 1: Separate Modules
Create separate modules for each testing type:
```
cherenkov/
├── api/          # API testing
├── mobile/       # Mobile testing
├── chat/         # Chat agents
├── knowledge/    # Second Brain
└── desktop/      # Desktop host
```

**Rejected because:**
- Duplicates patterns (each module has its own pipeline, stages, oracles)
- Harder to maintain (5 codebases instead of 1)
- Harder to extend (new testing types require new module)
- Inconsistent architecture (each module evolves independently)

### Alternative 2: Plugin Architecture
Create a plugin system where each testing type is a plugin:
```
cherenkov/
├── core/         # Core framework
└── plugins/
    ├── api/      # API testing plugin
    ├── mobile/   # Mobile testing plugin
    └── chat/     # Chat agents plugin
```

**Rejected because:**
- Over-engineering for current scope (5 testing types don't need plugin system)
- Adds complexity (plugin loading, dependency management)
- Slower development (plugin API design takes time)
- Premature optimization (can refactor to plugins later if needed)

## References

- EPIC #277 (Phase -1)
- `docs/vision/01_ARCHITECTURE.md` (existing architecture)
- `docs/vision/09_WIRING_SCHEMA.md` (existing seams)
- `cherenkov/stages/` (existing stage pattern)
- `cherenkov/oracle/` (existing oracle pattern)

## Notes

This ADR establishes the architectural principle for all future development. All subsequent phases (Phase 0a through Phase 8) must follow the seam-widening pattern.

If a future requirement cannot be implemented via seam-widening, a new ADR must be created to justify the exception.
