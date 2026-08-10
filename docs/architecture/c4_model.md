# CHERENKOV QA — C4 Architecture Diagrams (Diagrams-as-Code)

This document provides visual models of the **Cherenkov QA** architecture using the **C4 Model** (Context, Container, Component) rendered natively via Mermaid.js syntax.

---

## Level 1: System Context Diagram

The System Context diagram shows Cherenkov QA in relation to external users, target APIs, AI models, and CI/CD pipelines.

```mermaid
C4Context
    title System Context Diagram for Cherenkov QA
    
    Person(dev, "Developer / QA Engineer", "Writes specs, triggers validations, reviews test reports.")
    Person(agent, "AI Coding Agent", "Interacts via MCP, reads AGENTS.md / llms.txt.")

    System(cherenkov, "Cherenkov QA", "Autonomous Quality Engineering fabric for API spec validation & drift detection.")

    System_Ext(targetApi, "Target API Service", "REST, GraphQL, gRPC, or AsyncAPI endpoints being validated.")
    System_Ext(localAi, "LocalAI / Ollama / LLM", "Serves VLM & SLM models for test synthesis and semantic judging.")
    System_Ext(cicd, "CI/CD Pipeline", "GitHub Actions, GitLab CI, or Jenkins running continuous validation.")

    Rel(dev, cherenkov, "Uses CLI / Web Dashboard")
    Rel(agent, cherenkov, "Calls MCP Tools / Reads context")
    Rel(cicd, cherenkov, "Executes cherenkov validate / guardian")
    Rel(cherenkov, targetApi, "Sends HTTP/gRPC validation probes")
    Rel(cherenkov, localAi, "Generates & verifies test payloads")
```

---

## Level 2: Container Diagram

The Container diagram breaks down Cherenkov QA into its high-level runnable units and storage components.

```mermaid
C4Container
    title Container Diagram for Cherenkov QA

    Container(cli, "CLI Application", "Python / Click", "Command line interface for validation, training, and guardian daemons.")
    Container(web, "Web Dashboard", "FastAPI / Jinja2 / CSS", "Browser dashboard for telemetry, device monitoring, and chat agents.")
    Container(daemon, "Spec Guardian Daemon", "Python Threading", "Background process monitoring live API spec drift with hot-reload.")
    Container(mcp, "MCP Server Mesh", "JSON-RPC 2.0", "Exposes Cherenkov capabilities as MCP tools to AI assistants.")

    ContainerDb(sqlite, "SQLite Storage", "WAL mode", "Stores drift events, telemetry runs, training data, and audit logs.")
    ContainerDb(marketplace, "Local Marketplace Store", "File System", "Stores custom test templates and MCP tool manifests (~/.cherenkov/marketplace/).")

    Rel(cli, sqlite, "Reads/Writes telemetry & reports")
    Rel(daemon, sqlite, "Persists drift events & trends")
    Rel(web, sqlite, "Renders analytics & charts")
    Rel(mcp, cli, "Invokes engine logic")
    Rel(cli, marketplace, "Publishes & installs templates")
```

---

## Level 3: Component Diagram (Core Validation Engine)

The Component diagram shows the internal structure of the core validation engine.

```mermaid
C4Component
    title Component Diagram for Core Validation Engine

    Component(orchestrator, "OrchestrationEngine", "core/orchestrator.py", "Coordinates stage execution and state flow.")
    Component(specValidator, "SpecValidator", "spec_guardian/detector.py", "Checks HTTP status codes and schema conformance against OpenAPI/AsyncAPI.")
    Component(driftLoop, "DriftLoop", "drift/loop.py", "Maker/checker autonomy gate (L1 report, L2 proposal, L3 auto-reconcile).")
    Component(identityPort, "IdentityProvider Port", "domain/ports/identity.py", "Clean Architecture port for authentication & SAML SSO.")
    Component(trainerRunner, "TrainingRunner", "training/runner.py", "Orchestrates SLM fine-tuning across DryRun and HuggingFace backends.")

    Rel(orchestrator, specValidator, "Delegates schema checks")
    Rel(orchestrator, driftLoop, "Evaluates drift proposals")
    Rel(orchestrator, identityPort, "Verifies auth tokens & SAML assertions")
    Rel(orchestrator, trainerRunner, "Exports telemetry for model training")
```
