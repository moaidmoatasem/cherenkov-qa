# CHERENKOV Operator

A Kubernetes operator that validates API conformance via `ConformanceCheck` CRDs.

## Quick start

```bash
# Build the operator
cd operator && go build -o manager main.go

# Build the CLI bridge
cd cmd/k8s-run && go build -o k8s-run main.go

# Or build the Docker image
docker build -t cherenkov/operator:latest .
```

## Usage

```bash
# Run a ConformanceCheck from CLI
./k8s-run --spec petstore-spec --target prism --port 4010

# Or apply a CRD directly
kubectl apply -f - <<EOF
apiVersion: validation.cherenkov.io/v1alpha1
kind: ConformanceCheck
metadata:
  name: petstore-smoke
  namespace: cherenkov
spec:
  targetRef:
    apiVersion: v1
    kind: Service
    name: prism
    namespace: cherenkov
    port: 4010
  specRef: petstore-spec
EOF

# Watch status
kubectl get conformancecheck -w
kubectl describe conformancecheck petstore-smoke
```

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `MAX_CONCURRENT_LLM_TASKS` | `2` | Max concurrent LLM validation tasks |

## Architecture

See [docs/vision/14_KUBERNETES_CONSIDERATIONS.md](../docs/vision/14_KUBERNETES_CONSIDERATIONS.md)
