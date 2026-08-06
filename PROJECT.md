# Project: CHERENKOV-QA

## Architecture
- `cherenkov/mcp/`: MCP server implementation & handlers.
- `cherenkov/integrations/` or `cherenkov/langchain/`: LangChain tools & integration.
- `desktop/src-tauri/`: Tauri 2 Desktop app backend (Rust) & frontend.
- `vscode/`: VS Code Extension (TypeScript).
- Root: Registry configuration (`smithery.yaml`, `mcp.json`).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Victory Audit Fixes | Fix 5 gate-blocking issues | none | DONE |
| 2 | MCP Stub Tools | Implement Jira, k6, MENA compliance tools & tests | none | PLANNED |
| 3 | LangChain Integration | Implement `CherenkovTool` & tests | M2 | PLANNED |
| 4 | Desktop Auto-Setup Wizard | Tauri 2 dependency checker (Ollama, Docker, Node) | none | PLANNED |
| 5 | VS Code Extension Expansion | Test Explorer & inline healing CodeLens/QuickFix | none | PLANNED |
| 6 | Publish MCP Server | Create `smithery.yaml`/`mcp.json` registry config | M2 | PLANNED |

## Interface Contracts
- MCP tools MUST expose structured JSON responses for Jira export, k6 performance runs, and MENA compliance scans.
- `CherenkovTool` MUST expose `generate_tests`, `validate`, `explain_violation` actions cleanly as a LangChain BaseTool.
- Tauri desktop wizard MUST check for Ollama, Docker, and Node binaries/services without crashing and degrade gracefully.
- VS Code extension MUST integrate with VS Code Test Controller API and provide CodeLens/QuickFix providers for spec violations.
- Smithery config MUST specify command `cherenkov` with arguments `["mcp"]`.

## Code Layout
- Backend / MCP: `cherenkov/mcp/`, `cherenkov/`
- LangChain: `cherenkov/` (e.g., `cherenkov/integrations/langchain.py` or `cherenkov/langchain/`)
- Desktop: `desktop/src-tauri/`
- VS Code: `vscode/`
- MCP Config: `smithery.yaml` / `mcp.json`
