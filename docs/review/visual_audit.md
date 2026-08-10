# Visual Asset Audit

## Current State
- The repository contains an exceptionally high number of `.svg` files (14,987). This suggests either a massive icon library (e.g., node_modules/ or similar that was checked in) or auto-generated visual reports.
- UI assets exist in `vscode/images/` (e.g., `icon.png`, `icon.svg`).
- There are some PNGs/JPEGs scattered, but they are minimal (31 `.png` files).
- Diagrams exist under `docs/diagrams/DIAGRAMS.md`, but it's unclear if these are native Mermaid diagrams or linked images.

## Issues Identified
1. **SVG Bloat**: Over 14,000 SVGs is likely an anomaly (possibly checked-in dependencies or build artifacts). These need to be investigated and added to `.gitignore` if they are not source assets.
2. **Lack of Inline Visuals**: The core documentation files lack inline diagrams. Modern docs require architecture diagrams to break up text.

## Action Items
- **Investigate SVGs**: Run a script to identify the source of the 14,987 `.svg` files and remove them from version control if they are artifacts.
- **Implement Mermaid**: Replace static diagrams or purely text-based architectural descriptions with native Mermaid.js blocks in Markdown. This ensures they are version-controlled and render natively in GitHub and MkDocs.
