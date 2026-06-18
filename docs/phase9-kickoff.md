# Phase 9 — Market Launch Kickoff Suggestions

**Goal:** Landing page, `npx cherenkov init` flow, Product Hunt prep.

## Assets already in place

- CLI with `cherenkov init` command (zero-config setup) — `cherenkov/cli/commands/simple.py`
- `docs/GETTING_STARTED.md` — quickstart guide
- `docs/QA_DEMO_KIT.md` — demo kit for practitioners
- `docs/CLI_DEMO.md` — CLI walkthrough
- Docker compose files for AI stack (`docker-compose.ai.yml`)
- Eject produces standalone Playwright — there IS zero lock-in

## Gaps to close

### 1. Landing page
- No static site / GitHub Pages site exists
- Options: `mkdocs` on GitHub Pages (low effort), or a standalone landing page in `site/`
- `pages.yml` workflow exists but generates nothing

### 2. `npx cherenkov init`
- `cherenkov init` exists as a Click command
- Needs verification that it works end-to-end: `npx cherenkov` → `init` → prompts → ready-to-run project
- No npm package published for it (only `packages/mcp-server` is published)

### 3. Product Hunt / social proof
- Collect 3 case studies from the G0 E0.1 divergences (Petstore, HTTPBin, GitHub)
- One-liner: *"API conformance test generator — spec in, Playwright tests out, zero lock-in."*
- Tagline from HANDOVER.md already exists and is proven

### 4. Quick wins
- Fix `npm-publish.yml` to publish the main package, not just `packages/mcp-server`
- Add `pip install cherenkov-qa` flow (needs `pyproject.toml` build config)
- Verify `cherenkov init` produces a working project in <60 seconds
