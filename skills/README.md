# CHERENKOV Skills

Reusable agent skill files for the CHERENKOV QA platform, following the [vercel-labs/skills](https://github.com/vercel-labs/skills) open agent skills convention.

Each skill lives in its own subdirectory as a `SKILL.md` file with YAML frontmatter. Skills are compatible with the `npx skills` CLI.

## Install via skills CLI

```bash
# Install all cherenkov skills into your agent's skills directory
npx skills add moaidmoatasem/cherenkov-qa

# Install a single skill
npx skills add moaidmoatasem/cherenkov-qa --skill verify
```

## Skills

| Skill | Description |
|-------|-------------|
| [`find-skills`](find-skills/SKILL.md) | Meta-skill: discover which skill to load for any task |
| [`api-test-generation`](api-test-generation/SKILL.md) | Generate Playwright API tests from an OpenAPI spec |
| [`verify`](verify/SKILL.md) | Run conformance verification against a live server |
| [`check-suite`](check-suite/SKILL.md) | Audit test suite quality through the 6-gate pipeline |
| [`certify`](certify/SKILL.md) | Issue a signed conformance certificate |
| [`hitl-review`](hitl-review/SKILL.md) | Manage the Human-In-The-Loop review queue |
| [`self-healing`](self-healing/SKILL.md) | Diagnose failures and suggest fixes (suggest-only) |
| [`eject-standalone`](eject-standalone/SKILL.md) | Export tests to a standalone Playwright suite |
| [`mcp-integration`](mcp-integration/SKILL.md) | Set up the CHERENKOV MCP server |
| [`open-interpreter`](open-interpreter/SKILL.md) | Drive CHERENKOV from Open Interpreter |
| [`k6-perf`](k6-perf/SKILL.md) | K6 load testing via MCP |
| [`perf-baseline`](perf-baseline/SKILL.md) | Track latency baselines and flag regressions |
| [`visual-regression`](visual-regression/SKILL.md) | Pixel-level visual regression testing |
| [`visual-diff`](visual-diff/SKILL.md) | Visual screenshot baselines via MCP |
| [`governance-certification`](governance-certification/SKILL.md) | Governance KPI panel and model certification |
| [`jira-exporter`](jira-exporter/SKILL.md) | Suggest-only Jira export via MCP |
| [`rag-query`](rag-query/SKILL.md) | Query the RAG index for historical context |
| [`mena-compliance`](mena-compliance/SKILL.md) | MENA-region compliance scanning |
| [`ocr-review`](ocr-review/SKILL.md) | Alibaba OCR code review (Gate 7b) |
| [`snyk-remediation`](snyk-remediation/SKILL.md) | Fix Snyk vulnerability findings |
| [`sync-driven-dev`](sync-driven-dev/SKILL.md) | Session sync protocol and token tracking |

## Skill format

Each `SKILL.md` follows the open agent skills specification:

```yaml
---
name: skill-name           # required — unique lowercase identifier
description: >One-liner.   # required — shown in skill discovery
scope: ...                 # cherenkov-specific scope label
invariants: [D7, ...]      # design invariants this skill respects
related_contracts: [...]   # track references
---
```

## Contributing a skill

```bash
npx skills init my-skill-name
# Edit skills/my-skill-name/SKILL.md
```

See [find-skills/SKILL.md](find-skills/SKILL.md) for the discovery index.
