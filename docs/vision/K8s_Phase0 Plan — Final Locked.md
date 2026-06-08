## Phase 0 Plan — Final Locked

All three agents converge after debate. Here's the definitive set:

### ✅ Three Decisions — All Settled

| Decision | Choice | Agents |
|----------|--------|--------|
| **Healer isolation** | **Option A — Ephemeral K8s Jobs** (not sandbox pod, not Docker socket) | 1/1, 2/3, 3/1 — unanimous |
| **Phase 0 scope** | **Core only: prism + cherenkov + ollama** (no agents) | unanimous |
| **CLI bridge** | **CRD generator** (`cherenkov k8s run` generates ConformanceCheck YAML → `kubectl apply` → watches status) | 1/1, 3/1 describe "shell-out" but mean Job-container execution; 2/3 correctly calls it CRD-generation. The actual validation always runs in-cluster via Jobs, never in the operator process |

### 🔧 5 Critical Fixes (F1-F5) — Before Day 1

| ID | File | Fix |
|----|------|-----|
| **F1** | `k8s/k3d-cluster.yaml` | Remove Ollama LB port + Docker socket volume |
| **F2** | `k8s/ollama-init-job.yaml` | Add file — Job that runs `ollama pull` before StatefulSet |
| **F3** | `k8s/namespace.yaml` | Add file — create `cherenkov` ns with `pod-security.kubernetes.io/enforce: baseline` |
| **F4** | `k8s/operator-rbac.yaml` | Add file — ServiceAccount + Role + RoleBinding |
| **F5** | `ROADMAP_PACKAGING.md` | Add override line: `OVERRIDDEN by Phase 0 operator spike — owner: @moaid, 2026-06-07 — rationale: GitOps + multi-tenant demand` |

### 📅 Phase 0 Days 1-5

| Day | Task | Deliverable |
|-----|------|-------------|
| **1** | Bootstrap: apply F1-F5, `k3d-up`, all pods healthy | `make k3d-up` green |
| **2** | `cherenkov k8s run` CLI + ConformanceCheck CRD scaffold | CLI creates CR, applies it, watches status |
| **3** | Operator reconciler (kubebuilder) + Job runner + concurrency semaphore | CR → Job → status update → K8s Event |
| **4** | Integration tests: happy path + failure + concurrency + cleanup | `make k3d-test` passes |
| **5** | Demo to stakeholders | Full validate flow in k3d |

### 📁 Directory Structure (Locked)

```
cherenkov-qa/
├── operator/                         # NEW Go module
│   ├── go.mod / go.sum
│   ├── main.go                       # kubebuilder entrypoint
│   ├── api/v1alpha1/
│   │   ├── conformancecheck_types.go
│   │   └── groupversion_info.go
│   ├── controllers/
│   │   └── conformancecheck_controller.go
│   ├── internal/
│   │   ├── runner.go                 # Job template
│   │   └── scheduler.go             # MAX_CONCURRENT_LLM_TASKS semaphore
│   ├── cmd/k8s-run/main.go          # CLI bridge: CRD gen + apply + watch
│   ├── config/
│   │   ├── rbac/
│   │   ├── crd/
│   │   └── manager/
│   └── Dockerfile                    # multi-stage Go build
├── k8s/
│   ├── namespace.yaml                # NEW (F3)
│   ├── k3d-cluster.yaml              # FIXED (F1)
│   ├── ollama-statefulset.yaml
│   ├── ollama-service.yaml
│   ├── ollama-init-job.yaml          # NEW (F2)
│   ├── ollama-pvc.yaml
│   ├── prism-deployment.yaml
│   ├── prism-service.yaml
│   ├── cherenkov-deployment.yaml
│   ├── cherenkov-service.yaml
│   ├── operator-rbac.yaml            # NEW (F4)
│   └── kustomization.yaml
├── Makefile                          # NEW targets: k3d-up/down/reset/test + operator-image
└── scripts/
    ├── k3d-setup.sh                  # NEW (Linux/macOS)
    └── k3d-setup.ps1                 # Windows
```

### 🎯 Why This Plan Survives the Premortem

| Failure from Premortem | How This Plan Prevents It |
|------------------------|--------------------------|
| Healer Job latency spiral | Accepted — healing is async, 2-5s is fine |
| GPU thundering herd | Concurrency semaphore (`MAX_CONCURRENT_LLM_TASKS=2`) |
| Kopf/async impedance | Go operator — zero async risk |
| QA adoption mutiny | `cherenkov k8s run` CLI bridge — QA never touches YAML |
| Process isolation broken | Ephemeral Jobs = true disposability per invocation |
| SSOT violation | F5 reconciles ROADMAP_PACKAGING.md explicitly |

**Ready to start.** Say "go" and I'll execute Day 1: apply F1-F5, scaffold k3d cluster, and produce the first K8s manifests.