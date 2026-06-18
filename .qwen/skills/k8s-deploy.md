---
name: k8s-deploy
description: Deploy CHERENKOV to a local k3d Kubernetes cluster and run the conformance test suite. Uses the existing scripts/k3d binary and Makefile targets.
triggers:
  - "k8s deploy"
  - "k3d"
  - "kubernetes"
  - "deploy cherenkov"
  - "make k3d-test"
---

# Skill: k8s-deploy

## Purpose
Deploy CHERENKOV to a local k3d cluster and run the full k8s conformance suite.  
This validates the Kubernetes packaging and engine (Go binary) alongside the Python core.

## Prerequisites
- k3d binary at `scripts/k3d`
- kubectl at `~/.local/bin/kubectl` (v1.31.0)
- Docker running
- Go 1.22.5 at `~/.local/opt/go/bin/go`

## Workflow

### Quick path — use Makefile
```bash
make k3d-test
```
This is the recommended path. It handles cluster creation, image build, deployment, and test run.

### Manual path

#### Step 1 — Create cluster
```bash
scripts/k3d cluster create cherenkov-test --wait
```

#### Step 2 — Build and load images
```bash
docker build -t cherenkov:dev .
docker build -t cherenkov-mcp:latest -f Dockerfile.mcp .
scripts/k3d image import cherenkov:dev cherenkov-mcp:latest -c cherenkov-test
```

#### Step 3 — Apply k8s manifests
```bash
~/.local/bin/kubectl apply -f k8s/
~/.local/bin/kubectl wait --for=condition=ready pod -l app=cherenkov --timeout=120s
```

#### Step 4 — Run conformance checks
```bash
python3 cherenkov.py validate --target http://$(kubectl get svc cherenkov -o jsonpath='{.spec.clusterIP}'):8080
```

#### Step 5 — Cleanup
```bash
scripts/k3d cluster delete cherenkov-test
```

## Expected Output
- All pods: `Running`
- Conformance: `PASS` with 0 high-severity findings
- Gate: `PASS`

## On Failure
Check pod logs:
```bash
~/.local/bin/kubectl logs -l app=cherenkov --tail=100
```
Report findings — do NOT auto-patch manifests without review.

## References
- `scripts/k3d-test.sh` — shell script version
- `k8s/` — Kubernetes manifests
- `engine/` — Go conformance engine source
- Phase 8 completion: `make k3d-test` is green
