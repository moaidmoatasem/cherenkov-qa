# CHERENKOV-QA Assumptions

**Date:** 2026-06-08  
**Status:** Active  
**Related EPIC:** #277 (Phase -1)

---

## Team Assumptions

- **1-2 FTE developers** (solo developer is the primary use case)
- **Part-time contributors** welcome (clean architecture enables <30 min onboarding)
- **No dedicated DevOps** (Docker Compose for local, K8s for production)
- **No dedicated QA** (CHERENKOV is the QA tool)

---

## Hardware Assumptions

- **Target machine**: 16GB+ RAM, GPU optional
- **Development machine**: 8GB+ RAM, no GPU required (L0 mode)
- **CI runners**: GitHub Actions (no GPU, CPU-only)
- **Production**: K8s cluster with GPU nodes (optional)

---

## OS Assumptions

- **Windows primary** (WSL2 for development)
- **macOS follow-on** (native or Docker)
- **Linux follow-on** (native or Docker)
- **Desktop app**: Windows + macOS + Linux (Tauri 2 cross-platform)

---

## Cost Assumptions

- **Solo developer zero-cost path**: Everything local, cloud opt-in only
- **L0-L3**: $0/month (bare CLI → Ollama → Docker Compose → full stack)
- **L4**: $50-100/month (optional cloud VLM, cloud devices)
- **L5**: $300+/month (enterprise: K8s, SSO, audit logs)

### Cost Tiers

| Tier | Setup | Monthly | What You Get |
|------|-------|---------|--------------|
| **L0: Bare CLI** | $0 | $0 | Python + existing Ollama, SQLite only, no Docker |
| **L1: + Ollama** | $0 | $0 | L0 + local LLM, brute-force RAG, API + visual testing |
| **L2: + Docker Compose** | $0 | $0 | L1 + LocalAI (VLM), Redis (vector search, sessions), API + visual + chat |
| **L3: + Full Stack** | $0 | $0 | L2 + Android emulator, Maestro, mobile testing, desktop app |
| **L4: + Cloud** | $0 | $50-100/mo | L3 + optional cloud VLM (GPT-4o-mini), cloud devices (BrowserStack) |
| **L5: + Enterprise** | $0 | $300+/mo | L4 + K8s operator, organization management, SSO, audit logs |

---

## Dependency Assumptions

- **Python 3.10+** (minimum)
- **Node 18+** (for Playwright, openapi-typescript)
- **Docker optional** (L0 mode works without Docker)
- **Ollama optional** (demo mode works without LLM)
- **Redis optional** (SQLite fallback for all stores)
- **GPU optional** (CPU-only mode with pixel_diff_only VLM tier)

---

## All New Dependencies Optional

Every new dependency is behind an extras flag:

```bash
pip install cherenkov-qa              # Core only (L0)
pip install cherenkov-qa[mobile]      # + Maestro, Appium (L3)
pip install cherenkov-qa[redis]       # + Redis adapter (L2)
pip install cherenkov-qa[vlm]         # + LocalAI, VLM models (L2)
pip install cherenkov-qa[all]         # Everything (L3)
```

### `pyproject.toml`

```toml
[project]
name = "cherenkov-qa"
version = "0.1.0"
dependencies = [
    "pydantic>=2.0",
    "fastapi>=0.100",
    "uvicorn>=0.20",
    "requests>=2.28",
]

[project.optional-dependencies]
mobile = [
    "maestro-python>=0.1",
    "Appium-Python-Client>=3.0",
]
redis = [
    "redis>=5.0",
]
vlm = [
    "localai-python>=0.1",
]
all = [
    "cherenkov-qa[mobile,redis,vlm]",
]
```

---

## Performance Assumptions

| Module | Baseline | Notes |
|--------|----------|-------|
| VLM request (LocalAI) | < 10s for 1280×720 PNG | GPU required for <10s |
| VLM request (Ollama) | < 30s for 1280×720 PNG | CPU-only, slower |
| Knowledge query (SQLite) | < 500ms for 1000-record DB | Full-text search |
| Knowledge query (Redis) | < 100ms for 10000-record DB | Vector search |
| Chat response (short) | < 5s first token | LocalAI or Ollama |
| Chat response (tool call) | < 20s completion | Includes tool execution |
| Dashboard API (`/overview`) | < 200ms p95 | SQLite queries |
| Desktop startup (cold) | < 8s to window visible | Tauri 2 + sidecar |
| Desktop startup (warm) | < 2s | Cached sidecar |
| Setup wizard | < 5 min for fresh user | 7 steps |

---

## Security Assumptions

- **Localhost-first**: All services bind to localhost by default
- **No secrets in code**: All secrets via environment variables or `cherenkov.toml`
- **Egress policy**: Respects `egress = "none"` (no outbound network)
- **Input validation**: All API inputs validated and sanitized
- **Rate limiting**: 20 req/min, 100 messages/session
- **Token budget**: Max 4000 tokens per chat message

---

## Scalability Assumptions

- **Single user**: Designed for solo developer (1 user)
- **Multi-user**: Docker Compose supports 5-10 users
- **Enterprise**: K8s operator supports 100+ users (Phase 8)

---

## Testing Assumptions

- **Unit tests**: 500+ tests, >80% coverage
- **Contract tests**: 50+ tests, all adapters pass same tests
- **Integration tests**: 50-100 tests, cross-module integration
- **E2E tests**: 5-10 tests, golden paths only
- **Smoke tests**: 10+ tests, CLI commands work
- **Mobile smoke tests**: 5+ tests, mobile pipeline works

---

## Documentation Assumptions

- **New contributor can add an adapter in <30 minutes** using docs alone
- **All design patterns documented** in PHASE_PLAN.md
- **All ADRs documented** in docs/adr/
- **All vision docs documented** in docs/vision/
- **All engineering docs documented** in docs/engineering/

---

## Validation Assumptions

- **5-QA validation gate**: 5 real QA practitioners test the tool
- **Evidence ledger**: All verdicts recorded in `docs/process/VALIDATION_EVIDENCE_LEDGER.md`
- **Gate passed**: Owner decision (2026-06-08), evidence collection continues

---

## References

- EPIC #277 (Phase -1)
- Issue #299 (Assumptions documentation)
- `docs/PHASE_PLAN.md` (Consolidated plan)
- `docs/TESTING.md` (Testing strategy)
