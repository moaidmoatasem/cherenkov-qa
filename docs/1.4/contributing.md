---
title: Contributing to the Docs
description: How to update the CHERENKOV-QA public documentation — the SSOT rule, audience separation, and the contribution workflow.
---

# Contributing to the Documentation

Thank you for improving the CHERENKOV-QA docs. This guide explains the **one rule** that governs all doc changes and the workflow to follow it.

---

## The SSOT Rule

CHERENKOV-QA has two documentation areas with strictly different purposes:

| Area | Path | Audience | Purpose |
|------|------|---------|---------|
| **Internal SSOT** | `docs/` | Agents, developers, CI | Agent handover, architecture decisions, phase plans |
| **Public Docs** | `docs-site/docs/` | End users, developers, OSS community | How to install, use, and integrate CHERENKOV |

**The rule:**
- **Never publish `docs/` content directly** — it contains internal agent instructions, handover state, fabricated-doc warnings, and operational data that should never be public.
- **`docs-site/docs/` is the public source** — all public docs go here, even if they're derived from `docs/`.
- **When you update internal SSOT, update the public doc too.** The dual-source relationship is a feature, not a bug. Public docs are *curated* views of internal docs, not copies.

---

## What Belongs Where

### ✅ Goes in `docs-site/docs/` (public)

- User-facing guides (installation, quickstart, tutorials)
- CLI reference
- Architecture diagrams
- Release notes and changelog
- Integration guides

### ❌ Never goes in `docs-site/docs/` (internal only)

- `HANDOVER.md` — agent handover notes
- `PHASE_PLAN.md` — internal delivery phases
- `AGENTS.md` — agent operating rules
- Strategy docs (`PRODUCT_STRATEGY_ROADMAP.md`, etc.)
- ADRs that contain internal debates or cancelled proposals
- Any file containing "Phase N", "Track A/B/C", "CC-N" references (these are internal)

---

## Updating Public Docs

### When You Update an Internal SSOT Doc

1. Make your internal doc change in `docs/`
2. Check if any public doc page in `docs-site/docs/` derives from that file
3. If yes: update the corresponding public page to reflect the change
4. Run the sanitizer to verify no internal tokens leaked:
   ```bash
   make docs-check-clean
   ```

### When You Add a New Public Page

1. Create the file in `docs-site/docs/<section>/your-page.md`
2. Add it to `nav:` in `docs-site/mkdocs.yml`
3. Run `make docs-build` to validate
4. Run `make docs-check-clean` to verify no internal tokens
5. Open a PR against `main` — the CI will validate both

---

## Local Preview

```bash
# Install docs dependencies (one-time)
pip install -r docs-site/docs-requirements.txt

# Start the live-reload preview server
make docs-serve
# Opens at http://localhost:8000

# Build (strict mode — catches broken links)
make docs-build

# Lint markdown
make docs-lint

# Check for leaked internal tokens
make docs-check-clean
```

---

## CI Checks (What Runs on Every PR)

| Check | What It Does | Fail Action |
|-------|-------------|-------------|
| `mkdocs build --strict` | Validates all pages render, no broken internal links | Block merge |
| `check_public_docs_clean.py` | Greps for leaked internal SSOT tokens | Block merge |
| `pymarkdownlnt` | Markdown linting | Advisory (non-blocking) |

---

## Page Ownership

Each page in `docs-site/docs/` has a corresponding internal source:

| Public Page | Internal Source | Notes |
|-------------|-----------------|-------|
| `getting-started/installation.md` | `docs/GETTING_STARTED.md` | Curated — internal setup details stripped |
| `getting-started/quickstart.md` | `docs/QUICKSTART_PETSTORE.md` | Curated |
| `cli/reference.md` | `cherenkov --help` | **Auto-generated** — do not edit manually |
| `architecture/diagrams.md` | `docs/diagrams/DIAGRAMS.md` | Curated — agent-internal diagrams excluded |
| `releases/v*.md` | `docs/RELEASE_NOTES_v*.md` | Direct — user-facing already |
| `changelog.md` | `CHANGELOG.md` | Direct |

---

## Questions?

Open an issue or ask in [Discord](https://discord.gg/cherenkov). The [RUNBOOK.md](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/docs-site/RUNBOOK.md) covers operational procedures for maintainers.
