# Build Artifacts Script

Run this Python script to create all Week 1 artifacts.

```python
#!/usr/bin/env python3
"""Create week 1 build artifacts: action.yml, GH workflow, VS Code icon, CI workflow."""
import base64, os, subprocess, sys

PROJECT = os.path.expanduser("~/cherenkov-qa")

def write_action_yml():
    L = chr(123)
    R = chr(125)
    DQ = chr(34)

    content = f"""name: 'Cherenkov QA Conformance Test'
description: 'Runs CHERENKOV QA API conformance tests against OpenAPI specs. Generates Playwright tests from your spec, catches spec-server drift, and uploads SARIF results. Supports diff-aware mode for PRs.'
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
    description: 'Test mode - full (all endpoints) or diff (changed endpoints only, requires diff_base)'
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
      if: {L}{L} inputs.mode == {DQ}diff{DQ} && inputs.diff_base != {DQ}{DQ} {R}{R}
      shell: bash
      run: |
        git fetch origin --depth=50 2>/dev/null || true
        echo {DQ}base_ref={L}{L} inputs.diff_base {R}{R}{DQ} >> $GITHUB_ENV

    - name: Install dependencies
      shell: bash
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        cd stub && npm ci && cd ..

    - name: Run Cherenkov (validate)
      shell: bash
      run: |
        ARGS={DQ}validate --spec {L}{L} inputs.spec_path {R}{R} --target {L}{L} inputs.target_url {R}{R}{DQ}
        ARGS={DQ}$ARGS --source {L}{L} inputs.source_type {R}{R}{DQ}
        ARGS={DQ}$ARGS --workers {L}{L} inputs.workers {R}{R}{DQ}

        if [ {DQ}{L}{L} inputs.mode {R}{R}{DQ} = {DQ}diff{DQ} ] && [ -n {DQ}{L}{L} inputs.diff_base {R}{R}{DQ} ]; then
          ARGS={DQ}$ARGS --diff-base {L}{L} inputs.diff_base {R}{R}{DQ}
          echo {DQ}Running diff-aware mode against {L}{L} inputs.diff_base {R}{R}{DQ}
        fi

        echo {DQ}::group::CHERENKOV output{DQ}
        python cherenkov.py $ARGS
        EXIT_CODE=$?
        echo {DQ}::endgroup::{DQ}
        echo {DQ}exit_code=$EXIT_CODE{DQ} >> $GITHUB_ENV

    - name: Generate SARIF report
      if: {L}{L} always() {R}{R}
      shell: bash
      run: |
        python cherenkov.py validate --spec {L}{L} inputs.spec_path {R}{R} --target {L}{L} inputs.target_url {R}{R} --source {L}{L} inputs.source_type {R}{R} --format sarif --output {L}{L} inputs.output_path {R}{R} --workers {L}{L} inputs.workers {R}{R} || true

    - name: Upload SARIF results
      if: {L}{L} inputs.format == {DQ}sarif{DQ} && always() {R}{R}
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: {L}{L} inputs.output_path {R}{R}
        category: cherenkov-conformance

    - name: Annotate PR
      if: {L}{L} github.event_name == {DQ}pull_request{DQ} && always() {R}{R}
      uses: actions/github-script@v7
      with:
        script: |
          const fs = require('fs');
          const rp = {DQ}{L}{L} inputs.output_path {R}{R}{DQ};
          let s = String.fromCharCode(9989) + {DQ} **Cherenkov QA** - No violations.{DQ};
          try {{
            const r = JSON.parse(fs.readFileSync(rp, {DQ}utf8{DQ}));
            if (r.runs?.[0]?.results?.length > 0) {{
              const v = r.runs[0].results;
              s = String.fromCharCode(9888,65039) + {DQ} **Cherenkov QA** - {DQ} + v.length + {DQ} violation(s).{DQ};
            }}
          }} catch(e) {{}}
          await github.rest.issues.createComment({{
            issue_number: context.issue.number, owner: context.repo.owner, repo: context.repo.repo, body: s
          }});

    - name: Fail on drift
      if: {L}{L} inputs.fail_on_drift == {DQ}true{DQ} && env.exit_code != {DQ}0{DQ} {R}{R}
      shell: bash
      run: |
        exit {L}{L} env.exit_code || 1 {R}{R}
"""
    path = os.path.join(PROJECT, "action.yml")
    with open(path, "w") as f:
        f.write(content)
    print(f"Written action.yml ({len(content)} bytes)")

def write_ci_workflow():
    content = """name: Cherenkov Conformance
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
  workflow_dispatch:
jobs:
  conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Run Cherenkov
        uses: ./
        with:
          spec_path: stub/openapi_3_1.yaml
          target_url: http://localhost:8000
          format: sarif
          mode: full
"""
    d = os.path.join(PROJECT, ".github", "workflows")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "cherenkov-ci.yml"), "w") as f:
        f.write(content)
    print("Written .github/workflows/cherenkov-ci.yml")

def write_vscode_icon():
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#1a1a2e"/><stop offset="100%" stop-color="#16213e"/>
  </linearGradient></defs>
  <rect width="128" height="128" rx="16" fill="url(#bg)"/>
  <text x="64" y="72" font-family="monospace" font-size="48" font-weight="bold" fill="#58a6ff" text-anchor="middle">C</text>
  <text x="64" y="100" font-family="monospace" font-size="14" fill="#8b949e" text-anchor="middle">CHERENKOV</text>
</svg>"""
    d = os.path.join(PROJECT, "vscode", "images")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "icon.svg"), "w") as f:
        f.write(svg)
    print("Written vscode/images/icon.svg")

def fix_vscode_package():
    import json
    pkg_path = os.path.join(PROJECT, "vscode", "package.json")
    with open(pkg_path, "r") as f:
        pkg = json.load(f)
    pkg["icon"] = "images/icon.svg"
    with open(pkg_path, "w") as f:
        json.dump(pkg, f, indent=2)
    print("Updated vscode/package.json icon path")

if __name__ == "__main__":
    write_action_yml()
    write_ci_workflow()
    write_vscode_icon()
    fix_vscode_package()
    print()
    print("=== Week 1 artifacts built ===")
    print("Next: cd ~/cherenkov-qa/vscode && npm install && npx tsc && npx vsce package")
```
