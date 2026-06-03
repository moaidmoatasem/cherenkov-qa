# FAQ

**What is CHERENKOV?** A model-agnostic engine that finds where a system's sources of truth disagree, proves it by reproduction, and emits the closing artifact. Track A: OpenAPI → Playwright conformance tests, zero lock-in.

**Is it shipped?** Built, not shipped. Gated by the 5-QA validation gate ([#79](https://github.com/moaidmoatasem/cherenkov-qa/issues/79)).

**Why "model-agnostic"?** Agents never name a model; they emit a `ReasoningRequest{capability_tier}` routed by the Substrate Router. Swap models via config (`cherenkov.toml`), never code.

**What's quarantined?** `track-b-c-deferred/` (visual, perf, RAG, compliance, jira, dashboard). Reference-only until the gate passes.

**Can it run fully local / sovereign?** Yes — `egress: none` keeps everything on local models.

**Where do I start contributing?** [Way of Work](Way-of-Work) → pick a `status:ready` issue → branch → PR with evidence.

**Does eject lock me in?** No. `eject` produces standalone Playwright that runs with zero `cherenkov` on the path (a hard invariant).
