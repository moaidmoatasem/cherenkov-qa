---
sidebar_position: 2
---

# CLI Reference

The CHERENKOV CLI is the primary way to interact with the platform.

## `init`
\`\`\`bash
npx cherenkov init
\`\`\`
Initializes a new CHERENKOV configuration in the current directory. Creates `.cherenkov/config.yaml`.

## `generate`
\`\`\`bash
npx cherenkov generate --spec <path_to_spec>
\`\`\`
Reads the provided OpenAPI specification and generates typed Playwright tests for every endpoint.

**Flags:**
- `--spec`: Path to the OpenAPI `.yaml` or `.json` file.
- `--output`: (Optional) Path to export tests to. Defaults to `./tests`.

## `check`
\`\`\`bash
npx cherenkov check
\`\`\`
Runs the generated conformance tests against the target API defined in `.cherenkov/config.yaml`.

## `dashboard`
\`\`\`bash
npx cherenkov dashboard
\`\`\`
Spins up the local React dashboard to visually explore endpoints, conformance results, and the Knowledge Mesh GraphRAG.

## `eject`
\`\`\`bash
npx cherenkov eject --output ./ejected-tests
\`\`\`
Strips all proprietary CHERENKOV imports and utilities from the generated tests, leaving pure vanilla Playwright tests that can be run completely independently of the CHERENKOV platform.
