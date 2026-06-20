---
sidebar_position: 1
---

# Getting Started

Welcome to **CHERENKOV-QA**, the AI-native API conformance platform. 
CHERENKOV helps you catch API spec drift before it hits production, using an LLM to generate test structures and your OpenAPI spec to generate assertions.

## Quickstart

You can generate your first test suite in under 60 seconds without installing anything locally besides Node.js and an Ollama instance.

### 1. Prerequisites

CHERENKOV uses `qwen2.5-coder:7b` via Ollama by default so that your proprietary specs remain private.

\`\`\`bash
# Pull and run the model
ollama run qwen2.5-coder:7b
\`\`\`

### 2. Scaffold a Project

Navigate to an empty directory (or the root of your existing API project) and run the initialization script:

\`\`\`bash
npx cherenkov init
\`\`\`

This will generate a `.cherenkov/config.yaml` and a sample `api.yaml`.

### 3. Generate Tests

To generate tests against the spec:

\`\`\`bash
npx cherenkov generate --spec ./api.yaml
\`\`\`

You'll see CHERENKOV reading the spec, calling the LLM, passing the 6-gate review, and outputting Playwright test files in the `tests/` directory.

### 4. Run the Dashboard

Explore the results visually:

\`\`\`bash
npx cherenkov dashboard
\`\`\`
