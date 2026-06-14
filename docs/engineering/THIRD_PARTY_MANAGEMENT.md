# Third-Party Management Strategy

This document outlines the standard operating procedure for managing third-party libraries and integrated external services within the CHERENKOV QA project. It enforces the **Clean Architecture (Ports & Adapters)** boundaries specified in [ADR-004: Clean Architecture](../adr/ADR-004-clean-architecture.md).

## 1. Automated Dependency Updates (Libraries)

To keep all utilized libraries (Python, Node, Rust) and ecosystems (Docker, GitHub Actions) continuously updated and secure, the project relies on **GitHub Dependabot**.

* **Configuration:** Dependabot is configured in `.github/dependabot.yml`.
* **Schedule:** Updates are checked on a **weekly** schedule.
* **Process:** Dependabot will automatically open Pull Requests titled with `chore(deps)` when updates are available. These PRs run against the CI pipeline (`ci.yml`) and must pass all behavior and unit tests before merging.

## 2. Integrated 3rd Parties (External Services & Models)

CHERENKOV QA integrates with multiple external third parties, including but not limited to:
- LocalAI / Ollama (Local Models)
- External LLM APIs (OpenAI, Anthropic)
- Prism (Mock Servers)
- Redis / In-memory caches

### The "Adapter" Rule

All third-party services MUST be isolated behind a **Port (Interface)** and implemented via an **Adapter**.
* **Never** leak a third-party SDK (e.g., `openai` package or `redis` client) into the core `use_cases` or `domain` layers.
* The domain defines what it needs (the Port). The infrastructure layer implements it (the Adapter).
* This ensures that swapping one third-party service for another (e.g., moving from Redis to an in-memory queue) requires exactly zero changes to the core logic.

### Fallbacks and Circuit Breakers

External services are inherently unreliable. When managing integrated third parties:
1. **Graceful Degradation:** Use the `DependencyStatus` and `CircuitBreaker` patterns (referenced in `docs/ERROR_HANDLING.md`).
2. **Health Checks:** If an integrated service goes down, the application state should move to `degraded` and fall back to local or alternative workflows if possible, rather than crashing entirely.
3. **No Hard Dependencies:** Avoid making external services hard blockers unless absolutely critical to the execution path (e.g., golden path AI generation). For everything else, treat external services as optional enhancements.

## 3. Autonomous End-Of-Life (EOL) Mitigation

When a third-party library or service reaches End-Of-Life (EOL), simple version bumps via Dependabot are often insufficient. CHERENKOV QA handles EOL components autonomously:
1. **Weekly EOL Scanning:** A GitHub Action (`agent-eol-scanner.yml`) runs weekly to scan for deprecated/EOL components using tools like `pip-audit` and `npm audit`.
2. **Agentic Healing:** If an EOL component is found, the scanner triggers an autonomous agent. The agent forks a branch, rewrites the affected Adapter to use a modern alternative, validates the test suite, and opens a Pull Request.

By adhering to this strategy and leveraging Dependabot alongside AI maintenance agents, the project maintains a strict security posture and autonomous architectural flexibility regarding all external tools and libraries.
