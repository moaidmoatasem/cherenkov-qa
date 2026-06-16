# Agent Handover — CHERENKOV QA

## Current State
- **691 unit tests passing, 0 failed, 0 deprecation warnings**
- **Commit**: `c026c087` on `main`, aligned with `origin/main` (0 behind/0 ahead)
- **CI**: Billing issue prevents workflow runs (GitHub payments), not a code problem

## What Was Built (This Session)

### Horizon 1: Developer Ecosystem & QA Platforms (Complete)
- **VS Code Extension**: DiagnosticsProvider (red/green squiggles), HoverProvider (verdict on hover), QuickFixProvider (generate/view drift code actions)
- **NotifierPort/Registry**: Clean Architecture `NotifierPort` protocol in `cherenkov/ports/notifier.py`, `NotifierRegistry` in `cherenkov/adapters/notifiers/registry.py` with `from_env()` auto-discovery
- **Adapter interface methods**: Added `send()` and `notify_event()` to all 6 notifiers (Slack, Teams, Linear, Webhook, OpsGenie, PagerDuty) — backward-compatible
- **Jira enhancements**: `create_jira_issue_full()` (labels, priority, components), `bulk_create()`, `add_comment()`, `add_attachment()`
- **npx init script**: `npm-package/bin/cherenkov-init.js` — zero-install bootstrap with Python detection, pip install, config setup

### Horizon 2: AI Ecosystem & Desktop (Complete)
- **LangChain Tool**: `cherenkov/langchain/tool.py` — `CherenkovTool.generate_tests()` and `validate()` for multi-agent frameworks
- **MCP npm package**: `packages/mcp-server/` with package.json, index.js, README, LICENSE
- **Desktop Setup Wizard**: `desktop/src-tauri/src/setup_wizard.rs`, `cherenkov/web/ui/src/components/SetupWizard.tsx`
- **Desktop build verified**: `cargo check` succeeds (14s)

### Horizon 3: Observability & Spec Guardian (Complete)
- **Spec Guardian**: Full module at `cherenkov/spec_guardian/` with core.py, daemon.py, detector.py, store.py — wired to CLI via `legacy_cli.py daemon --guardian`
- **OTEL tracer**: `cherenkov/observability/llm_tracer.py`, `cherenkov/observability/otel.py`
- **Synthetic data generator**: `cherenkov/synthetic/generator.py`, `runner.py`, `cmd.py`
- **Spec Guardian tests**: 18 tests in `tests/unit/test_spec_guardian.py`

### Horizon 4: Market Expansion (Complete)
- **AsyncAPI source adapter**: `cherenkov/sources/asyncapi/` (adapter.py, contracts.py) + `cherenkov/stages/plan_asyncapi.py` — 12 tests
- **Training pipeline**: `cherenkov/training/` (collector.py, dataset.py, trainer.py) — DataCollector (SQLite telemetry), TrainingDataset (JSONL/format), Trainer (LoRA simulation mode) — 12 tests
- **Postman importer tests**: 9 tests in `tests/unit/test_postman_importer.py`

### Quality Improvements
- **Fixed all `datetime.utcnow()` deprecation warnings** across codebase and tests
- **Adversarial testing module**: detector, garak_adapter, runner — 14 tests
- **GraphQL source adapter**: 14 tests in `tests/unit/test_graphql_source.py`
- **gRPC source adapter**: 12 tests in `tests/unit/test_grpc_source.py`

## What Remains (Not Started / Incomplete)

### Low Priority / Stretch
1. **Fine-tuned model training** — The pipeline is built (`cherenkov/training/`) but actual LoRA fine-tuning requires GPU hardware. The `Trainer` runs in simulation mode. To productionize: install `unsloth`, `peft`, `transformers` and replace the simulation methods.
2. **npm/marketplace publishing** — VS Code extension (`vsce package`) and npm package (`npm publish`) never executed. Needs GitHub token and marketplace auth setup.
3. **CI/CD billing fix** — GitHub Actions billing issue blocks workflow runs. Needs payment method update in GitHub settings.
4. **Backstage plugin** — `cherenkov-backstage-plugin/` exists but deployment/testing not verified.
5. **ArgoCD ApplicationSet** — Spec Guardian CRD deployment template not integrated.

## Key Files for Next Agent

| Area | Path |
|------|------|
| VS Code extension | `vscode/` (12 files) |
| Notifier registry | `cherenkov/adapters/notifiers/registry.py` |
| Training pipeline | `cherenkov/training/` |
| AsyncAPI adapter | `cherenkov/sources/asyncapi/` |
| Spec Guardian | `cherenkov/spec_guardian/` |
| LangChain tool | `cherenkov/langchain/tool.py` |
| MCP server package | `packages/mcp-server/` |
| Desktop Tauri | `desktop/src-tauri/` |
| Synthetic data | `cherenkov/synthetic/` |

## Quick Commands
```bash
# Run tests
python3 -m pytest tests/unit/ --no-header

# Run specific test file
python3 -m pytest tests/unit/test_asyncapi_adapter.py -v

# Build desktop
export PATH=$HOME/.cargo/bin:$PATH; cd desktop/src-tauri && cargo check

# Check issues
gh issue list --state open
```
