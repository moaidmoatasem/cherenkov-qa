# Competitive Positioning vs. North Stars (TestSprite, Momentic, Vibium, MCP ecosystem, CLIs) — 2026-08-01

## Provenance

This note synthesizes ~10 external LLM-generated competitive assessments pasted into a session by the maintainer, comparing CHERENKOV-QA to TestSprite, Momentic.ai, Vibium, the MCP ecosystem, and general CLI testing tools. **Those reports were produced by tools with no access to this repository** — several explicitly say the GitHub repo "cannot be fetched" and then invent plausible-sounding specifics (star counts, issue counts, funding figures) to fill the gap. Do not cite their numbers. What follows is the structural signal that was *consistent across all ~10 independent reports*, checked against what's actually true in this codebase as of `main`.

## What's actually true here (verified, not guessed)

- **There is a real MCP server**: `cherenkov/mcp/{server.py,protocol.py,handlers.py,auth.py,mesh_router.py,policy.py}` plus `cherenkov/mcp/tools/{sentinel.py,teleport.py}`. Several of the pasted reports claim "CHERENKOV has no MCP server" — that's false. What's unverified is *depth*: how many tools it exposes, whether it's wired into `smithery.yaml`/registry publishing (tracked, still open: issue #792), and whether an external agent (Claude Code, Cursor) can actually drive `check-suite`/`verify` through it today. That's the real open question, not existence.
- **The core "integrity auditor" claim is real**, per the 2026-08-01 GraphQL/gRPC/Enterprise/SpecGuardian triage (see `CHANGELOG.md` "Corrected" entry under 1.2.0): AST-based test auditing, mutant-battery synthesis, and spec-derived expected values are implemented, not vaporware.
- **The "Phase 11-16 fully implemented" claim the reports partly relied on was false** and has been corrected in `CHANGELOG.md` and the GitHub issue tracker (see the 2026-08-01 issue triage — 18 issues closed as genuinely done, 14 annotated as partial/unwired, ~23 left open as not started).

## The consistent signal across the external reports (worth acting on)

1. **CHERENKOV is not a competitor to Momentic/TestSprite/Vibium — it's a complementary layer.** They generate/execute E2E or UI flows; CHERENKOV proves the *API contract* those flows depend on hasn't silently drifted. Every report converged on this independently — it's a safe positioning bet, not a hunch.
2. **The distinguishing feature — auditing existing tests for weakened/deleted/hallucinated assertions against a spec — has no direct equivalent** in Schemathesis, Pact, Dredd, Postman, or any of the named north stars. This is the thing worth protecting and marketing, not the K8s operator or the desktop app.
3. **MCP depth, not MCP existence, is the gap.** The actionable next step is exposing `check-suite` / `verify` / `generate` as callable MCP tools an agent invokes mid-session (e.g., "I just changed this endpoint, did I weaken any assertions?") — not building a new server from scratch.
4. **Scope discipline was flagged independently by nearly every report**: K8s operator, mobile testing, desktop app, marketplace/webhook/analytics (Phase 16) all shipped or half-shipped ahead of any external adoption signal. This matches the 2026-08-01 issue triage finding that Phase 15/16 is mostly stub/simulated code. Recommendation converges with the repo's own `docs/ROADMAP_2026H2.md`: stop opening new phases, finish wiring what already has real logic behind it (SAML/RBAC/GDPR CLI wiring, Spec Guardian daemon entrypoint — see open issues #755, #757, #759, #765).

## What NOT to act on from the pasted reports

- Specific star/fork/funding/user counts — unverifiable from this environment and inconsistent across the ten reports themselves (one says "37 open issues," the real count checked via the GitHub API was 55).
- Anything premised on "the docs site returns 404" or "CLI reference page is broken" — checked directly in this session: `mkdocs build --strict` passes clean, no broken links. If this is still visibly broken on the live gh-pages site, it's a *deploy* problem (see the release/tag reconciliation below), not a content problem.

## Concrete next step if picked up

Deepen `cherenkov/mcp/server.py`'s tool surface (`check-suite`, `verify`, `generate` as directly invokable MCP tools) and register the server per issue #792 (MCP registry publish) — this is the single highest-leverage item every external report converged on, and it's additive to existing code rather than a new subsystem.
