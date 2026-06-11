# Deployment

## Health Probes
The Kubernetes operator provides two health check endpoints to manage the pod lifecycle:
- `/healthz` -> Liveness probe. Returns 200 OK when the controller loop is running.
- `/readyz` -> Readiness probe. Returns 200 OK when the controller cache is synced AND the embedded Ollama process responds to requests.

Port 8081 is used for these health probes (which does not conflict with the default 8080 metrics port).

## GitHub Actions Integration
You can use the native CHERENKOV composite action to enforce API conformance checks in your CI pipelines.

```yaml
name: API Conformance

on:
  pull_request:
    paths:
      - 'openapi.yaml'
      - 'src/**'

jobs:
  conformance:
    runs-on: ubuntu-latest
    services:
      api:
        image: your-api-image:latest
        ports:
          - 8080:8080

    steps:
      - uses: actions/checkout@v4

      - name: Run CHERENKOV
        uses: moaidmoatasem/cherenkov-qa@v1
        with:
          spec: openapi.yaml
          target: http://localhost:8080
          fail-on-drift: true
          ollama-cache-key: qwen-7b-v1
```

### Action Inputs
| Input | Description | Default |
|-------|-------------|---------|
| `spec` | Path to OpenAPI or GraphQL spec file | `openapi.yaml` |
| `target` | Target API URL to test against | (required) |
| `fail-on-drift` | Fail the step if conformance drift is detected | `false` |
| `model` | Ollama model to use for test generation | `qwen2.5-coder:7b` |
| `ollama-cache-key` | Cache key for the Ollama model (set to skip re-pull) | `""` |

### Action Outputs
| Output | Description |
|--------|-------------|
| `drift-count` | Number of conformance drift findings |
| `report-path` | Path to generated `.cherenkov/report.json` |

When `fail-on-drift` is false (default), the step will succeed even if there are drift findings, and SARIF output will be pushed to the GitHub Security tab automatically.
