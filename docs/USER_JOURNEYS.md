# CHERENKOV User Journeys

**Status:** Product journeys and acceptance intent. Not a claim that every step is shipped today.
**Related:** [PLATFORM_OPERATING_MODEL.md](PLATFORM_OPERATING_MODEL.md), [NORTH_STAR.md](NORTH_STAR.md), [ROADMAP_2026H2.md](ROADMAP_2026H2.md)

## Purpose

These journeys make the product legible from a user's point of view. A capability is valuable only when it reduces uncertainty in a real quality decision. The journeys deliberately describe an open platform: tools may vary, but the evidence and human decision model should remain consistent.

## 1. A QA lead connects an unfamiliar repository

**Goal:** Establish an honest starting point in hours, not weeks.

1. The QA lead connects a repository or runs CHERENKOV locally in its root.
2. CHERENKOV discovers relevant artifacts: specifications, test runners, CI configuration, services, recent changes, and existing quality reports.
3. It presents an evidence map that distinguishes observed facts from assumptions and explicitly reports what it could not inspect.
4. The QA lead chooses an initial quality policy and a small, high-value scope—for example, a payment API, checkout journey, or release-critical mobile flow.
5. CHERENKOV proposes a first verification plan. Nothing runs against a target or sends data outside the environment without an approved policy.
6. The lead receives a baseline verdict with coverage, gaps, and recommended next checks.

**Success:** The team knows what has been checked, what has not, and why. A green screen never hides unprobed or unsupported areas.

## 2. An AI coding agent completes a feature

**Goal:** Prevent an agent from declaring success without independent verification.

1. A developer asks Codex, Claude Code, or another agent to implement a feature.
2. The agent changes code and may generate tests using its preferred framework.
3. Before the agent reports completion, it calls CHERENKOV through MCP or CI with the change context, relevant claims, and test artifacts.
4. CHERENKOV derives or retrieves independent checks from the repository's policy, specifications, and accepted knowledge. It records test integrity findings separately from application findings.
5. The result is a verdict: pass with scope, fail with reproducible evidence, or needs human review with the reason.
6. The developer and QA reviewer see the same evidence in the pull request, CLI, or quality console.

**Success:** “Tests pass” is no longer equivalent to “safe to ship.” The team can see what evidence backs the claim.

## 3. A team investigates a release risk across surfaces

**Goal:** Turn scattered signals into one accountable decision.

1. A release changes an API, web workflow, and mobile client.
2. Different executors collect evidence: an API conformance runner, a browser runner, a mobile runner, and a performance runner.
3. CHERENKOV normalizes their results into a single evidence record, retaining each tool's native artifact and limitations.
4. Oracles compare evidence to the applicable policy: specification, user-flow expectation, performance budget, accessibility rule, or approved risk exception.
5. The QA owner reviews conflicts and decides to ship, block, or accept a time-bounded exception.
6. The decision links to the evidence, policy version, responsible reviewer, and follow-up work.

**Success:** The quality decision is explainable even when different tools disagree.

## 4. A team turns an incident into shared intelligence

**Goal:** Ensure painful lessons improve later work without poisoning the knowledge base.

1. A production incident or escaped defect is recorded with its impact and supporting evidence.
2. An agent proposes likely reusable lessons, checks, or risk signals.
3. A designated reviewer approves, edits, rejects, or time-limits each proposed memory item.
4. Approved knowledge becomes available to relevant future plans and agents, with provenance and confidence visible.
5. When the same pattern appears in another repository or pull request, CHERENKOV points to the prior evidence and asks for a fresh verification—not blind reuse.

**Success:** Memory is compounding organizational judgment, not a collection of unverifiable agent notes.

## 5. An engineering leader governs adoption

**Goal:** Scale quality without forcing one runner, model vendor, or workflow on every team.

1. The leader defines organization-wide policy: allowed model providers, data-egress rules, minimum evidence for protected services, and approval boundaries.
2. Teams choose compatible adapters for their context: local models or cloud models; Playwright or Cypress; k6 or another performance executor.
3. CI and MCP integrations enforce the same policy and publish portable results such as JSON, JUnit, or SARIF.
4. The leader sees adoption, recurring risks, and coverage gaps without treating dashboard counts as proof.
5. Teams can eject generated artifacts and replace adapters without losing the historical verdict record.

**Success:** Governance increases trust and reuse without becoming vendor lock-in or a centralized testing bottleneck.

## How these relate to journeys in the product

The five journeys above are personas — how a person's work unfolds. Since 2026-08-06 the word also names a concrete resource: a `JourneyDefinition` (`cherenkov/journeys/`) is a declarative workflow that the engine executes and the dashboard renders from a single definition, served by `GET /api/v1/journeys`. The shipped default, `api-conformance`, is the Generate → Validate → Triage → Knowledge loop.

Two distinctions matter when reading either sense:

- **Auto vs manual steps.** The engine runs the `auto` steps. `manual` steps — triage, knowledge — are a person's work, and the engine never marks them complete. This is the acceptance rule below ("no integration fabricates a passing result") expressed in the data model.
- **Chained journeys** are a third thing again: a multi-step API test that creates a resource and then uses the identifier the server actually returned. They exist because a depth-1 probe cannot honestly reach an item endpoint, and because inferring an identifier instead would manufacture divergences that say nothing about conformance.

## Journey-wide acceptance rules

- Every verdict names its scope, evidence, tool versions, policy, and limitations.
- No integration fabricates a passing result for work it did not execute.
- Unsupported or skipped work is visible; it cannot be rendered as a clean pass.
- Agents cannot lower their own verification requirements or silently promote private memory to team knowledge.
- A human owns policy definition and the final release decision.
- Tests and evidence remain exportable and usable outside CHERENKOV where their native tools allow it.
