---
name: find-skills
description: "Helps agents discover and load the right CHERENKOV skill for any task — API testing, HITL review, MCP setup, certification, and more."
scope: Meta
invariants: []
---

# Find Skills

## Purpose
This meta-skill helps you (or an AI agent) find the right CHERENKOV skill for a task. When someone asks "how do I generate tests?", "what skill handles performance?", or "is there a skill for Jira?", consult this index first.

## Skill Index

| Task | Skill | Key command |
|------|-------|-------------|
| Generate API tests from an OpenAPI spec | `api-test-generation` | `cherenkov generate` |
| Verify tests against a live server | `verify` | `cherenkov verify` |
| Audit test suite quality (6 gates) | `check-suite` | `cherenkov check-suite` |
| Issue a signed conformance certificate | `certify` | `cherenkov certify` |
| Review uncertain tests with a human | `hitl-review` | `cherenkov hitl list` |
| Self-heal failing tests (suggest-only) | `self-healing` | `cherenkov heal` |
| Export ejected tests to a standalone repo | `eject-standalone` | `cherenkov eject` |
| Set up CHERENKOV MCP server | `mcp-integration` | `cherenkov mcp serve` |
| Drive CHERENKOV from Open Interpreter | `open-interpreter` | `bash scripts/setup_oi.sh` |
| K6 load testing via MCP | `k6-perf` | MCP `run_k6_perf` |
| Performance baseline + regression tracking | `perf-baseline` | `cherenkov perf` |
| Visual screenshot regression | `visual-regression` | `cherenkov visual` |
| Visual diff baselines via MCP | `visual-diff` | MCP `visual_diff_baseline` |
| Governance KPI panel + model certification | `governance-certification` | `cherenkov governance` |
| Export to Jira (suggest-only) | `jira-exporter` | MCP `export_jira_ticket` |
| Query RAG index for historical context | `rag-query` | MCP `query_rag_index` |
| MENA compliance scan | `mena-compliance` | MCP `scan_mena_compliance` |
| Alibaba OCR code review (Gate 7b) | `ocr-review` | `cherenkov ocr review` |
| Fix Snyk vulnerabilities (app code) | `snyk-remediation` | reads `agent_memory/snyk-findings.md` |
| Session sync + token tracking | `sync-driven-dev` | `python scripts/agent_sync.py before` |

## How to load a skill

In Claude Code, skills live at `skills/<name>/SKILL.md`. Load one by reading the file before starting the task:

```bash
# Claude Code reads this automatically when you invoke the /skill-name command
# Or explicitly: Read skills/verify/SKILL.md
```

Via the skills CLI (compatible with vercel-labs/skills format):

```bash
# Install all cherenkov skills into your agent's skills directory
npx skills add moaidmoatasem/cherenkov-qa

# Or install a single skill
npx skills add moaidmoatasem/cherenkov-qa --skill verify
```

## Discovery tips

- **"I want to generate tests"** → `api-test-generation`
- **"I want to check conformance"** → `verify`
- **"I want to certify an API"** → `certify`
- **"Something is failing"** → `self-healing`
- **"I use Claude Desktop / Cursor / Open Interpreter"** → `mcp-integration`
- **"I want to export to Jira"** → `jira-exporter`
- **"I need to fix a security issue"** → `snyk-remediation`
- **"I want to track performance"** → `perf-baseline` or `k6-perf`
- **"I want visual regression"** → `visual-regression`

## References
- `skills/` — all skill files in this directory
- `CLAUDE.md` — project norms and entry points
- `HANDOVER.md` — current gate/phase status (always check this first)
