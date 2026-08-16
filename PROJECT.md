# Project: CHERENKOV-QA Documentation Consolidation (v1.4)

## Architecture
- `docs/1.4/`: Consolidated documentation tree for CHERENKOV-QA version 1.4 (Diátaxis structure: Tutorials, How-To Guides, Reference, Explanation).
- `docs/1.4/assets/`: Static image and screenshot assets (`homepage_overview.png`, `getting_started.png`, `sitemap_architecture.png`, `version_diff.png`).
- `docs-site/docs/`: Live MkDocs source documentation matching version 1.4 baseline.
- `docs-site/overrides/`: Custom template overrides (`main.html`) handling dynamic version-warning banners.
- `mkdocs.yml` & `docs-site/mkdocs.yml`: MkDocs configuration files specifying site structure, theme, plugins (`pymdownx.superfences` for Mermaid), and version metadata (`extra.version.current: "1.4"`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Content Merge (1.2 + 1.3 -> 1.4) | Combine all pages from 1.2 and 1.3 into coherent 1.4 hierarchy, keeping 1.3/HEAD updates | M1 | R1, AC1 |
| 2 | Version Warning Banner Configuration | Ensure 1.4 suppresses outdated warning banner, while older version archives display warning pointing to 1.4 | M1 | R2, AC1 |
| 3 | Mermaid Visualizations | Version-diff flow and consolidated site map diagrams embedded in documentation | M2 | R3, AC2 |
| 4 | Static Screenshot Assets | PNG/SVG screenshots of key pages (homepage, getting started) in `docs/1.4/assets/` and referenced in docs | M2 | R3, AC2 |
| 5 | MkDocs Configuration | Configure `extra.version.current: "1.4"` and list previous versions; ensure clean build | M3 | R4, AC3 |
| 6 | Git Branch & Commit | Create branch `docs/consolidate-1.4`, commit all changes with conventional commit messages | M4 | R5, AC4 |
| 7 | Pull Request with Changelog | Open PR titled "Consolidate CHERENKOV-QA docs into version 1.4" targeting `main` with changelog | M4 | R5, AC4, AC5 |
| 8 | Multi-Agent Review & Challenge | Independent 2-Reviewer + 2-Challenger validation of rendered site, links, and layout | M5 | Verification |
| 9 | Forensic Integrity Audit | Binary veto audit confirming genuine implementations, valid assets, and no hardcoded bypasses | M5 | Audit |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Content Merge & Banner Fix | Combine 1.2/1.3 pages into `docs/1.4/`, resolve conflicts, verify banner behavior | none | IN_PROGRESS |
| 2 | Visualizations & Media | Add Mermaid diagrams for version flow & site map; generate/add static screenshots | M1 | PLANNED |
| 3 | MkDocs Config & Build Verification | Update `mkdocs.yml`, verify `mkdocs build` strict pass | M1, M2 | PLANNED |
| 4 | Git Workflow, Push & PR | Create branch `docs/consolidate-1.4`, commit, push to origin, open PR with changelog | M1, M2, M3 | PLANNED |
| 5 | Multi-Angle Review & Forensic Audit Gate | 2 Reviewers + 2 Challengers + 1 Forensic Auditor gate verification | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
- **Documentation Tree**: `docs/1.4/` must contain all merged markdown files and an `assets/` subdirectory for images.
- **Banner Behavior**: `docs/1.4/*.html` or `/1.4/` route MUST NOT render the `.md-version-warning` banner; legacy routes (`/1.2/`, `/1.3/`) MUST display `.md-version-warning` linking to `https://moaidmoatasem.github.io/cherenkov-qa/1.4` or `/1.4/`.
- **Mermaid Fences**: Diagram blocks must use ```mermaid syntax supported by `pymdownx.superfences`.
- **MkDocs Config**: `mkdocs.yml` MUST define `extra.version.current: "1.4"` and `extra.version.versions: ["1.2", "1.3", "1.4"]`.
- **Git Branch**: Branch name MUST be `docs/consolidate-1.4`, targeting `main`. PR title MUST be `"Consolidate CHERENKOV-QA docs into version 1.4"`.

## Code Layout
- Documentation Root: `docs/1.4/`
- Documentation Assets: `docs/1.4/assets/`
- MkDocs Source Site: `docs-site/docs/`
- MkDocs Overrides: `docs-site/overrides/`
- Root Config: `mkdocs.yml`
- Site Config: `docs-site/mkdocs.yml`
