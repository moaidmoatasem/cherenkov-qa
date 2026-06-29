---
title: Cost Tiers
description: CHERENKOV-QA runs at zero cost for individuals and small teams. Enterprise tier available for K8s and SSO.
---

# Cost Tiers

CHERENKOV-QA is designed to run at **$0/month** for the vast majority of users.

---

## Tier Overview

| Tier | Setup | Monthly Cost | What You Get |
|------|-------|-------------|--------------|
| **L0 — Bare CLI** | Python + `pip install` | **$0** | Core engine, SQLite, no Docker |
| **L1 — + Ollama** | Ollama installed locally | **$0** | L0 + local LLM, API testing, visual testing |
| **L2 — + Docker** | Docker Desktop/Engine | **$0** | L1 + LocalAI (VLM), Redis (vector/sessions) |
| **L3 — Full Stack** | Android emulator or device | **$0** | L2 + mobile testing, Maestro, desktop app |
| **L4 — + Cloud** | Cloud VM / GPU | ~$50–100 | L3 + cloud VLM/devices, CI scaling |
| **L5 — Enterprise** | K8s cluster | $300+/mo | L4 + K8s operator, SSO, audit logs, compliance |

---

## Tier Details

### L0 — Bare CLI ($0)

The minimum viable setup. Good for evaluating CHERENKOV before committing to Ollama.

```bash
pip install cherenkov-qa

# Uses a lightweight fallback model or requires OPENAI_API_KEY
cherenkov validate --spec api.yaml --target http://localhost:8000
```

**Limitations:** LLM generation requires either Ollama (L1) or a cloud API key (small cost).

---

### L1 — + Ollama ($0)

The recommended default. Everything runs locally with zero ongoing cost.

```bash
# One-time setup
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:8b

# Then use CHERENKOV normally
cherenkov validate --spec api.yaml --target http://localhost:8000
```

**Hardware:** Works on CPU. GPU recommended for speed (not required).

---

### L2 — + Docker ($0)

Adds LocalAI for Vision-Language Model support and Redis for vector similarity search.

```bash
make full   # Starts all services via docker-compose
```

**What Docker adds:**
- `LocalAI` — VLM-powered visual screenshot analysis
- `Redis` — fast vector search for the knowledge mesh
- `Prism` — OpenAPI mock server for dry-run test validation

---

### L3 — Full Stack ($0)

Adds mobile testing (Maestro/ADB) and the Tauri 2 desktop app.

```bash
# Install mobile tools (Linux/macOS)
sudo apt install -y android-tools-adb
curl -Ls https://get.maestro.mobile.dev | bash

# Desktop app (requires Rust/Cargo)
cd desktop
cargo build
```

**Requirement:** Physical Android device or emulator for live mobile test runs.

---

### L4 — + Cloud (~$50–100/month)

For teams that need cloud GPU, remote device farms, or scaling beyond a single machine. Costs depend on provider and usage.

---

### L5 — Enterprise ($300+/month)

For organizations requiring:

- **SAML 2.0 / SSO** (Okta, Azure AD, Google Workspace)
- **K8s Operator** — `ConformanceCheck` CRD for scheduled in-cluster runs
- **SOC2 / GDPR** compliance report generation
- **RBAC** — Admin, Developer, Viewer roles
- **Audit Logging** — append-only JSONL audit trail
- **Multi-tenant org management** with quotas
- **BYO-LLM** — Azure OpenAI and AWS Bedrock adapters

[Contact us for enterprise pricing →](mailto:enterprise@cherenkov.dev){ .md-button }

---

## Solo Developer Zero-Cost Path

If you're a solo developer or on a small team:

```
L0 → L1 → L2 = $0/month, indefinitely
```

No credit card. No account. No data sent anywhere.
