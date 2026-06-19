# CHERENKOV QA — Deferred Vision Archive

**Authority:** v3.1 + delta · **Status:** DEFERRED (Archived Candidates)

This document archives tools and frameworks evaluated for Track B and Track C. None of these tools change our current architecture or step. They are explicitly deferred until **Track A** is shipped and verified by 5 real users (yielding at least 3 "Yes" answers).

---

## 🛠️ Track B/C Candidate Tools (Research, 2026)

The following candidates are mapped to prospective future tracks, to be evaluated **only** after Track A has cleared its validation gate:

### 1. Visual Testing Track (Track B Candidate)
* **Midscene.js + Qwen3-VL**: Vision-based, self-healing UI testing with plain-text intent assertions. This is the credible path if we ever build the E2E/UI Visual Testing track and have sufficient local VRAM/GPU resources.

### 2. Deep Test Generation Track (Track B/C Candidate)
* **Cover-Agent (Qodo)**: Implements the "generate → run → read stack trace → fix → repeat until green" self-healing loop. This is a pattern for deeper test assertion coverage than our current OpenAPI smoke tests, relevant if we implement advanced value-tightening heuristics.

### 3. Context Retrieval & Slicing (Track B/C Candidate)
* **Sweep / Agentless**: Utilizes advanced data-flow tracing to isolate and pull only necessary codebase files into the LLM context. While we currently solve this deterministically with depth-1 spec slicing, their approach is worth comparing in future iterations.

### 4. Performance Testing Track (Track B Candidate)
* **ML Anomaly Detection (Gatling AI pattern)**: Isolation Forest / LSTM baselines. The honest way to evaluate programmatic performance regressions and flaky diagnostic thresholds if the performance track is activated.

---

## 🛑 Worth Knowing (Out of Scope / Not For CHERENKOV)

The following tools have been audited but are explicitly excluded from the product scope:

* **RepoAudit / VulnHuntr / AnyPoC**: Focused on autonomous security vulnerability hunting and PoC generation. This represents the archived CHERENKOV Professional security module (Track C) and is strictly out of scope.
* **Browser-Use / Skyvern**: Autonomous E2E web exploration. These frameworks are extremely heavy and slow (performing an LLM call at every step), making them commercially unviable for local developer smoke validation.
* **Virtuoso / Functionize / Mabl**: Closed-source commercial competitors. Kept solely as product positioning references (what CHERENKOV is *not*), not for adoption.
