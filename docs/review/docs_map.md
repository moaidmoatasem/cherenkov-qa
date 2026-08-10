# Documentation Map

Based on the repository inventory, the `docs/` folder contains a deeply structured and comprehensive set of markdown documentation. Here is a high-level map of the critical sections.

## Root Level Docs
- `HANDOVER_TO_CLAUDE_CODE.md`
- `INDEX.md`, `README.md`
- `MIGRATION.md`, `MIGRATION_INVENTORY.md`
- `PLAYBOOK.md`
- `TECHNICAL_DESIGN.md`, `SYSTEM_DESIGN.md`
- `STATUS.md`, `MODULE_STATUS.md`, `SCOPE_LEDGER.md`
- Roadmap Files: `MASTER_ROADMAP_*.md`, `ROADMAP_2026H2.md`, `ROADMAP_AQE.md`, etc.
- QA & Testing: `QA_AUTOMATION_AI_STRATEGY.md`, `QA_ASSESSMENT_*.md`, `TESTING.md`

## Key Subdirectories
### `docs/adr/` (Architecture Decision Records)
Contains 15+ ADRs detailing major technical decisions, such as `ADR-004-clean-architecture.md` and `ADR-008-multi-agent-mcp-mesh.md`.

### `docs/engineering/`
Guidelines for the engineering team.
- `AGENT_COLLABORATION_PROTOCOL.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `SYNC_DRIVEN_DEV.md`
- `SYSTEM_DESIGN.md`

### `docs/vision/`
Strategic documents outlining the past, present, and future phases of the project (e.g., `01_ARCHITECTURE.md`, `15_SECOND_BRAIN.md`, `20_SPEC_GUARDIAN.md`).

### `docs/wiki/`
Appears to be the source for a project wiki, covering `Architecture.md`, `CLI-Reference.md`, `Configuration.md`, `Deployment.md`, etc.

### `docs/recordings/` and `docs/onboarding/`
Materials for onboarding and demonstrating the product, including session transcripts/scripts.

### `docs/qa/` and `docs/evidence/`
Test plans, business regression suites, and evidence ledgers for testing and validation.

## Observations
- **Redundancy**: There are multiple roadmap and vision files (e.g., `ROADMAP_2026H2.md`, `MASTER_ROADMAP_*.md`, and `02_ROADMAP.md` in `vision/`). Some unification is needed.
- **Audience Fragmentation**: The documentation contains a mix of developer-centric docs (ADRs, engineering guides) and end-user/business docs (pitch decks, QA assessment). 
- **Richness**: The documentation is incredibly rich, tracking the exact progression of the AI testing suite over time.
