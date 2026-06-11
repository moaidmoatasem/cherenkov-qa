# FrontierCode & Open-Source Alternatives

**FrontierCode** is a proprietary evaluation benchmark created by Cognition AI (makers of Devin). It tests whether AI models can write high-quality, "mergeable" code for production codebases — going beyond functional correctness to assess code quality, scope, and the subjective standard of whether a senior engineer would approve the change.

Because Cognition keeps FrontierCode's tasks closed to prevent AI models from training on the answers, the open-source community has developed its own robust alternatives for both benchmarks (to test models) and autonomous agents (to write the code).

---

## Open-Source Benchmark Alternatives

### DeepSWE (Datacurve)

Released May 2026. Currently the most rigorous open-source answer to FrontierCode.

- Forces agents to make larger, multi-file edits (averaging 5.5× more code than older benchmarks)
- Uses an LLM-based judge to enforce strict correctness
- Explicitly prevents agents from "cheating" by looking up Git histories

### SWE-bench Pro & Verified

The industry-standard open-source benchmark, built by researchers at Princeton and OpenAI.

- Tests agents against thousands of real, historically resolved GitHub issues
- Covers multiple programming languages
- Two tiers: **Verified** (human-confirmed solvability) and **Pro** (harder, curated subset)

### FeatureBench & SWE-Factory

Newer (2026) open-source frameworks that evaluate an agent's ability to build complex, end-to-end features from scratch rather than patching isolated bugs.

---

## Open-Source AI Agents

### OpenHands (formerly OpenDevin)

The most direct open-source response to Devin.

- Operates in a sandboxed Docker environment
- Executes terminal commands, browses the web, and edits code autonomously
- Routinely scores at or above proprietary agents on SWE-bench
- Supports 100+ models, including local models via Ollama

### SWE-agent / mini-SWE-agent

Developed by the creators of SWE-bench at Princeton.

- Lightweight agent framework with a custom Agent-Computer Interface (ACI)
- Optimised for navigating codebases and resolving GitHub issues autonomously
- `mini-SWE-agent` achieves strong benchmark scores with a minimal footprint

### Aider

Terminal-integrated agent heavily optimised for Git workflows.

- Auto-commits changes with descriptive messages
- Works with any LLM backend (local or cloud)
- Strong support for large, multi-file refactors

### Cline

VS Code extension for permission-gated autonomous coding.

- Every shell command and file write requires explicit user approval
- Integrates directly into the IDE editor
- Supports multiple LLM backends

---

## Relevance to CHERENKOV

CHERENKOV is an AI-powered conformance-test generator, not a general-purpose coding agent. It occupies a complementary niche: rather than competing with FrontierCode-style agents on feature implementation, it validates what those agents (and human developers) ship by detecting the gap between an OpenAPI spec and a live server's actual behaviour.

| Tool class | FrontierCode target | CHERENKOV target |
|---|---|---|
| Coding agents (OpenHands, SWE-agent, Aider, Cline) | Write production code | Consumer of test output |
| Benchmarks (DeepSWE, SWE-bench) | Score code quality | Evaluate test completeness |
| **CHERENKOV** | — | Detect spec drift, generate conformance tests |

In practice, CHERENKOV can be used *after* an autonomous agent lands a change: run `cherenkov validate` to confirm the agent's edits did not silently break API contracts.
