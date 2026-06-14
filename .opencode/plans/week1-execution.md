# Week 1 Execution Plan: GH Action + VS Code Extension

## Stream A: GitHub Actions Action (action.yml)

**Current state:** Basic action exists at `action.yml` — composite action with `validate` only, SARIF upload.

**Changes to make:**

### 1. Update `action.yml` — add diff mode + PR annotation

Replace the current content with:

```yaml
name: 'Cherenkov QA Conformance Test'
description: 'Runs Cherenkov QA API conformance tests against OpenAPI specs. Generates Playwright tests from your spec, catches spec-server drift, and uploads SARIF results. Supports diff-aware mode for PRs.'
author: 'Moaid Moatasem'
branding:
  icon: 'check-circle'
  color: 'blue'

inputs:
  spec_path:
    description: 'Path to OpenAPI or GraphQL spec'
    required: true
  target_url:
    description: 'Target API URL to test against'
    required: true
  source_type:
    description: 'Type of spec (openapi, graphql, grpc, accessibility)'
    required: false
    default: 'openapi'
  format:
    description: 'Output format (json, text, sarif, junit)'
    required: false
    default: 'sarif'
  output_path:
    description: 'Path for output report'
    required: false
    default: '.cherenkov/cherenkov_report.sarif'
  mode:
    description: 'Test mode — full (all endpoints) or diff (changed endpoints only, requires diff_base)'
    required: false
    default: 'full'
  diff_base:
    description: 'Git ref to compare against (e.g. origin/main). Required for diff mode.'
    required: false
    default: ''
  fail_on_drift:
    description: 'Exit with error if any conformance drift is detected'
    required: false
    default: 'true'
  workers:
    description: 'Number of parallel workers for test execution'
    required: false
    default: '2'

runs:
  using: 'composite'
  steps:
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
        cache: pip

    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: npm
        cache-dependency-path: stub/package-lock.json

    - name: Fetch git history for diff mode
      if: ${{ inputs.mode == 'diff' && inputs.diff_base != '' }}
      shell: bash
      run: |
        git fetch origin --depth=50 2>/dev/null || true
        echo "base_ref=${{ inputs.diff_base }}" >> $GITHUB_ENV

    - name: Install dependencies
      shell: bash
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        cd stub && npm ci && cd ..

    - name: Generate tests from spec
      shell: bash
      run: |
        ARGS="validate --spec ${{ inputs.spec_path }} --target ${{ inputs.target_url }}"
        ARGS="$ARGS --source ${{ inputs.source_type }}"
        ARGS="$ARGS --workers ${{ inputs.workers }}"

        if [ "${{ inputs.mode }}" = "diff" ] && [ -n "${{ inputs.diff_base }}" ]; then
          echo "Running diff-aware mode against ${{ inputs.diff_base }}"
          ARGS="$ARGS --diff-base ${{ inputs.diff_base }}"
        fi

        echo "::group::CHERENKOV output"
        python cherenkov.py $ARGS
        EXIT_CODE=$?
        echo "::endgroup::"
        echo "exit_code=$EXIT_CODE" >> $GITHUB_ENV

    - name: Generate SARIF report
      if: ${{ inputs.format == 'sarif' && always() }}
      shell: bash
      run: |
        python cherenkov.py validate \
          --spec ${{ inputs.spec_path }} \
          --target ${{ inputs.target_url }} \
          --source ${{ inputs.source_type }} \
          --format sarif \
          --output ${{ inputs.output_path }} \
          --workers ${{ inputs.workers }} || true

    - name: Upload SARIF results to GitHub Security
      if: ${{ inputs.format == 'sarif' && always() }}
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: ${{ inputs.output_path }}
        category: cherenkov-conformance

    - name: Annotate PR with conformance results
      if: ${{ github.event_name == 'pull_request' && always() }}
      uses: actions/github-script@v7
      with:
        script: |
          const fs = require('fs');
          const reportPath = '${{ inputs.output_path }}';
          let summary = '\u2705 **Cherenkov QA** \u2014 No conformance violations detected.';
          try {
            const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
            if (report.runs?.[0]?.results?.length > 0) {
              const violations = report.runs[0].results;
              summary = `\u26a0\ufe0f **Cherenkov QA** \u2014 ${violations.length} conformance violation(s) detected.\n\n`;
              for (const v of violations.slice(0, 10)) {
                summary += `- \`${v.message.text}\`\n`;
              }
              if (violations.length > 10) {
                summary += `\n\u2026 and ${violations.length - 10} more. See SARIF artifact for full report.`;
              }
            }
          } catch {}
          await github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: summary
          });

    - name: Fail on drift
      if: ${{ inputs.fail_on_drift == 'true' && env.exit_code != '0' }}
      shell: bash
      run: |
        echo "::error::CHERENKOV detected conformance drift. See SARIF report for details."
        exit ${{ env.exit_code || 1 }}
```

### 2. Create GitHub Actions workflow for CI test

Create `.github/workflows/cherenkov-ci.yml`:

```yaml
name: CHERENKOV Conformance

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Cherenkov conformance (full)
        uses: ./  # uses local action.yml
        with:
          spec_path: stub/openapi_3_1.yaml
          target_url: http://localhost:8000
          format: sarif
          mode: full

      - name: Run Cherenkov conformance (diff, PR-aware)
        if: github.event_name == 'pull_request'
        uses: ./
        with:
          spec_path: stub/openapi_3_1.yaml
          target_url: http://localhost:8000
          format: sarif
          mode: diff
          diff_base: origin/${{ github.base_ref || 'main' }}
```

### 3. Test the action locally

```bash
# From WSL:
cd ~/cherenkov-qa
python -m pip install -r requirements.txt
cd stub && npm ci && cd ..
python cherenkov.py validate --spec stub/openapi_3_1.yaml --target http://localhost:8000
```

---

## Stream B: VS Code Extension

**Current state:** Full scaffold exists at `vscode/` — `package.json`, `src/extension.ts`, 4 commands, CodeLens, TreeView, Webview panel, API client.

### What's missing:
1. `images/icon.png` — referenced in `package.json` but doesn't exist
2. `node_modules/` — npm install hasn't been run
3. Compiled JavaScript (`out/`) — TypeScript hasn't been compiled

### 1. Create SVG icon

Create `vscode/images/icon.svg` (VS Code accepts SVG):

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1a1a2e"/>
      <stop offset="100%" stop-color="#16213e"/>
    </linearGradient>
  </defs>
  <rect width="128" height="128" rx="16" fill="url(#bg)"/>
  <text x="64" y="72" font-family="monospace" font-size="48" font-weight="bold" fill="#58a6ff" text-anchor="middle">C</text>
  <text x="64" y="100" font-family="monospace" font-size="14" fill="#8b949e" text-anchor="middle">CHERENKOV</text>
</svg>
```

Update `package.json` to use SVG instead of PNG:

```json
"icon": "images/icon.svg"
```

### 2. Install and compile

```bash
cd ~/cherenkov-qa/vscode
npm install

# Add these dev dependencies if missing:
npm install --save-dev typescript @types/node @types/vscode @vscode/vsce

# Compile:
npx tsc -p tsconfig.json

# Package:
npx vsce package
```

### 3. Verify `vscode/tsconfig.json`

```json
{
  "compilerOptions": {
    "module": "commonjs",
    "target": "ES2020",
    "outDir": "out",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "sourceMap": true,
    "declaration": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "out"]
}
```

### 4. Test the extension

```bash
# From WSL vscode/ directory:
npx vsce package
# Produces cherenkov-qa-1.0.0.vsix
# Install in VS Code:
code --install-extension cherenkov-qa-1.0.0.vsix
```

### 5. Publish to marketplace

```bash
# Requires personal access token from https://dev.azure.com
npx vsce publish
```

---

## Week 1 Success Criteria

- [ ] `action.yml` updated with diff mode + PR annotation
- [ ] `.github/workflows/cherenkov-ci.yml` created
- [ ] Action tested locally: `python cherenkov.py validate --spec stub/openapi_3_1.yaml --target http://localhost:8000` works
- [ ] `vscode/images/icon.svg` created
- [ ] `package.json` updated to use SVG
- [ ] `npm install` runs clean in `vscode/`
- [ ] `npx tsc -p tsconfig.json` compiles clean
- [ ] `npx vsce package` produces `.vsix`
- [ ] Extension installs and activates in VS Code
- [ ] Right-click openapi.yaml → "Generate Tests" works

---

## Commands Summary

```bash
# --- GitHub Action ---
# Write the updated action.yml (content above)
# Create .github/workflows/cherenkov-ci.yml

# --- VS Code Extension ---
cd ~/cherenkov-qa/vscode
npm install
npm install --save-dev typescript @types/node @types/vscode @vscode/vsce
npx tsc -p tsconfig.json
npx vsce package
```
