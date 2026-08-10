# Original User Request

## Initial Request — 2026-06-07T15:34:13Z

# Teamwork Project Prompt — Draft

> Status: Launched

Review the Mistral Vibe comprehensive assessment report of the CHERENKOV-QA project and execute a prioritized slice of the recommendations autonomously, focusing on resolving gate-blocking issues.

Working directory: ~/wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa
Integrity mode: development

## Requirements

### R1. Resolve Critical Risks
Identify and resolve the most pressing "GATE-BLOCKING ISSUES" listed in the report (e.g., UI mock data, Initialize Pilot Run wiring).

### R2. Architectural Integrity
Maintain the design invariants of the CHERENKOV-QA project (D7, anti-lock-in, spec-derived).

## Acceptance Criteria

### Functional
- [ ] At least one P0 gate-blocking issue is completely resolved and functional.
- [ ] No regression introduced into the core Track A execution pipeline.

## Follow-up — 2026-07-30T19:52:35Z

Execute all 5 tracks of the Sprint 4 and Phase 11 roadmap for CHERENKOV-QA: Complete MCP stub tools (Jira, k6, MENA), build the LangChain integration, implement the Tauri Desktop auto-setup wizard, expand the VS Code extension, and publish the MCP server to the registry.

Working directory: Z:\home\moaid\cherenkov-qa
Integrity mode: development

## Requirements

### R1. Complete 3 MCP Stub Tools
Implement the actual business logic for `export_jira_ticket` (Jira REST API v3), `run_k6_perf` (k6 load testing via subprocess), and `scan_mena_compliance` (SAMA/FinCSF compliance validation) in `cherenkov/mcp/handlers.py` and associated adapters.

### R2. Build the LangChain Integration
Create a LangChain Tool class (`CherenkovTool`) that exposes `generate_tests`, `validate`, and `explain_violation`. The team may decide the best location within the repository for this package.

### R3. Desktop Auto-Setup Wizard (Phase 3)
Implement a first-run dependency checker wizard in the existing Tauri app (`desktop/src-tauri`). The frontend framework is up to the team's discretion. It must detect Ollama, Docker, and Node, and gracefully degrade if dependencies can't be fetched locally.

### R4. VS Code Extension Expansion (Phase 11)
Enhance the existing beta extension in `vscode/` with deeper editor integration, specifically adding Test Explorer Integration and inline healing suggestions (e.g., CodeLens or QuickFix) for failed endpoints.

### R5. Publish MCP Server
Create the necessary configuration file (e.g., `smithery.yaml` or `mcp.json`) to register CHERENKOV to the official MCP registry, allowing Cursor/Windsurf users to auto-discover it.

## Acceptance Criteria

### Automated Testing & Compilation
- [ ] `pytest` passes for the new `jira_client.py`, `k6_runner.py`, and `langchain` integrations.
- [ ] `npm run compile` and `npm run lint` pass without errors inside the `vscode/` directory.
- [ ] `cargo check` passes inside `desktop/src-tauri/` without compilation errors.

### Functionality Verification
- [ ] Running the MCP server locally exposes the 3 newly implemented tools, and they return valid structured responses (not "not implemented" stubs) when invoked via a test client script.
- [ ] The LangChain `CherenkovTool` can be successfully imported and instantiated in a standalone python script.
- [ ] The `smithery.yaml` (or equivalent) configuration file exists in the repository root and correctly points to the `cherenkov mcp` entrypoint.

## Follow-up — 2026-08-02T01:22:29Z

# Teamwork Project Prompt — Draft

A fully implemented UI code revamp featuring a completely new, modern aesthetic. The implementation must integrate with existing backend features, maintain end-to-end workflows, and align with the CHERENKOV QA roadmap, north stars, and goals.

Working directory: Z:\home\moaid\cherenkov-qa
Integrity mode: development

## Requirements

### R1. Complete UI/UX Revamp
Design and implement a completely new, modern aesthetic and layout from scratch. The architecture must be scalable and designed to be easy to grow as new features are added in the future.

### R2. End-to-End Backend Wiring & Cleanup
Wire all existing, in-progress, and upcoming backend functionalities seamlessly into the new UI. Actively identify and remove any irrelevant, unused, overly complex, or mocked/fake features from the codebase to streamline the system.

### R3. New UI Automation
With the new UI, introduce completely new UI automation tests to verify functionality. The agents must take the lead on writing programmatic verification (e.g. Playwright/Cypress) for the new end-to-end workflows.

## Acceptance Criteria

### Implementation Quality
- [ ] The new UI is fully implemented, renders correctly, and features a cohesive modern aesthetic.
- [ ] No mocked, fake, or unwired features remain in the active UI (all visible features must connect to actual backend logic).
- [ ] Dead, unused, or overly complex legacy UI code has been cleanly removed.

### Verification
- [ ] New UI automation tests are introduced alongside the new UI.
- [ ] The new UI automation tests execute successfully and verify the core end-to-end workflows.

## Follow-up — 2026-08-10T16:59:22Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Ensure 100% documentation coverage across the entire Cherenkov QA repository, starting from the root and traversing all nested directories.

Working directory: `z:\home\moaid\cherenkov-qa`
Integrity mode: development

## Requirements

### R1. Source Code Documentation
Ensure every public function, class, and module across the codebase (including Python and Go) has descriptive docstrings or comments explaining its purpose, arguments, and return values.

### R2. User-Facing Documentation
Ensure all Markdown files in the `docs/` folder (and all nested folders) are complete, accurate, and free of "TODO" or placeholder text. 

### R3. Programmatic Verification
Create automated scripts to objectively measure documentation coverage. For example, use tools like `pydocstyle` for Python code and markdown link checkers for the `docs/` directory. The scripts must strictly fail if coverage is below 100%.

## Acceptance Criteria

### Verification & Completeness
- [ ] A programmatic verification script for source code docstrings runs and exits with code 0 (100% coverage).
- [ ] A programmatic verification script for Markdown files (checking for broken links, missing references, or empty files) runs and exits with code 0.
- [ ] `grep -ri "TODO\|TBD\|\[\]" docs/` returns no results, proving all placeholders are resolved.



