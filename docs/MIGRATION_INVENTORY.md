# CHERENKOV Legacy Migration Inventory

This inventory registers every module of the legacy repository `cherenkov-professional` and tags it with its architectural destination for the new clean QA testing repository.

## Tagging Rubric
* **REUSE**: Proven utility/infrastructure code copied into the `legacy/` folder (trimmed).
* **REFERENCE**: Clean design patterns to guide fresh implementations in new core package.
* **ARCHIVE**: Security business logic modules (scanners, compliance checkers) left untouched.
* **DROP**: Dead, experimental, or crew-related swarm logic.

---

## Migration Catalog

| Legacy Module Path | Classification | Context / Migration Target |
| :--- | :--- | :--- |
| **`cherenkov/core/exceptions.py`** | **REFERENCE** | Custom typed exceptions are now cleanly handled by `cherenkov/core/errors.py`. |
| **`cherenkov/core/circuit_breaker.py`** | **REFERENCE** | Conceptual model for circuit breaker. Rewritten inside new orchestrator without old base scanner dependencies. |
| **`cherenkov/core/tokamak_logger.py`** | **REFERENCE** | Structured logger. Replaced by clean `StructuredLogger` emitting JSONL to stderr. |
| **`cherenkov/core/base_scanner.py`** | **ARCHIVE** | Security core scanning class. Left untouched in legacy ref. |
| **`cherenkov/core/hybrid_orchestrator.py`** | **REFERENCE** | Multi-agent execution model. We reimplement a dedicated QA DAG orchestrator instead. |
| **`cherenkov/ai/lattice.py`** | **REFERENCE** | Legacy model connection client. Replaced by `cherenkov/ai/ollama_client.py` using `format="json"`. |
| **`cherenkov/ai/model_selector.py`** | **REFERENCE** | Dynamic model selection. In Week 0/1, we explicitly anchor to Ollama `qwen2.5-coder:7b`. |
| **`cherenkov/scanners/`** (all scanners) | **ARCHIVE** | SQL injection, SSRF, XSS, iOS, Android, static XXE, network, Severe severities. Left untouched. |
| **`cherenkov/compliance/`** (all frameworks) | **ARCHIVE** | SAMA CCSF, DORA, Egypt FinCSF, PDF rendering. Out of scope for QA test suite validator. Left untouched. |
| **`cherenkov/api/main.py`** | **REFERENCE** | Clean patterns for FastAPI backend. Will guide Dashboard backend implementation in Week 12. |
| **`cherenkov/crews/`** (Swarm crews) | **DROP** | CrewAI Autonomous developer team, swarms, newsletters, etc. Dropped. |
| **`cherenkov/tools/`** | **DROP** | Out-of-scope auxiliary tools. Dropped. |

---

## 🛡️ Migration Tripwire Enforced

> [!IMPORTANT]
> **No imports from legacy ref**: No file inside `cherenkov/core/`, `cherenkov/ai/`, or `cherenkov/stages/` is permitted to import anything from `/home/moaid/_cherenkov-legacy-ref` or `legacy/`. The legacy abstractions are entirely isolated to prevent security-business-logic bleed.
