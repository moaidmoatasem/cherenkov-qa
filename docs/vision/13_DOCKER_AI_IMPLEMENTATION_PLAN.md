# CHERENKOV — Horizon 3: Docker AI Integration — Implementation Plan

**Status:** Draft · **Date:** 2026-06-07
**Parent:** [`12_DOCKER_AI_HORIZON.md`](12_DOCKER_AI_HORIZON.md) (strategic overview)
**Invariants:** D7, anti-lock-in, suggest-only, spec-derived, egress sovereignty — all preserved; each change has a non-Docker fallback.

---

## Table of Contents

- [Phase A — MCP Gateway Foundation (complete)](#phase-a--mcp-gateway-foundation-complete)
- [Phase B — Sandbox-Heal Convergence](#phase-b--sandbox-heal-convergence)
- [Phase C — Governance Layer](#phase-c--governance-layer)
- [Phase D — Model Runner & Offload](#phase-d--model-runner--offload)
- [Phase E — Compose Agents & Hub Publishing](#phase-e--compose-agents--hub-publishing)
- [Cross-cutting: Config Schema](#cross-cutting-config-schema)
- [Cross-cutting: Testing Strategy](#cross-cutting-testing-strategy)
- [Dependency Graph & Sequencing](#dependency-graph--sequencing)

---

## Phase A — MCP Gateway Foundation (complete)

**Status:** ✅ Done · Commits: `a8c00d2d`, `8d8ef507`, `40a86931`

### Files created

| File | Purpose |
|------|---------|
| `Dockerfile.mcp` | Slim Python 3.10-slim image, only `cherenkov/` + `requirements.txt`, entrypoint `cherenkov.py mcp serve` |
| `cherenkov-mcp.yaml` | MCP server entry spec: name, image, env, type |
| `.mcp.json` | Root MCP config for openIDE — `docker mcp gateway run --profile full-dev` |
| `.cursor/mcp.json` | Cursor MCP config — same profile |
| `.vscode/mcp.json` | VS Code MCP config — same profile |
| `docs/vision/12_DOCKER_AI_HORIZON.md` | Strategic overview |

### Files modified

| File | Change |
|------|--------|
| `skills/mcp-integration.md` | Added Docker MCP Gateway docs: profiles, auth, tool tables |

### Profiles created in Docker MCP Gateway

| Profile | Servers | Purpose |
|---------|---------|---------|
| `full-dev` | cherenkov, context7, sequentialthinking, github-official, atlassian-remote | Daily development — 48 tools |
| `ai_coding` | cherenkov, context7, sequentialthinking | No-auth subset for quick use |

### Client connections (system-wide)

opencode, claude-code, cline, continue, gemini, vscode — all connected to `full-dev`.

---

## Phase B — Sandbox-Heal Convergence

**Goal:** Replace filesystem-based sandbox isolation with Docker Sandboxes (E2B) for true container-boundary isolation. D7 becomes platform-enforced.

### B1 — Add sandbox provider abstraction

**File to create:** `cherenkov/healing/providers/__init__.py`
**File to create:** `cherenkov/healing/providers/base.py`
**File to create:** `cherenkov/healing/providers/filesystem.py`
**File to create:** `cherenkov/healing/providers/docker_sandbox.py`

**Changes:**

1. Define abstract `SandboxProvider` in `base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class SandboxResult:
    passed: bool
    exit_code: int
    stdout: str
    stderr: str

class SandboxProvider(ABC):
    @abstractmethod
    def replicate_workspace(self, scenario_id: str, stub_dir: str) -> str:
        """Copy stubs to isolated workspace. Return workspace path."""
        ...

    @abstractmethod
    def execute_test(self, workspace: str, spec: str, api_url: str) -> SandboxResult:
        """Run a Playwright test in the workspace."""
        ...

    @abstractmethod
    def destroy_workspace(self, workspace: str) -> None:
        """Clean up the workspace."""
        ...

    @abstractmethod
    def read_file(self, workspace: str, path: str) -> str:
        """Read a file from the workspace (for diff extraction)."""
        ...
```

2. Move existing logic to `filesystem.py`:

- `replicate_workspace` → copy `stub/` to `.cherenkov/sandbox_{id}/`, symlink `node_modules`
- `execute_test` → `subprocess.run([npx, playwright, test, ...])`
- `destroy_workspace` → `shutil.rmtree(workspace)`
- `read_file` → `open(path).read()`

3. Implement `docker_sandbox.py`:

```python
class DockerSandboxProvider(SandboxProvider):
    def __init__(self, image: str = "cherenkov-mcp:latest"):
        self.image = image

    def replicate_workspace(self, scenario_id: str, stub_dir: str) -> str:
        # Build a sandbox container image with stubs baked in
        # or mount stubs as a Docker volume
        container_id = subprocess.check_output([
            "docker", "create",
            "--rm",
            "--network", "host",
            "-v", f"{stub_dir}:/workspace/stub:ro",
            self.image,
            "python", "-m", "pytest", "/workspace"
        ]).decode().strip()
        return container_id

    def execute_test(self, container_id: str, spec: str, api_url: str) -> SandboxResult:
        result = subprocess.run(
            ["docker", "start", "-a", container_id],
            capture_output=True, text=True,
            env={**os.environ, "API_URL": api_url}
        )
        return SandboxResult(
            passed=(result.returncode == 0),
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr
        )

    def destroy_workspace(self, container_id: str) -> None:
        subprocess.run(["docker", "rm", "-f", container_id],
                       capture_output=True)

    def read_file(self, container_id: str, path: str) -> str:
        result = subprocess.run(
            ["docker", "cp", f"{container_id}:{path}", "-"],
            capture_output=True
        )
        return result.stdout.decode()
```

### B2 — Refactor SandboxHealer to use provider

**File to modify:** `cherenkov/healing/sandbox_healer.py`

**Changes:**

```python
class SandboxHealer:
    def __init__(self, run_id: str | None = None, provider: str = "filesystem"):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.provider = self._resolve_provider(provider)
        ...

    def _resolve_provider(self, name: str) -> SandboxProvider:
        if name == "docker":
            return DockerSandboxProvider()
        return FilesystemSandboxProvider()  # default

    def replicate_workspace(self, scenario_id: str) -> str:
        return self.provider.replicate_workspace(scenario_id, self.stub_dir)

    def execute_playwright_sandbox(self, sandbox_dir: str, ...) -> dict:
        result = self.provider.execute_test(sandbox_dir, spec_filename, api_url)
        return {"passed": result.passed, ...}

    def run_deep_healing(self, ...) -> dict:
        # ... same logic, but uses self.provider for all workspace ops ...
```

### B3 — Wire provider selection into config

**File to modify:** `cherenkov.toml` (or add `[healing]` section)

```toml
[healing]
sandbox_provider = "filesystem"    # "filesystem" | "docker"
docker_image = "cherenkov-mcp:latest"
docker_network = "host"
max_repair_attempts = 3
```

### B4 — Extend SandboxHealer MCP tool with provider param

**File to modify:** `cherenkov/mcp/contracts.py` — add `provider` to `ValidateRunGateInput` schema
**File to modify:** `cherenkov/mcp/handlers.py` — pass provider to healer

### B5 — Update CI workflow

**File to modify:** `.github/workflows/ci.yml`

Add a `sandbox-heal-docker` job that runs `smoke_test_deep_healing.py` with `sandbox_provider=docker`:

```yaml
  sandbox-heal-docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: python -m pytest track-b-c-deferred/smoke_tests/smoke_test_deep_healing.py \
              -k "sandbox" --sandbox-provider docker
```

### B6 — Smoke tests

**File to modify:** `track-b-c-deferred/smoke_tests/smoke_test_deep_healing.py`

Add test cases:
- `test_sandbox_filesystem_provider` — existing behavior, unchanged
- `test_sandbox_docker_provider` — identical scenario, provider=docker
- `test_sandbox_provider_parity` — both providers produce identical diffs for same input

### B7 — Rollback

- Set `sandbox_provider = "filesystem"` in `cherenkov.toml` restores original behavior
- `DockerSandboxProvider` class not imported if provider is `filesystem`
- No Docker dependency at import time

---

## Phase C — Governance Layer

**Goal:** Codify CHERENKOV's design invariants as Docker AI Governance policy. Govern which MCP tools each agent profile can use.

### C1 — Define `cherenkov-policy.json`

**File to create:** `cherenkov-policy.json`

```json
{
  "version": "1.0",
  "profiles": {
    "full-dev": {
      "servers": {
        "cherenkov": {
          "tools": ["hitl_list", "hitl_approve", "hitl_reject", "validate_run_gate"],
          "allow_network": [],
          "allow_filesystem": false
        },
        "github-official": {
          "tools": [
            "list_issues", "search_code", "get_file_contents",
            "list_pull_requests", "pull_request_read",
            "create_branch", "create_pull_request", "push_files"
          ],
          "blocked_tools": [
            "delete_file", "create_repository", "fork_repository"
          ],
          "allow_network": ["api.github.com:443"]
        },
        "context7": {
          "tools": ["resolve_library_id", "get_library_docs"],
          "allow_network": ["*"]
        },
        "sequentialthinking": {
          "tools": ["sequentialthinking"],
          "allow_network": [],
          "allow_filesystem": false
        },
        "atlassian-remote": {
          "tools": ["*"],
          "allow_network": ["mcp.atlassian.com:443"]
        }
      }
    },
    "ai_coding": {
      "servers": {
        "cherenkov": { "tools": ["*"], "allow_network": [] },
        "context7": { "tools": ["*"], "allow_network": ["*"] },
        "sequentialthinking": { "tools": ["*"], "allow_network": [] }
      }
    }
  },
  "invariants": {
    "d7_suggest_only": {
      "enabled": true,
      "enforcement": "governance",
      "message": "Never auto-edit test code. All heal suggestions are diff-only."
    },
    "anti_lock_in": {
      "enabled": true,
      "enforcement": "convention",
      "message": "Every component has a non-Docker fallback."
    },
    "egress_sovereignty": {
      "enabled": true,
      "enforcement": "policy",
      "message": "Egress dial must be respected by all MCP servers."
    }
  }
}
```

### C2 — Add policy validation to gateway startup

**File to create:** `cherenkov/mcp/policy.py`

```python
"""
Policy enforcement for MCP tool access.
Reads cherenkov-policy.json and validates tool calls against allowlists.
"""

import json
from pathlib import Path
from typing import Any

class PolicyEngine:
    def __init__(self, policy_path: str = "cherenkov-policy.json"):
        self.policy = json.loads(Path(policy_path).read_text())

    def is_tool_allowed(self, profile: str, server: str, tool: str) -> bool:
        profile_cfg = self.policy["profiles"].get(profile, {})
        server_cfg = profile_cfg.get("servers", {}).get(server, {})
        allowed = server_cfg.get("tools", ["*"])
        blocked = server_cfg.get("blocked_tools", [])
        if tool in blocked:
            return False
        if "*" in allowed:
            return True
        return tool in allowed

    def is_network_allowed(self, profile: str, server: str, host: str) -> bool:
        profile_cfg = self.policy["profiles"].get(profile, {})
        server_cfg = profile_cfg.get("servers", {}).get(server, {})
        allowed = server_cfg.get("allow_network", ["*"])
        if "*" in allowed:
            return True
        return host in allowed
```

### C3 — Wire policy into MCP tool call handler

**File to modify:** `cherenkov/mcp/handlers.py`

```python
from cherenkov.mcp.policy import PolicyEngine

policy = PolicyEngine()

def handle_tool_call(params: dict[str, Any]) -> dict[str, Any]:
    tool_name = params.get("name", "")
    server_name = params.get("server", "cherenkov")
    profile = os.environ.get("MCP_PROFILE", "full-dev")

    if not policy.is_tool_allowed(profile, server_name, tool_name):
        return {
            "content": [{"type": "text", "text": f"Tool '{tool_name}' blocked by policy"}],
            "isError": True
        }
    # ... existing dispatch logic ...
```

### C4 — Policy tool for gateway management

**File to modify:** `cherenkov/mcp/handlers.py`

Add `policy_list` and `policy_reload` tools:

```python
# In TOOLS list:
MCPTool(
    name="policy_list",
    description="List current policy allow/block rules for all servers and profiles",
    inputSchema=MCPToolInputSchema(type="object", properties={})
),
MCPTool(
    name="policy_reload",
    description="Reload cherenkov-policy.json from disk",
    inputSchema=MCPToolInputSchema(type="object", properties={})
),
```

### C5 — Tests

**File to create:** `test_mcp_policy.py`

- `test_policy_allows_known_tool`
- `test_policy_blocks_unknown_tool`
- `test_policy_allows_all_when_wildcard`
- `test_policy_blocks_tool_in_blocked_list`
- `test_policy_network_allow`
- `test_policy_network_block`
- `test_handle_tool_call_respects_policy`
- `test_policy_reload_updates_runtime`

---

## Phase D — Model Runner & Offload

**Goal:** Add Docker Model Runner as a substrate provider. Enable cloud GPU via Docker Offload for CI.

### D1 — Model Runner client adapter

**File to create:** `cherenkov/ai/model_runner_client.py`

```python
"""
Docker Model Runner adapter for CHERENKOV substrate router.
Conforms to the same interface as ollama_client.py.
"""

import subprocess
import json

class ModelRunnerClient:
    def __init__(self, model: str = "qwen2.5-coder:7b"):
        self.model = model

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        cmd = ["docker", "model", "run", self.model, "--prompt", prompt]
        if system_prompt:
            cmd += ["--system", system_prompt]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    def list_models(self) -> list[str]:
        result = subprocess.run(
            ["docker", "model", "list", "--format", "json"],
            capture_output=True, text=True
        )
        return [m["name"] for m in json.loads(result.stdout)]
```

### D2 — Substrate router integration

**File to modify:** `cherenkov/ai/ollama_client.py` (or create `cherenkov/ai/router.py`)

```python
from cherenkov.ai.ollama_client import OllamaClient
from cherenkov.ai.model_runner_client import ModelRunnerClient

class InferenceRouter:
    def __init__(self, provider: str = "ollama"):
        self.provider = provider
        self._clients = {
            "ollama": OllamaClient,
            "model-runner": ModelRunnerClient,
        }

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        client_cls = self._clients.get(self.provider)
        if not client_cls:
            raise ValueError(f"Unknown provider: {self.provider}")
        return client_cls().complete(prompt, system_prompt)
```

### D3 — Config for provider selection

**File to modify:** `cherenkov.toml`

```toml
[inference]
provider = "ollama"           # "ollama" | "model-runner" | "openai"
model = "qwen2.5-coder:7b"

[inference.model_runner]
model = "qwen2.5-coder:7b"

[inference.ollama]
host = "http://localhost:11434"
model = "qwen2.5-coder:7b"
```

### D4 — CI Offload support

**File to modify:** `.github/workflows/ci.yml`

Add Docker Offload to the `live-llm-generate` job:

```yaml
  live-llm-generate:
    if: github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - uses: docker/offload-action@v1
        with:
          docker-config: ${{ secrets.DOCKER_CONFIG }}
      - run: docker compose --profile full up -d
      - run: ./bin/cherenkov generate --target ${{ secrets.TARGET_URL }}
```

### D5 — Tests

**File to create:** `test_model_runner_client.py`
- `test_complete_returns_string`
- `test_list_models_returns_list`
- `test_router_switches_provider`

---

## Phase E — Compose Agents & Hub Publishing

**Goal:** Deploy CHERENKOV agents as Docker Compose services. Publish images to Docker Hub.

### E1 — Add Docker Hub MCP to full-dev profile

```bash
docker mcp profile server add full-dev \
  --server catalog://mcp/docker-mcp-catalog/docker-hub
```

**File to modify:** `skills/mcp-integration.md`

### E2 — CI publish workflow

**File to create:** `.github/workflows/publish.yml`

```yaml
name: Publish to Docker Hub
on:
  push:
    branches: [main]
    paths: ['Dockerfile', 'Dockerfile.mcp', 'cherenkov/**']

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Build and push MCP image
        uses: docker/build-push-action@v5
        with:
          file: Dockerfile.mcp
          tags: |
            ${{ vars.DOCKER_ORG }}/cherenkov-mcp:latest
            ${{ vars.DOCKER_ORG }}/cherenkov-mcp:${{ github.sha }}
          push: true
```

### E3 — Compose agent profile

**File to modify:** `docker-compose.yml` — add agent services:

```yaml
services:
  # ... existing prism, cherenkov, ollama ...

  explorer-agent:
    profiles: ["agents"]
    build: .
    command: python -m cherenkov explore --daemon
    environment:
      - OLLAMA_HOST=http://ollama:11434
    depends_on:
      - ollama

  healer-agent:
    profiles: ["agents"]
    build: .
    command: python -m cherenkov heal --daemon --provider docker
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - ollama

  daemon-agent:
    profiles: ["agents"]
    build: .
    command: python -m cherenkov daemon --watch
    depends_on:
      - ollama
```

### E4 — Startup script

**File to create:** `scripts/start-agent-fabric.sh`

```bash
#!/usr/bin/env bash
# Start the full CHERENKOV agent fabric
docker compose --profile agents up -d
docker compose exec daemon-agent cherenkov daemon --watch
```

---

## Cross-cutting: Config Schema

### `cherenkov.toml` additions (cumulative)

```toml
# ── Sandbox Provider (Phase B) ──────────────────────────────────
[healing]
sandbox_provider = "filesystem"   # "filesystem" | "docker"
docker_image = "cherenkov-mcp:latest"
max_repair_attempts = 3

# ── MCP Policy (Phase C) ────────────────────────────────────────
[mcp]
policy_file = "cherenkov-policy.json"
profile = "full-dev"

# ── Inference Provider (Phase D) ────────────────────────────────
[inference]
provider = "ollama"               # "ollama" | "model-runner" | "openai"

[inference.ollama]
host = "http://localhost:11434"
model = "qwen2.5-coder:7b"

[inference.model_runner]
model = "qwen2.5-coder:7b"
```

---

## Cross-cutting: Testing Strategy

### Test matrix

| Test file | Phase | Coverage |
|-----------|-------|----------|
| `test_mcp.py` (30 tests) | A | Existing — MCP protocol, tools, validation |
| `smoke_test_mcp.py` | A | Existing — MCP end-to-end smoke |
| `test_mcp_policy.py` (~8 tests) | C | Policy allow/block/reload |
| `test_sandbox_providers.py` (~6 tests) | B | Filesystem + Docker provider parity |
| `test_model_runner_client.py` (~3 tests) | D | Model Runner adapter |
| `smoke_test_deep_healing.py` (updated) | B | Provider-specific healing smoke |

### D7 verification tests

Each phase adds a test proving the D7 invariant:

```python
def test_docker_sandbox_cannot_modify_host():
    """D7: Docker sandbox process cannot write to host filesystem."""
    provider = DockerSandboxProvider()
    workspace = provider.replicate_workspace("d7-test", STUB_DIR)
    result = provider.execute(workspace, "echo 'host write' > /outside/test.txt")
    assert not os.path.exists("/outside/test.txt")
    provider.destroy_workspace(workspace)

def test_filesystem_sandbox_d7_fallback():
    """Anti-lock-in: filesystem provider passes same D7 semantic."""
    provider = FilesystemSandboxProvider()
    workspace = provider.replicate_workspace("d7-test", STUB_DIR)
    assert os.path.exists(workspace)  # workspace created
    assert not os.path.exists("/outside/test.txt")  # host untouched
    provider.destroy_workspace(workspace)
```

---

## Dependency Graph & Sequencing

```
Phase A (done)
  │
  ├──► Phase B (sandbox providers)
  │      └──► B5 (CI docker job) ← depends on B1-B4
  │
  ├──► Phase C (governance)
  │      └──► C3 (wire into handler) ← depends on C1-C2
  │
  └──► Phase D (model runner / offload)
  │      └──► D4 (CI offload) ← depends on D1-D3
  │
  └──► Phase E (hub / compose agents)
         └──► E2 (CI publish) ← depends on E1
         └──► E3 (compose agents) ← independent
```

**Parallelizable:** B, C, and D share no code dependencies and can be built concurrently. E depends on the Docker Hub MCP server but is independent of B-D.

**Recommended order:** B (sandbox) → C (governance) → D (model runner) → E (compose), with B + D having highest user-facing impact.

---

## Summary: Files Created & Modified

| Phase | Create | Modify | Total Files |
|-------|--------|--------|-------------|
| A | 7 | 1 | 8 |
| B | 4 | 4 | 8 |
| C | 2 | 3 | 5 |
| D | 2 | 2 | 4 |
| E | 3 | 3 | 6 |
| **Total** | **18** | **13** | **31** |
