# Audit Report: Subsystem 3 — MCP Server, Marketplace, Push Events, Auth, and Hook Infrastructure

**Target Subsystem**: Subsystem 3 (MCP & Hooks Infrastructure)  
**Auditor**: Explorer 3  
**Date**: 2026-08-02  
**Working Directory**: `Z:\home\moaid\cherenkov-qa\.agents\explorer_mcp_hooks`  
**Project Root**: `Z:\home\moaid\cherenkov-qa`  

---

## Executive Summary

This deep-dive architectural and code audit evaluates Subsystem 3 of **CHERENKOV-QA**, which comprises the Model Context Protocol (MCP) server architecture, MCP Marketplace, authentication & authorization mechanisms, push events, multi-agent mesh routing, dynamic tool definitions, and the pipeline Hook infrastructure (Phase CC-1 and CC-3 components). 

The audit reveals a modular, clean-architecture design (Ports and Adapters per ADR-004 & ADR-012) built with zero mandatory third-party SDK dependencies for core protocol handling. Key safety mechanisms include shell escaping via `shlex.quote`, working directory path containment verification (`_resolve_within_cwd`), Pydantic v2 input validation at trust boundaries, and policy/guard interceptors. Areas of technical debt include missing subprocess kill on timeout in `SubprocessHookExecutor` (potential zombie processes), hardcoded/stubbed marketplace HTTP methods, and shared global mutable singletons (`_registry`, `_policy`) without thread locks.

---

## Section 1: MCP Architecture & Security

### 1.1 MCP Server Protocols & Transport Layer
* **Files**: `cherenkov/mcp/server.py`, `cherenkov/mcp/protocol.py`, `cherenkov/mcp/contracts.py`
* **Transport Protocol**: JSON-RPC 2.0 over standard I/O (`stdio`).
* **Handshake & Capability Advertisement**:
  * In `server.py` (`_handle_initialize`, lines 50–62), the server processes the `initialize` method, responding with `protocolVersion="2024-11-05"`, `serverInfo=MCPServerInfo(name="cherenkov", version="1.0.0")`, and capabilities advertising `resources`, `tools`, and `prompts`.
  * `notifications/initialized` (`_handle_initialized`, lines 64–68) receives client readiness without returning a response.
* **JSON-RPC Dispatcher**:
  * In `protocol.py` (`dispatch_one`, lines 59–100), incoming newline-delimited JSON strings are parsed (`json.loads`).
  * Request schema is validated using `JsonRpcRequest.model_validate(data)`.
  * Notifications (`id` missing) are executed silently without sending response objects back to `stdout`.
  * Standard JSON-RPC error codes (`PARSE_ERROR` = -32700, `INVALID_REQUEST` = -32600, `METHOD_NOT_FOUND` = -32601, `INTERNAL_ERROR` = -32603) are populated via `_make_error()` helper functions (lines 47–52).
* **Stream Loop**: `serve_stdio` (`protocol.py`, lines 102–128) loops over input lines (`stdin`), allowing stream injection for tests via `input_stream` and `output_stream`.

```python
# cherenkov/mcp/protocol.py:59-100
def dispatch_one(raw: str, table: DispatchTable) -> JsonRpcResponse | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _make_error(None, PARSE_ERROR, f"Parse error: {exc}")

    req_id = data.get("id")
    try:
        req = JsonRpcRequest.model_validate(data)
    except Exception as exc:
        return _make_error(req_id, INVALID_REQUEST, f"Invalid request: {exc}")

    is_notification = "id" not in data
    handler = table.get(req.method)
    if handler is None:
        if is_notification:
            return None
        return _make_error(req.id, METHOD_NOT_FOUND, f"Method not found: {req.method!r}")

    try:
        result = handler(req.params)
        if is_notification:
            return None
        return _make_success(req.id, result)
    except Exception as exc:
        if is_notification:
            return None
        return _make_error(req.id, INTERNAL_ERROR, f"Internal error: {exc}")
```

### 1.2 Tool Definition & Execution Surface
* **Files**: `cherenkov/mcp/handlers.py`, `cherenkov/mcp/tools/sentinel.py`, `cherenkov/mcp/contracts.py`
* **Tool Catalogue**:
  * Exposes high-level tools like `verify_suite`, `verify_system`, `check_suite`, `verify`, `generate`, `hitl_list`, `hitl_approve`, `hitl_reject`, `validate_run_gate`, `visual_diff_baseline_enhanced`, `run_k6_perf`, `export_jira_ticket`, `scan_mena_compliance_enhanced`, `validate_governance_certification`, `mcp_registry_list`, `mcp_registry_publish`, and IDE Sentinel tools (`cherenkov/audit-test-file`, `cherenkov/check-assertion`, `cherenkov/suggest-spec-fix`).
* **Input Validation & Trust Boundary**:
  * MCP peers are considered untrusted. Every handler in `handlers.py` converts raw dict parameters into Pydantic models (e.g. `VerifySuiteInput`, `CheckSuiteInput`, `HitlApproveInput`) before execution.
  * Invariant D7 ("Never auto-edit test code; suggest-only") is enforced across all tools (e.g. `verify_suite` returns a report, `auto_heal_code` produces patches without modifying files).
* **Sentinel Tools**:
  * Defined in `cherenkov/mcp/tools/sentinel.py` (lines 27–108) and registered in `SENTINEL_HANDLERS` (lines 288–292).
  * Wraps `cherenkov.integrity.api.audit_test_integrity` to deliver real-time feedback to IDE coding agents (Cursor, Windsurf, Claude Code).

### 1.3 MCP Marketplace Architecture
* **Files**: `cherenkov/mcp/marketplace/registry.py`, `cherenkov/mcp/marketplace/sandbox.py`, `cherenkov/mcp/install.py`
* **Marketplace Discovery**:
  * `MarketplaceRegistry` (`registry.py`, lines 22–45) provides `discover_tools()` and `get_tool_info(tool_id)`. Currently returns simulated stub tools (`_stub_tools`, lines 47–73) including `slack-notifier`, `github-webhooks`, and `jira-sync`.
* **Sandbox Validator**:
  * `SandboxValidator` (`sandbox.py`, lines 17–42) verifies 3rd-party tool manifests.
  * Ensures `install_command` satisfies strict regex pattern matching (`_ALLOWED_INSTALL_RE`, lines 12–14: `^pip install [a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?(\[[\w,]+\])?(==[\w.*]+)?$`). Commands with shell metacharacters or arbitrary binaries are rejected.
* **Installation Flow**:
  * `install_marketplace_tool` (`install.py`, lines 18–42) fetches tool metadata, validates manifest schema & sandbox rules, and executes installation via `subprocess.run(shlex.split(...))` in an isolated tokenized execution.

```python
# cherenkov/mcp/marketplace/sandbox.py:12-35
_ALLOWED_INSTALL_RE = re.compile(
    r"^pip install [a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?(\[[\w,]+\])?(==[\w.*]+)?$"
)

class SandboxValidator:
    def validate_tool_manifest(self, manifest: dict[str, Any]) -> bool:
        required_keys = {"id", "name", "install_command"}
        if not required_keys.issubset(manifest):
            return False

        cmd = manifest.get("install_command", "")
        if not _ALLOWED_INSTALL_RE.match(cmd):
            return False

        return True
```

### 1.4 JWT Authentication & Authorization
* **Files**: `cherenkov/mcp/auth.py`
* **JWT Token Generation & Verification**:
  * `generate_mcp_token` (lines 15–24) issues tokens signed with HMAC-SHA256 (`HS256`), setting standard claims: issuer (`iss="cherenkov-mcp"`), issued-at (`iat`), expiration (`exp`), and subject (`sub=client_id`).
  * `verify_mcp_token` (lines 26–31) decodes and validates signature and expiration, returning token payload or `None` on failure (`jwt.PyJWTError`).
* **Secret Management & Fallback Warning**:
  * Secret loaded from `os.environ.get("CHERENKOV_JWT_SECRET", "cherenkov-mcp-jwt-secret-change-me")`.
  * `MCPAuthMiddleware` (lines 33–59) emits a runtime `warnings.warn` if authentication is enabled (`require_auth=True`) while using the insecure default secret. Supports dual-mode authentication (API key set or JWT token validation).

### 1.5 Push Event Delivery Mechanism
* **Files**: `cherenkov/mcp/protocol.py` (lines 39–45)
* **Notification Dispatcher**:
  * `send_notification(method: str, params: dict[str, Any] | None = None)` creates an outbound `JsonRpcRequest` lacking an `id` field.
  * Serializes payload to JSON-RPC 2.0 format (`model_dump_json(exclude_none=True)`) and writes directly to `sys.stdout` followed by `sys.stdout.flush()`.
  * Used for server-to-client push events (e.g. status updates, test progress notifications).

---

## Section 2: Hook Infrastructure & Life Cycle

### 2.1 HookEvent Definitions (10 Events)
* **Files**: `cherenkov/hooks/domain/models.py` (lines 12–25)
* **Supported Hook Points (ADR-012)**:
  1. `PRE_GENERATE` (`pre_generate`): Fires prior to scenario/test generation.
  2. `POST_GENERATE` (`post_generate`): Fires immediately following code generation.
  3. `PRE_REVIEW` (`pre_review`): Fires before 6-gate review execution.
  4. `POST_REVIEW` (`post_review`): Fires after 6-gate review completion.
  5. `PRE_VALIDATE` (`pre_validate`): Fires prior to ValidationGate execution.
  6. `POST_VALIDATE` (`post_validate`): Fires following validation report assembly.
  7. `PRE_EJECT` (`pre_eject`): Fires before test suite ejection (`eject` command).
  8. `POST_EJECT` (`post_eject`): Fires after stripping CHERENKOV dependencies.
  9. `PRE_COMMIT` (`pre_commit`): Fires prior to git commit operations.
  10. `POST_COMMIT` (`post_commit`): Fires following pipeline completion/commit.

### 2.2 HookRegistry & TOML Configuration Parsing
* **Files**: `cherenkov/hooks/registry.py`
* **Configuration Loader**:
  * Parses `[hooks.*]` sections from `cherenkov.toml` via `HookRegistry.from_config()`.
  * Supports both single-table definitions (`[hooks.post_validate]`) and array-of-tables definitions (`[[hooks.post_validate]]`) for registering multiple commands under a single event.
  * Rejects invalid event names with a explicit `ValueError` (lines 53–57).
  * Graceful degradation: `load_registry_from_project` (lines 117–149) falls back to `HookRegistry.empty()` if `cherenkov.toml` is absent or unparseable.

```python
# cherenkov/hooks/registry.py:52-93
for event_name, raw in hooks_section.items():
    if event_name not in _VALID_EVENTS:
        raise ValueError(
            f"Unknown hook event {event_name!r} in cherenkov.toml [hooks.*]. "
            f"Valid events: {sorted(_VALID_EVENTS)}"
        )
    event = HookEvent(event_name)
    entries = raw if isinstance(raw, list) else [raw]

    hook_list: list[HookConfig] = []
    for entry in entries:
        if not isinstance(entry, dict) or "run" not in entry:
            continue
        fail_mode_str = entry.get("fail_mode", "warn")
        try:
            fail_mode = FailMode(fail_mode_str)
        except ValueError:
            fail_mode = FailMode.WARN

        hook_list.append(
            HookConfig(
                event=event,
                run=entry["run"],
                timeout=int(entry.get("timeout", 30)),
                fail_mode=fail_mode,
                env=entry.get("env", {}),
            )
        )
```

### 2.3 SubprocessHookExecutor & Lifecycle Execution
* **Files**: `cherenkov/hooks/adapters/subprocess_executor.py`, `cherenkov/hooks/ports/executor.py`
* **Port / Adapter Interface**:
  * Implements `HookExecutor` `Protocol` (ADR-004 Clean Architecture ports & adapters).
* **Template Variable Rendering & Shell Safety**:
  * Injected variables (`{report_path}`, `{output_dir}`, `{verdict}`, `{endpoint}`, `{spec_path}`) are escaped using `shlex.quote(v)` to prevent shell injection (lines 34–37).
* **Execution & Environment Injection**:
  * Executes rendered command with `subprocess.run(rendered_cmd, shell=True, timeout=config.timeout, env={**_current_env(), **config.env})`.
* **Fail Mode Policies (`WARN` vs `ABORT`)**:
  * `FailMode.WARN` (default): Command failures (`exit_code != 0`) or timeouts return a `HookResult` with `status=HookStatus.FAILED` or `HookStatus.TIMEOUT`, allowing the pipeline to log and continue.
  * `FailMode.ABORT`: Raises `HookAbortError` (`domain/models.py`, lines 109–119), immediately halting pipeline execution.

```python
# cherenkov/hooks/adapters/subprocess_executor.py:34-40
template_vars = context.as_template_vars()
safe_vars = {k: shlex.quote(v) if v else "''" for k, v in template_vars.items()}
try:
    rendered_cmd = config.run.format(**safe_vars)
except KeyError as exc:
    result = HookResult(
        event=config.event,
        status=HookStatus.FAILED,
        command=config.run,
        error_message=f"Unknown template variable: {exc}",
    )
    return self._handle_failure(config, result)
```

---

## Section 3: Design Patterns

| Pattern | Location / Implementation | Architectural Value |
|---|---|---|
| **Ports & Adapters (Hexagonal)** | `cherenkov/hooks/ports/executor.py` (`HookExecutor` protocol) & `adapters/subprocess_executor.py` (`SubprocessHookExecutor`) | Isolates core domain models from OS-level subprocess I/O. Facilitates mock testing without subprocess execution. |
| **Chain of Responsibility / Middleware** | `cherenkov/mcp/handlers.py` (`handle_tool_call`), `policy.py` (`PolicyEngine`), `auth.py` (`MCPAuthMiddleware`), `chat/guard.py` | Inbound requests pass sequentially through JWT auth -> Policy checks -> Guard safety rules -> Tool dispatch. |
| **Registry Pattern** | `HookRegistry` (`hooks/registry.py`), `MCPRegistry` (`mcp/mesh_router.py`), `MarketplaceRegistry` (`mcp/marketplace/registry.py`) | Provides centralized lookup, registration, and discovery of hooks, remote MCP tools, and marketplace extensions. |
| **Interceptor / Guard** | `PolicyEngine.is_tool_allowed()`, `SafetyGuard.check_tool_call()` | Intercepts tool execution to enforce server/profile allowlists/blocklists and safety policies without polluting tool logic. |
| **Observer Pattern** | Hook lifecycle events (`HookEvent` enum) & push notifications (`send_notification`) | Allows external scripts or MCP clients to react to pipeline milestones (post-validate, post-review) asynchronously. |
| **Command Pattern** | `HookConfig.run`, `JsonRpcRequest`, `MCPToolCallInput` | Encapsulates executable actions, environment parameters, timeouts, and arguments as serializable objects. |

---

## Section 4: Code Quality, Security & Concurrency Analysis

### 4.1 Process Execution Safety & Shell Injection Prevention
* **Template Substitution**: In `SubprocessHookExecutor` (lines 35), `shlex.quote` is applied to all template context values before calling `str.format()`. This prevents command injection via malformed endpoints or file paths.
* **Path Containment Boundary**: Handlers use `_resolve_within_cwd()` (`handlers.py`, lines 98–112) to verify that user-supplied paths (`suite_path`, `spec_path`, `candidate_path`) resolve strictly within the active working directory:
  ```python
  if not str(resolved).startswith(str(cwd)):
      return f"{path} must be within the working directory."
  ```
* **Marketplace Installer Regex**: `SandboxValidator` enforces strict alphanumeric/version regex on pip install strings, preventing execution of chained shell operators (e.g. `pip install pkg && rm -rf /`).

### 4.2 Security Vulnerabilities & Subprocess Handling Deficiencies
* **Subprocess Timeout Zombie Hazard**:
  * In `SubprocessHookExecutor.execute` (lines 82–91), catching `subprocess.TimeoutExpired` captures timing metadata and invokes `_handle_failure`.
  * **Defect**: `subprocess.run` with `shell=True` spawns a subshell process. When `TimeoutExpired` occurs, `subprocess.run` attempts to kill the parent shell process, but child processes spawned by the shell (e.g. long-running background tasks or node scripts) remain running as orphan/zombie processes.
* **JWT Weak Secret Default**:
  * `auth.py` defines `_DEFAULT_JWT_SECRET = "cherenkov-mcp-jwt-secret-change-me"`. Although `MCPAuthMiddleware` emits a warning when `require_auth=True`, if `require_auth=False` (the default), no secret validation occurs, exposing HTTP transport modes to unauthorized invocation if enabled.

### 4.3 Concurrency & State Handling
* **Stdio Single-Thread Loop**: The standard JSON-RPC stdio server (`protocol.py`) processes incoming JSON lines synchronously in a single thread loop. This avoids race conditions on stdio streams but can block stdin processing during long-running tool executions (e.g. `verify_system` or `run_k6_perf`).
* **Global Mutable Singletons without Locks**:
  * `_registry` in `mesh_router.py` (lines 177–180) and `_policy` in `handlers.py` (lines 85) are global singletons accessed and modified by requests (e.g. `mcp_registry_publish`, `policy_reload`). They lack `threading.Lock` primitives, making them vulnerable to race conditions if the server is run in multi-threaded HTTP mode.

### 4.4 Exception Propagation & JSON-RPC Error Handling
* In `protocol.py` (`dispatch_one`), errors are safely caught and wrapped:
  * Parse failure -> JSON-RPC code `-32700` (`PARSE_ERROR`).
  * Pydantic schema validation failure -> JSON-RPC code `-32600` (`INVALID_REQUEST`).
  * Unhandled handler exception -> JSON-RPC code `-32603` (`INTERNAL_ERROR`).
* Uncaught exceptions never crash the stdio server loop; errors are written as valid JSON-RPC response frames to stdout, preserving protocol connectivity.

---

## Section 5: Architectural Strengths & Technical Debt

### 5.1 Architectural Strengths
1. **Clean Architecture (Ports & Adapters)**: Strict separation between pure domain models (`hooks/domain/models.py`), abstract interfaces (`hooks/ports/executor.py`), and concrete I/O adapters (`hooks/adapters/subprocess_executor.py`).
2. **Zero-Dependency Core Protocol**: JSON-RPC 2.0 stdio server (`protocol.py`, `server.py`) is implemented using Python standard library primitives without requiring third-party MCP SDKs.
3. **Multi-Layer Security Interceptors**: Combines Policy Engine (`cherenkov-policy.json`), Safety Guard (`get_guard()`), Pydantic schema boundaries, and `shlex.quote` escaping.
4. **Strict Adherence to Invariant D7**: All MCP tools operate in suggest/report mode, guaranteeing that AI agents calling CHERENKOV tools cannot auto-modify or mutate test suites without human approval.
5. **Real-Time IDE Feedback (Sentinel)**: Direct integration of integrity checks into IDE agent tool calls via `cherenkov/tools/sentinel.py`.

### 5.2 Technical Debt & Recommended Fixes

1. **Subprocess Process Tree Termination on Timeout**:
   * *Issue*: `subprocess.run` with `shell=True` leaves orphan process trees when timing out.
   * *Fix*: Implement `popen` with process group creation (`start_new_session=True` on Unix, `CREATE_NEW_PROCESS_GROUP` on Windows) and send `SIGKILL`/`TerminateProcess` to the process group in an explicit `try...finally` or timeout handler.

2. **Marketplace Network Implementation**:
   * *Issue*: `MarketplaceRegistry.discover_tools()` relies on static stub tools (`_stub_tools`).
   * *Fix*: Implement asynchronous HTTP fetching via `httpx` with timeout and fallback caching.

3. **Singleton Thread Safety**:
   * *Issue*: `MCPRegistry` (`_registry`) and `PolicyEngine` (`_policy`) mutate internal dicts without mutex locks.
   * *Fix*: Add `threading.RLock()` guarding write operations (`register_server`, `unregister_server`, `reload`).

4. **Async/Non-Blocking Tool Dispatch for Stdio Server**:
   * *Issue*: Heavy tools (such as `verify_system` or `run_k6_perf`) block the main stdio loop.
   * *Fix*: Introduce an `asyncio` or worker-thread-based dispatch loop for long-running MCP tool executions.

---

## Section 6: Verification Method & Evidence

### 6.1 Unit Test Suite Execution
To verify the audit findings and code behavior, run the unit test suite for MCP and Hooks:

```bash
pytest tests/unit/test_hooks.py tests/unit/test_mcp_auth.py tests/unit/test_mcp_install.py tests/unit/test_mcp_marketplace.py tests/unit/test_mcp_registry.py tests/unit/test_mcp_sentinel.py -v
```

### 6.2 Smoke Test Execution
Verify stdio protocol functionality:

```bash
python tests/smoke/smoke_test_mcp.py
```

---

## Conclusion

Subsystem 3 (MCP & Hooks) in CHERENKOV-QA displays exceptional design discipline, robust input validation, clean architectural separation, and strict compliance with project invariants (D7 suggest-only and clean architecture). Addressing the identified technical debt (subprocess process group termination and singleton thread locks) will solidify the subsystem for enterprise production workloads.
