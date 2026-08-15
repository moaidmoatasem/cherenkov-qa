---
title: K8s Operator
---

# Kubernetes Operator

CHERENKOV ships a **Kubernetes operator** that manages `ConformanceCheck` custom resources for scheduled, in-cluster API conformance runs. The operator is built with `controller-runtime` and runs as a Deployment in the `cherenkov` namespace.

## Architecture

```
┌─────────────────────────────────────────┐
│  K8s API Server                         │
│  ┌─────────────────────────────────┐    │
│  │ ConformanceCheck CR (validation │    │
│  │ .cherenkov.io/v1alpha1)         │    │
│  └──────────┬──────────────────────┘    │
└─────────────┼───────────────────────────┘
              │ reconcile
┌─────────────▼───────────────────────────┐
│  cherenkov-operator (Deployment)        │
│  - Watches ConformanceCheck resources   │
│  - Creates Jobs for conformance runs    │
│  - Updates status subresource           │
│  - Exposes /healthz + /readyz probes    │
└─────────────────────────────────────────┘
```

## Install

```bash
# Apply the CRD
kubectl apply -f https://github.com/moaidmoatasem/cherenkov-qa/releases/latest/download/crd-conformancecheck.yaml

# Create namespace
kubectl create namespace cherenkov

# Deploy the operator
kubectl apply -f https://github.com/moaidmoatasem/cherenkov-qa/releases/latest/download/operator-deployment.yaml
kubectl apply -f https://github.com/moaidmoatasem/cherenkov-qa/releases/latest/download/operator-rbac.yaml
```

## Create a ConformanceCheck

```yaml
apiVersion: validation.cherenkov.io/v1alpha1
kind: ConformanceCheck
metadata:
  name: my-api-check
spec:
  targetRef:
    apiVersion: v1
    kind: Service
    name: my-api
    namespace: default
    port: 8080
  specRef: https://my-api.example.com/openapi.json
  schedule: "0 */6 * * *"   # every 6 hours
  gates:
    - name: status-codes
      type: status
      assert: "all"
    - name: response-schema
      type: schema
      assert: "strict"
  llmConcurrency: 2
  failOnDrift: true
```

```bash
kubectl apply -f conformance-check.yaml
kubectl get conformancechecks
kubectl get cck  # short name
```

## CRD Spec Fields

### `spec` fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `targetRef` | object | yes | Reference to the target Kubernetes Service |
| `specRef` | string | no | URL or path to the OpenAPI spec |
| `schedule` | string | no | Cron expression for scheduled runs |
| `gates` | array | no | Conformance gates to enforce |
| `llmConcurrency` | integer | no | Max concurrent LLM tasks (1-16) |
| `deviceTargets` | array | no | Mobile device targets for visual testing |
| `visualConfig` | object | no | Visual validation configuration |

### `status` fields

| Field | Type | Description |
|-------|------|-------------|
| `phase` | string | `Pending`, `Running`, `Pass`, `Fail`, or `Error` |
| `lastRun` | string | ISO 8601 timestamp of last execution |
| `result` | object | Pass/fail summary with divergence details |
| `conditions` | array | Standard Kubernetes condition objects |

## Operator Configuration

The operator Deployment exposes:

| Endpoint | Port | Purpose |
|----------|------|---------|
| `/healthz` | 8081 | Liveness probe |
| `/readyz` | 8081 | Readiness + Ollama connectivity check |
| Metrics | 8080 | Prometheus metrics |

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENT_LLM_TASKS` | `2` | Max parallel LLM calls per reconciliation |

## RBAC

The operator uses a dedicated ServiceAccount (`cherenkov-operator`) with a ClusterRole granting access to:

- `conformancechecks` + `conformancechecks/status` (CRD management)
- `jobs` (batch execution)
- `pods`, `pods/exec`, `configmaps`, `events` (runtime management)

## Building from Source

```bash
cd operator
docker build -t cherenkov-operator:latest .
```

The multi-stage Dockerfile produces a static binary (~20MB) that runs as non-root user `65532:65532`.

For full source, see the [operator directory](https://github.com/moaidmoatasem/cherenkov-qa/tree/main/operator) and [k8s manifests](https://github.com/moaidmoatasem/cherenkov-qa/tree/main/k8s).
