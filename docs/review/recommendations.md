# Master Recommendations for Documentation Refactor

Based on the thorough repository review, here are the prioritized recommendations to transform the Cherenkov QA documentation into a reconciled, humanized, and visual asset ready for end-users.

## High Priority (Immediate Action)
1. **Consolidate Roadmaps**: Merge `MASTER_ROADMAP`, `ROADMAP_2026H2`, and `ROADMAP_AQE` into a single, authoritative `ROADMAP.md` at the root of `docs/`.
2. **Clean Up Historical Handover Files**: Move the numerous `AGENT_HANDOVER_*.md` and `SESSION_HANDOVER_*.md` files into a `docs/archive/handovers/` directory. This will instantly declutter the root documentation folder.
3. **Investigate SVG Bloat**: Identify why there are nearly 15,000 `.svg` files in the repository. If these are build artifacts or node_modules, add them to `.gitignore` and remove them from version control to reduce repo size.

## Medium Priority (Structural & Visual)
4. **Create a Unified Quick Start**: Develop a visual, step-by-step Quick Start guide. This should be the first page a user sees in the MkDocs site, replacing fragmented onboarding scripts.
5. **Implement Mermaid Diagrams**: Standardize on Mermaid.js for all architectural diagrams. Update the `Architecture.md` and `SYSTEM_DESIGN.md` files to include native Mermaid charts instead of relying solely on text descriptions.
6. **MkDocs Navigation Overhaul**: Update the `mkdocs.yml` (once located or recreated) to ensure the navigation tree strictly separates:
   - **User Guides** (Quick start, installation, usage)
   - **Developer Guides** (Architecture, ADRs, contributing)
   - **QA & Testing** (Test plans, validation reports)

## Low Priority (Long-Term Health)
7. **Consistent Terminology Audit**: Run a pass over the remaining consolidated documents to ensure consistent use of terminology (e.g., standardizing how "MCP Mesh" or "Reasoning Engine" is referred to).
8. **Automate Documentation Checks**: Integrate a CI step that verifies Markdown links (e.g., using `markdown-link-check`) to ensure the massive documentation web doesn't develop dead links over time.

---
**Next Steps**: If you approve these recommendations, we can begin executing the High Priority tasks, starting with the cleanup of handover files and consolidation of roadmaps.
