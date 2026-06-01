# CHERENKOV — Track B & Track C System Architecture Guide

This guide registers the technical architecture, execution flow, and usage guidelines for the E2E/UI, Visual, Performance, RAG Diagnostics, and MENA Financial Compliance subsystems implemented in Track B and Track C.

---

## 🖥️ Track B — E2E/UI, Visual & Performance Platform

Track B expands CHERENKOV beyond pure API conformance validation into automated UI interactions, layout regression checks, and performance benchmarks.

```
                  ┌───────────────────────────────┐
                  │          UI DISCOVERY         │
                  │ (HTTP Parser / DOM Selector)  │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │      PLAYWRIGHT GENERATION    │
                  │  (LLM Prompt Prefix Cache)    │
                  └───────────────┬───────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│     E2E UI      │      │     VISUAL      │      │   PERFORMANCE   │
│  Locator Fills  │      │  toHaveScreenshot│      │ k6 Script Load  │
│  & Action Clicks│      │  Baseline Diffs │      │  Thresholds     │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

### 1. E2E/UI Test Generator (`stages/ui_plan.py` & `stages/ui_generate.py`)
- **UIPlanStage**: Dynamic HTML/DOM parser utilizing Python's built-in `html.parser` to programmatically extract unique input identifiers (`#email-input`, `#password-input`) and buttons. Formulates structured E2E scenarios.
- **UIGenerateStage**: Byte-identical cache prompt generator feeding the DOM spec to local `qwen2.5-coder:7b`. Automatically injects standard Playwright `expect` assertions via a line-based post-processing healer.

### 2. Visual Baseline Auditor (`execution/visual_diff.py`)
- **System**: Uses Playwright's native `toHaveScreenshot` page snapshot capabilities.
- **Prerequisites**: Captures baselines automatically inside `stub/generated_tests/visual_regression_baseline_ui.spec.ts-snapshots/` on first run via `--update-snapshots` if no snapshot exists.
- **Suggest-Only Sandbox**: Detects layout and rendering regressions, producing high-fidelity visual difference images without auto-committing baseline updates.

### 3. k6 Load Exporter (`execution/k6_runner.py`)
- **System**: Programmatically compiles standard Grafana k6 JavaScript load test scripts defining VUs, durations, and latency thresholds (`p(95) < 500ms`).
- **Resilient Fallback**: If k6 is not installed locally in the path, writes the JavaScript file and outputs clean CLI run instructions rather than throwing execution exceptions.

---

## 🧠 Track C — RAG Learning, AI Diagnostics & MENA Compliance

Track C equips CHERENKOV with cognitive semantic context, root-cause hypotheses, and financial compliance auditing matrices.

### 1. SQLite Vector RAG Index (`ai/rag_index.py`)
- **Database**: Relational SQLite RAG store table (`incident_vectors`) holding historical incident metadata.
- **Vector Embeddings**: Computes 768-dimension semantic embeddings locally via Ollama `nomic-embed-text` with a legacy HTTP `/api/embeddings` fallback.
- **Cosine Similarity**: Calculates dot-products programmatically in Python to score and rank similar past incidents in less than 1ms:
  $$\text{Similarity} = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$$

### 2. AI Root-Cause Diagnostics Stage (`stages/diagnostics_stage.py`)
- **System**: Wires RAG correlation incidents directly into a reliability prompt.
- **LLM Synthesis**: Directs the local `qwen2.5-coder:7b` to synthesize failure class, visual diffs, and contract drifts into a highly structured JSON diagnostics payload containing a definitive root-cause hypothesis and step-by-step resolution actions.

### 3. SAMA CCSF & Egypt CBE Compliance Auditor (`compliance/mena_scanner.py`)
- **Auditing**: Performs static analysis on the OpenAPI contract's `securitySchemes` (Bearer tokens) and active dynamic HTTP scans of gateway headers (`Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`).
- **Monetary Governance Mapping**: Direct-maps technical compliance metrics directly to regional monetary cybersecurity domains:
  - **SAMA CCSF Domain 3.1 & 3.2**: Access Control Policies and Data-in-Transit Protection.
  - **CBE Cyber Security Framework Section 4.2 & 4.5**: Secure Software Development Lifecycle and Boundary Protection.

---

## 🛠️ Verification Execution Commands

CHERENKOV E2E UI, Visual, Performance, and RAG systems are verified in CI using clean integration smoke tests:

```bash
# Verify E2E UI Discovery and TypeScript Code Compilation
python3 smoke_test_ui.py

# Verify Visual Baseline Capture and Comparison
python3 smoke_test_visual.py

# Verify k6 Load Script Exporter
python3 smoke_test_perf.py

# Verify RAG Embedding Indexing and Similarity Retrieval
python3 smoke_test_rag.py

# Verify RAG-augmented AI Root-Cause Synthesis
python3 smoke_test_diagnostics.py

# Verify CBE & SAMA Compliance Scanner Auditing
python3 smoke_test_compliance.py

# Verify Advanced Healing sequence & transient retry checks
python3 smoke_test_healing_advanced.py
```
