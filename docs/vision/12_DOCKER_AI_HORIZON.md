# CHERENKOV — Horizon 3: Docker AI Platform Integration

**Status:** Strategic proposal · **Date:** 2026-06-07 · **Parent:** Horizon V (ROADMAP_NEXT.md)
**Predecessor:** [`10_HORIZON_2.md`](10_HORIZON_2.md) (Adoption, Voice & Prove-in-the-Wild)
**See also:** [`00_VISION.md`](00_VISION.md) (north-star), [`01_ARCHITECTURE.md`](01_ARCHITECTURE.md) (layers), [`07_MASTER_PLAN.md`](07_MASTER_PLAN.md) (E7-E13)

---

## 1. Thesis

Docker is building the **Agentic AI Platform** — a unified layer for building, running, and securing AI agents. CHERENKOV is a **truth-maintaining system** that detects divergence between sources of truth. These two missions converge:

> Docker standardizes **how agents connect and act**. CHERENKOV standardizes **what agents verify and prove**.

Integrating Docker AI capabilities into CHERENKOV transforms it from a local CLI tool into a **first-class citizen of the agentic ecosystem** — deployable, governable, and verifiable at scale.

---

## 2. The Docker AI Surface (what's relevant)

| Docker Capability | What It Does | CHERENKOV Hook |
|---|---|---|
| **MCP Gateway + Catalog** | 200+ curated MCP servers; unified gateway endpoint | Already integrated (full-dev profile). Gateway exposes cherenkov's tools to any MCP client. |
| **Docker Sandboxes (E2B)** | Cloud-isolated sandboxes for safe agent code execution | Replace filesystem `sandbox_healer.py` with true container-boundary isolation. D7 becomes platform-enforced, not convention. |
| **AI Governance** | Central policy: tool allowlists, network rules, credential scoping | Enforce D7 (suggest-only) + anti-lock-in + egress dial as Docker policy. Govern which MCP tools each agent profile can use. |
| **Docker Model Runner** | Local-first LLM as OCI containers, portable across environments | Alternative to Ollama for CHERENKOV's substrate router. Model as container = push/pull/version like any dependency. |
| **Docker Offload** | Cloud GPU without infrastructure | CI validate/heal runs with cloud GPU — no self-hosted runners. Unblocks opt-in GPU gate in CI. |
| **Docker Hub MCP Server** | Manage images, repos, tags via MCP | CI publishes CHERENKOV images; agents inspect/rollback versions. |
| **Gordon (Docker AI)** | Docker's built-in AI assistant | Lower barrier: "Gordon, run cherenkov validate on this API" from the IDE. |
| **Docker Compose for agents** | Deploy agents as Compose services | Scale CHERENKOV agents (explorer, healer, daemon) as Compose replicas. |

---

## 3. Integration Layers (mapped to CHERENKOV architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                  DOCKER AI GOVERNANCE                        │
│  (D7 policy · tool allowlists · network rules · credentials) │
├─────────────────────────────────────────────────────────────┤
│                  DOCKER MCP GATEWAY                          │
│  (unified endpoint · 200+ tools · tool allowlisting)         │
├─────────┬──────────┬──────────┬──────────┬──────────────────┤
│ cherenkov│ context7 │sequential│ github   │ atlassian        │
│ (HITL,   │ (docs)   │(thinking)│ (PRs,    │ (Jira,           │
│ validate) │          │          │  issues) │  Confluence)     │
├─────────┴──────────┴──────────┴──────────┴──────────────────┤
│                  DOCKER SANDBOXES (E2B)                      │
│  (isolated agent execution · cloud-scale)                    │
├─────────────────────────────────────────────────────────────┤
│                  DOCKER MODEL RUNNER / OFFLOAD               │
│  (LLM inference · cloud GPU)                                 │
├─────────────────────────────────────────────────────────────┤
│                  CHERENKOV ENGINE (existing)                 │
│  (substrate router · divergence engine · HITL · heal)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Phased Rollout

### Phase A — Foundation (already done)

**Cost:** $0 (Docker Desktop 4.74.0 already installed)

- [x] Docker MCP Gateway connected to all IDEs (opencode, cursor, vscode, claude-code)
- [x] `full-dev` profile: cherenkov + context7 + sequentialthinking + github-official + atlassian-remote
- [x] `Dockerfile.mcp` — slim MCP server image
- [x] `cherenkov-mcp.yaml` — server entry spec
- [x] MCP configs committed to repo (`.mcp.json`, `.cursor/`, `.vscode/`)

### Phase B — Sandbox-Heal Convergence

**Target:** Replace filesystem sandbox with Docker E2B cloud sandboxes

| Task | What | Effort | D7 Impact |
|------|------|--------|-----------|
| B1 | Add `docker-sandbox` provider to `sandbox_healer.py` | M | D7 becomes platform-enforced (container cannot write host) |
| B2 | Wire E2B SDK for cloud sandbox orchestration | M | Sandbox lifecycle managed by Docker, not local FS |
| B3 | Keep filesystem fallback for offline/dev mode | S | Zero-egress mode preserved (anti-lock-in) |
| B4 | Smoke test: sandbox repair in E2B vs filesystem | S | Evidence parity across providers |

**Architecture:**

```python
# Current (filesystem):
sandbox_path = f"sandbox_{run_id}_{scenario_id}"  # local dir

# Future (Docker Sandbox):
sandbox = DockerSandbox(image="cherenkov-heal:latest")
sandbox.exec("playwright test --reporter=json")
diff = sandbox.read_file("healed_diffs/report.json")
sandbox.destroy()  # container removed, no host contamination
```

**Exit criteria:** `smoke_test_deep_healing.py` runs identically against both `provider: filesystem` and `provider: docker-sandbox`.

### Phase C — Governance Layer

**Target:** Codify CHERENKOV's design invariants as Docker AI Governance policy

| Task | What | Effort | Invariant |
|------|------|--------|-----------|
| C1 | Define `cherenkov-policy.json` — tool allowlists per profile | S | D7 (suggest-only) |
| C2 | Gate heal suggestions through governance: `allow_tool: [hitl_list, hitl_approve, ...]` | M | D7 + anti-lock-in |
| C3 | Network policy: `egress: none` blocks MCP servers with external endpoints | S | Sovereignty |
| C4 | Credential scoping: per-server secrets, not env-var-wide | S | Security |

**Policy document example:**

```json
{
  "profile": "full-dev",
  "servers": {
    "cherenkov": { "tools": ["hitl_list", "hitl_approve", "hitl_reject", "validate_run_gate"] },
    "github-official": { "tools": ["list_issues", "search_code", "get_file_contents"], "network": "api.github.com:443" }
  },
  "invariants": {
    "d7_suggest_only": true,
    "anti_lock_in": true,
    "spec_derived_status": true
  }
}
```

### Phase D — Model Runner & Offload

**Target:** Portable LLM inference via Docker Model Runner; cloud GPU via Docker Offload

| Task | What | Effort | Benefit |
|------|------|--------|---------|
| D1 | Test `docker model run` as alternative substrate | M | OCI-portable models, no Ollama dependency |
| D2 | Add `provider: docker-model-runner` to substrate router config | M | Swap inference backend per environment |
| D3 | CI: use Docker Offload for GPU validate/heal jobs | L | Remove "opt-in" gate; LLM-powered validation runs standard |
| D4 | Document: "choose your inference" matrix (ollama / model-runner / openai) | S | Anti-lock-in proven in docs |

### Phase E — Docker Hub MCP + Compose Agents

**Target:** Agentic deployment; CHERENKOV agents as Compose services

| Task | What | Effort | Strategic |
|------|------|--------|-----------|
| E1 | Add Docker Hub MCP server to `full-dev` profile | S | Agents manage images via MCP tools |
| E2 | CI: publish CHERENKOV image to Docker Hub on green main | M | Public availability, install via `docker pull` |
| E3 | Compose agent profile: deploy explorer+healer+daemon as replicas | L | Horizontal scaling, true agent fabric |
| E4 | `docker compose --profile agents up` — one-command multi-agent deploy | M | "Make it boring" (Horizon 2 Bet 3) |

---

## 5. Design Invariants (unmodified from core)

| Invariant | Docker Integration Impact |
|-----------|--------------------------|
| **D7 — Never auto-edit test code** | Sandboxes + Governance enforce this at infrastructure level. Heal suggestions remain suggest-only. |
| **Anti-lock-in** | All Docker integrations have a non-Docker fallback. Filesystem sandbox, direct stdio MCP, direct Ollama all preserved. |
| **Suggest-only healing** | E2B sandbox makes it *physically impossible* for heal output to modify the host. Stronger than convention. |
| **Spec-derived status** | Unchanged. Docker integrations don't touch the divergence or truth model. |
| **MCP peers as untrusted** | Docker Sandbox + Governance add platform-level enforcement on top of Pydantic validation. |
| **Egress sovereignty** | Governance policy codifies `egress: none` as network rules on MCP servers and sandboxes. |

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Docker Sandboxes (E2B) requires paid Docker subscription | High | Medium | Filesystem fallback preserved; open-source E2B SDK also available |
| Docker AI Governance is new/immature | Medium | Medium | Lock feature behind `cherenkov.toml` opt-in; default behavior unchanged |
| Docker Offload pricing unclear | Medium | Low | CI GPU remains opt-in; Offload is additive, not replacement |
| Model Runner doesn't support all models | Medium | Low | Substrate router already supports multiple providers; Model Runner is one option |
| Docker Desktop dependency on Windows | High (team may use Linux) | Low | All integrations work with Docker Engine on Linux; Desktop-only features (OAuth store) have CLI equivalents |

---

## 7. Summary: Docker + CHERENKOV = Trusted AI QA

| Before | After |
|--------|-------|
| Sandbox healer on local filesystem | Sandbox healer in Docker E2B cloud sandbox |
| D7 enforced by convention | D7 enforced by platform (Governance + Sandbox) |
| One inference provider (Ollama) | Swappable: Ollama / Model Runner / cloud API |
| CI GPU optional, self-hosted | CI GPU via Docker Offload, on-demand |
| MCP config per-IDE, manual | MCP config committed, gated by profile |
| Agent fabric proto (`.agents/`) | Agents as Compose services, scalable |

**The bottom line:** Docker's AI platform turns CHERENKOV's design invariants from **code conventions** into **infrastructure guarantees** — and makes the whole system deployable, governable, and verifiable at a scale no standalone CLI tool can reach.
