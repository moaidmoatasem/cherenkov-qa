# Handoff Report: Subsystem 3 Deep-Dive Audit (MCP Server & Hooks)

## 1. Observation
- Audited `cherenkov/mcp/` (server, protocol, contracts, handlers, auth, client, install, policy, mesh_router, marketplace/, tools/sentinel.py) and `cherenkov/hooks/` (domain/models.py, ports/executor.py, registry.py, adapters/subprocess_executor.py).
- Verified tests: `tests/unit/test_hooks.py`, `tests/unit/test_mcp_auth.py`, `tests/unit/test_mcp_registry.py`, `tests/unit/test_mcp_sentinel.py`, `tests/unit/test_mcp_install.py`, `tests/unit/test_mcp_marketplace.py`.
- Audit report generated and written to `Z:\home\moaid\cherenkov-qa\.agents\explorer_mcp_hooks\audit_report.md`.

## 2. Logic Chain
- Standard JSON-RPC 2.0 stdio protocol implemented without external MCP SDKs (`protocol.py`, `server.py`).
- Pydantic v2 input validation models (`contracts.py`) enforce trust boundaries for untrusted MCP peers before any handlers touch queue or gate stores.
- Invariant D7 ("Suggest-only, never auto-edit test code") strictly preserved across all tools.
- Process safety enforced via `shlex.quote` for hook template rendering and `_resolve_within_cwd` for file paths.
- Marketplace command validation uses strict pip regex (`_ALLOWED_INSTALL_RE`).
- Subprocess timeout handling in `SubprocessHookExecutor` currently catches `TimeoutExpired` but does not kill process trees spawned via `shell=True`.

## 3. Caveats
- Direct network integration with external live MCP marketplace servers is currently stubbed (`_stub_tools`).
- Stdio transport runs synchronously on single-thread loop; long-running tool execution blocks incoming requests until completion.

## 4. Conclusion
Subsystem 3 demonstrates high architectural compliance with Clean Architecture (ADR-004, ADR-012) and project invariants. Recommended improvements focus on process tree kill on hook timeouts and thread-locking global registry singletons.

## 5. Verification Method
- Execute pytest: `pytest tests/unit/test_hooks.py tests/unit/test_mcp_*.py`
- Run smoke test: `python tests/smoke/smoke_test_mcp.py`
- Inspect `audit_report.md` in `.agents/explorer_mcp_hooks/`.
