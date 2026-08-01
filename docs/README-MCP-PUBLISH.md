# Publishing CHERENKOV MCP to the Official Registry

**Status: READY FOR HUMAN SUBMISSION (issue #792, epic #790).**
The submission artifacts exist and are verified. Actual submission requires a
human account on each target registry — nothing here can (or should) be done
by an agent.

## What exists already (verified)

| Artifact | Purpose |
|---|---|
| `manifest.json` (repo root) | Single source of truth for registry metadata. Full 37-tool list with JSON inputSchemas, extracted programmatically from `cherenkov/mcp/handlers.py` `TOOLS` (37 tools, verified by `tools/list` smoke test). |
| `mcp.json` (repo root) | Registry-style metadata in the `modelcontextprotocol.io/schema/mcp.json` shape (name, displayName, server command, capabilities, full tool list). |
| `smithery.yaml` | Smithery config: `startCommand: cherenkov mcp serve`, configSchema (`targetUrl`, `specPath`). |
| `pyproject.toml` | Package name `cherenkov-qa` v1.2.0, console script `cherenkov` → `cherenkov.cli.core:main`. |
| `docs/README-MCP-PUBLISH.md` | This document. |

## Pre-flight (single command, run by the human)

```bash
# 1. Confirm the server handshake works end-to-end (stdio, JSON-RPC 2.0):
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"check","version":"0"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | cherenkov mcp serve
# Expect: initialize result with serverInfo.name=cherenkov, capabilities.tools,
# and tools/list returning exactly 37 tools.

# 2. Re-verify the manifest matches the live tool list after any future change:
python - <<'EOF'
import json
from cherenkov.mcp.handlers import TOOLS
m = json.load(open("manifest.json"))
assert [t["name"] for t in m["tools"]] == [t.name for t in TOOLS], "manifest drift!"
print("manifest matches handlers.TOOLS")
EOF
```

Note: `cherenkov mcp serve` is **stdio transport** (newline-delimited JSON-RPC over
stdin/stdout). There is no TCP port to configure; clients spawn the process
(`command: cherenkov`, `args: ["mcp", "serve"]`).

## Where to submit

### 1. Smithery (public, account needed)

- Register/login at <https://smithery.ai/> (human GitHub account).
- The `smithery.yaml` in this repo is the deploy config. Smithery builds and
  runs `cherenkov mcp serve` for you; declare `targetUrl` / `specPath` via the
  `configSchema` when publishing.
- During submission, select: **npm/PyPI-less** → "custom command" style server,
  or point at the pip package `cherenkov-qa` if publishing to PyPI first.
- Validate locally with the Smithery CLI before submitting:
  `npx @smithery/cli validate smithery.yaml`

### 2. CHERENKOV marketplace (self-hosted registry endpoint)

- Endpoint: `POST https://marketplace.cherenkov.dev/api/v1/tools`
  (`cherenkov/mcp/marketplace/registry.py` `DEFAULT_MARKETPLACE_URL`).
- Payload shape (the consumer's `MarketplaceTool` fields, plus the full manifest):
  `{id, name, description, version, repository_url, install_command}` + the
  `tools[]` array from `manifest.json` (or POST `manifest.json` verbatim if the
  endpoint accepts a full manifest).
- `id` (slug) for this server: `cherenkov-core-mcp`
  (`install_command: pip install cherenkov-qa`).
- Requires a human account with publisher rights on marketplace.cherenkov.dev.

### 3. Official MCP registry (future)

- The official registry track (<https://github.com/modelcontextprotocol/registry>)
  accepts submissions via PR to `servers.json`, usually after PyPI packaging and
  a tagged GitHub release (`v1.2.0`). Do this after 1–2 succeed.

## Human checklist

- [ ] GitHub release tagged `v1.2.0` (matches `pyproject.toml` version).
- [ ] Optional: publish `cherenkov-qa` to PyPI (`python -m build && twine upload dist/*`)
      — required for `install_command: pip install cherenkov-qa` to resolve.
- [ ] Docker image published (`cherenkov-mcp:latest`, see `Dockerfile.mcp`)
      for container-based registries (optional).
- [ ] Login to Smithery → validate `smithery.yaml` → submit.
- [ ] Login to marketplace.cherenkov.dev → `POST /api/v1/tools` with
      `manifest.json` (or via the marketplace UI).
- [ ] Update `manifest.json` version + `mcp.json` + `smithery.yaml` on every
      release so they never drift from `pyproject.toml`.

## Environment / auth for consumers

- No auth required by default (`MCPAuthMiddleware(require_auth=False)`).
- If the operator enables auth: set `CHERENKOV_JWT_SECRET` (JWT HS256, issuer
  `cherenkov-mcp`, see `cherenkov/mcp/auth.py`). **Never expose the service with
  the default secret.**
- All tool inputs are validated at the trust boundary
  (`cherenkov/mcp/contracts.py`); `spec_path` and file paths are confined to the
  working directory.

## Troubleshooting

- `cherenkov: command not found` → install package or use
  `python -m cherenkov mcp serve`.
- `tools/list` returns fewer than 37 → tool catalogue drift; re-run the
  validation snippet above and regenerate `manifest.json` from `handlers.TOOLS`.
- Registry rejects `manifest.json` → some registries want a flat
  `{id, name, description, version, repository_url, install_command}` envelope;
  `manifest.json` contains all of those fields plus `tools[]` — submit the
  superset or strip to the required subset per the target API.
