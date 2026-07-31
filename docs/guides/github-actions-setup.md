# CHERENKOV in GitHub Actions

The absolute best way to use CHERENKOV is as a blocking CI gate. By adding CHERENKOV to your GitHub Actions workflow, you ensure that **spec drift never makes it to production**.

## The Marketplace Action

We publish an official GitHub Action that handles downloading, configuring, and executing CHERENKOV against your API.

### Basic Setup

Create a file in your repository at `.github/workflows/conformance.yml`:

```yaml
name: API Conformance

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # 1. Start your API server in the background
      - name: Start API
        run: |
          npm install
          npm start &
          sleep 5 # Wait for server to be ready

      # 2. Run CHERENKOV
      - name: CHERENKOV Conformance Check
        uses: cherenkov-qa/action@v1
        with:
          spec: ./openapi.yaml
          target: http://localhost:8080
          fail-on-drift: 'true'
          llm-provider: 'openai' # Use cloud LLM for fast CI runs
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## SARIF Integration (GitHub Security Tab)

If you enable SARIF output, CHERENKOV will report API conformance violations directly into the GitHub Security tab and annotate the exact lines in your OpenAPI spec that caused the drift!

```yaml
      - name: CHERENKOV Conformance Check
        uses: cherenkov-qa/action@v1
        with:
          spec: ./openapi.yaml
          target: http://localhost:8080
          output-format: sarif
          output-path: cherenkov-results.sarif

      - name: Upload SARIF file
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: cherenkov-results.sarif
```

Now, every time an engineer opens a Pull Request that breaks the API contract, they'll see a red "X" right on their PR!
