# CHERENKOV k3d Cluster

Kubernetes manifests for running CHERENKOV on a local k3d cluster.

## Prerequisites

- Docker
- k3d (v5+) — `scripts/k3d` binary included, or install via `scripts/install-tools.sh`
- kubectl
- Go 1.22+ (for building the operator)

## Quick Start

```bash
# One-command bootstrap:
make k3d-up

# Or step by step:
k3d cluster create cherenkov --config k8s/k3d-cluster.yaml
kubectl apply -k k8s/
```

## Services

| Service | Type | Internal DNS | Port |
|---------|------|-------------|------|
| Ollama | StatefulSet | `ollama:11434` | 11434 |
| Prism | Deployment | `prism:4010` | 4010 |
| CHERENKOV | Deployment | `cherenkov:8000` | 8000 |

## Testing

```bash
make k3d-test
```

## Cleanup

```bash
make k3d-down
k3d cluster delete cherenkov
```
