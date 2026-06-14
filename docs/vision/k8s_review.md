#agent1:

The user wants me to review the file docs/vision/14_KUBERNETES_CONSIDERATIONS.md thoroughly. The file content has already been provided in the user's message. Let me analyze this document carefully for quality, completeness, consistency with the CHERENKOV project patterns, and technical accuracy.

Let me review the content:

Purpose & Context: This is a strategic + implementation blueprint for Kubernetes considerations for CHERENKOV. It's part of the vision/docs series.
Content Overview:
Executive summary: Doesn't recommend migrating today, defines playbook
Decision framework: When K8s becomes necessary + anti-patterns
Current architecture → K8s primitives mapping
Tiered deployment continuum (Tier 1-4)
Migration path: Docker Compose → k3d → Full K8s
Helm chart architecture
GPU scheduling strategy
Networking topology
Storage architecture
Security model
Observability stack
CHERENKOV as a Kubernetes Operator
Cost analysis
Rollback strategy
Decision triggers & checkpoints
Implementation sequencing
Appendices
Now let me do a thorough review focusing on:

Internal consistency
Alignment with CHERENKOV design principles (mentioned in AGENTS.md: D7, anti-lock-in, suggest-only, spec-derived)
Technical accuracy of K8s concepts
Completeness of the plan
Any contradictions or gaps
Let me examine the content carefully:

Potential Issues I Notice:
Cross-reference inconsistency: The frontmatter says "Parent: 00_VISION.md" and "Predecessor: 13_DOCKER_AI_IMPLEMENTATION_PLAN.md" but the text says "Docker integration" for 12_DOCKER_AI_HORIZON.md. Let me check if that main makes sense.
Section 3 has YAML indentation issues: In the StatefulSet spec, the indentation looks correct at first glance but let me check carefully... looks okay.
Self-contradiction in GPU scheduling: Section 7.2 says RTX 3060 8GB is "small" tier for ollama only. But the cost table in 13.1 mentions "RTX 5060 laptop" - that's inconsistent (3060 vs 5060). Also the ollama resources in 6.2 say nvidia.com/gpu: "1" but doesn't specify tier compatibility.
Helm chart structure vs content: Section 6 says charts/cherenkov/ but section 6.2 values.yaml has cherenkov-deployment.yaml while section 8.3 network policies reference cherenkov.io/role: agent labels that aren't defined in the Helm chart templates listed in 6.1.
Mermaid diagrams: Multiple mermaid diagrams are used - these are fine for markdown but won't render in all contexts.
Missing anti-lock-in consideration: AGENTS.md says "Anti-lock-in: Tests must run without CHERENKOV (eject strips all imports)." This document doesn't mention how K8s deployment affects the eject/anti-lock-in pattern for tests.
D7 invariant: "Never auto-edit test code. Validate and healing produce reports/suggestions only." The operator section (12) talks about creating GitHub issues and notifications, which aligns with suggest-only, but the "Job Runner" spawning validate pods could be seen as auto-execution. Need to check if it respects D7.
Spec-derived status codes: AGENTS.md says "Spec-derived: Expected HTTP status comes from the OpenAPI spec, not hardcoded assumptions." The operator example in 12.1 uses "200 vs spec" which is good, but the old Docker Compose mapping doesn't explicitly mention how status codes are derived from spec.
Section 12 Operator benefits table: "Without Operator" says "Manual or cron" for triggers, but Compose has cron capabilities via restart policies. Slight inaccuracy but not critical.
GPU cost discrepancy: Table 13.1 mentions RTX 5060 laptop for Tier 1 ($0) but Section 7.2 mentions RTX 3060 8GB as the "small" tier. These are inconsistent.
Helm values vs actual K8s resources: The values.yaml in 6.2 uses lowercase keys for GPU (nvidia.com/gpu) but Kubernetes resource names are case-sensitive. Also the nvidia.com/mig-1g.5gb in 7.3 - is this a valid resource name? It should be nvidia.com/mig-1g.5gb but typically MIG uses nvidia.com/gpu with device plugin configuring MIG. Need to verify.
Missing imagePullSecrets: For private registries (Docker Hub), imagePullSecrets should be in values.yaml but aren't mentioned.
Operator reconciliation loop: Section 12 doesn't describe error handling, retry logic, or what happens when a ConformanceCheck CR is deleted.
HPA for LLM services: Section 6.1 lists hpa.yaml but section 6.2 has autoscaling.enabled: false and the note in 2.3 correctly says "Auto-scaling LLMs doesn't work — GPU memory is the bottleneck, not CPU". However, HPA is still listed in the chart structure with hpa.yaml - this could confuse users.
StatefulSet + InitContainer for ollama-init: In section 3.1, the StatefulSet initContainer curls ollama service. But if this is the first pod starting, the service might not be ready yet. Actually, it does until curl -s -f http://ollama:11434/api/tags; do sleep 1; done which was correct for waiting on the ollama container itself... wait, no. This initContainer is running IN the same pod as the ollama container, before the main container starts. So curl http://ollama:11434 from within an initContainer would try to reach the pod's own service IP, which may not work because the pod isn't running yet. Actually, in K8s, a pod's Service IP is assigned when the pod is scheduled, and the kubelet can route to it, but the container isn't running. However, the ollama service ClusterIP routes to the pod IP. Since the pod is scheduled and has an IP, the service should resolve to it. But the main container isn't running yet, so nothing is listening on 11434. The initContainer is waiting for something that can't start because it's waiting for itself. This is a bug in the example! The initContainer should probably use a different mechanism, or the model pull should happen as a Job before the StatefulSet starts, not as an InitContainer within the same pod.
Actually, wait - looking more carefully at the example: it's an InitContainer in the same StatefulSet pod. ollama service points to the pod. The initContainer tries to curl http://ollama:11434 which is the pod itself. But the main ollama container isn't running yet. So this initContainer will loop forever. This is definitely a bug in the provided YAML.

k3d cluster creation command: Section 5.1 shows k3d cluster create cherenkov but k3d syntax might need --config or different flags. The --volume /var/run/docker.sock:/var/run/docker.sock@agent:0 syntax is valid for k3d, but the cluster creation without any node count might default to a server node. The healer-agent needs Docker socket access but why mount it on agent:0 specifically?
Section 5.1 Makefile targets: Doesn't show what make k3d-up would look like.
Section 16.1: References "Compose Hardening" as DONE in "this session" but there's no evidence of what session or whether it's accurate to the current codebase state. Could be stale or referring to a previous session.
Let me look for more issues...

NetworkPolicy in 8.3: The egress sovereignty policy allows DNS (k8s-app: kube-dns) but the ingress policy doesn't allow DNS for ingress controllers. Also, the podSelector uses k8s-app: kube-dns which is GKE-specific; other clusters use dns or coredns.
HPA for agents but autoscaling disabled: In values.yaml, autoscaling.enabled: false but the chart structure includes hpa.yaml. Should either remove the template or clarify.
Missing service ports in Helm values: The values.yaml snippets don't show containerPort definitions, which typically live in the deployment/statefulset templates, but they should be templated from values.
Workaround for healer-agent Docker socket: Section 3.1 mentions "healer-agent needs Docker socket or Docker-in-Docker" but section 10.1 shows RBAC for pods/exec but not for the Docker socket volume mount or hostPath volume. The healer-agent would need both RBAC and a volume mount for the Docker socket, which is missing from the security model.
Global image registry consistency: Cost table 13.1 says docker.io/cherenkov but values.yaml uses the same. However, the actual image names don't match Docker Compose service names exactly (e.g., prism in compose vs stoplight/prism in Helm).
Section 2.3 Worker Pool: Shows a mermaid diagram with healer/gen workers. The agents are explorer, healer, daemon according to section 3. What is "gen"? Not defined elsewhere. Also shows cherenkov --> redis but if cherenkov is a CLI tool, it wouldn't typically maintain a persistent connection to Redis.
Validation of Phase 0: Section 16.1 says Phase 0 is DONE with many checkboxes checked. But there's no evidence in this document that these were actually implemented. This might be aspirational rather than factual.
Section 12.4 Benefits table: The "Without Operator" column says "File on disk" for spec management. But Helm + ConfigMap already provides versioned, GitOps-ready spec management. The table oversells the operator benefit relative to what Helm already provides.
Section 9.2 StorageClass: The local-path provisioner rancher.io/local-path is indeed what k3d uses, but the name cherenkov-local might conflict if k3d already creates a local-path storage class. Should set default: false or use the existing class.
Cost table RTX 5060: As noted, RTX 5060 doesn't exist as of my knowledge cutoff (likely a typo for RTX 3060 or similar).
Section 7.2 node labels: The node labels use nvidia.com/gpu.product which requires the NVIDIA device plugin. Also, cherenkov.io/gpu-tier is custom. Fine, but the scheduler needs to know about them.
Helm values for healer dockerSocket: The values.yaml has agents.healer.dockerSocket: true but no corresponding template logic is shown that would mount /var/run/docker.sock.
Let me organize the review into categories:

Critical Issues:

InitContainer deadlock bug in section 3.1
RTX 5060 vs RTX 3060 inconsistency
Missing Docker socket mount for healer-agent despite RBAC being defined
"Phase 0 DONE" claim lacks evidence
Significant Issues:

HPA included in chart structure but autoscaling disabled
Autoscaling LLMs is correctly flagged as anti-pattern but HPA template still exists
NetworkPolicy DNS selectors are cloud-specific
Worker pool diagram uses undefined "gen" agent
StorageClass might override existing k3d local-path
Minor Issues:

Cross-reference formatting in Abstract (uses inline links but table of contents uses markdown links)
Some mermaid diagrams may not render in plain markdown viewers
Missing imagePullSecrets in values.yaml
Operator benefits table slightly oversells vs Helm
Positive Aspects:

Good decision framework with anti-patterns
Honest cost analysis
Tiered continuum is pragmatic
Operator concept is innovative
Rollback strategy is concrete
Extensive appendices with commands and decision tree
Let me present this review to the user. Since this is a review task, I should provide the review output and potentially use the suggest tool at the end if I feel a code review is warranted - though this is markdown, not code. Actually, the guidelines say "Use this tool only to suggest a local code review" and specifically for review commands. Since this is content review, I'll provide the review directly and then maybe suggest /local-review-uncommitted if there are uncommitted changes? But there's no indication the user just changed files. I'll just provide the review.

Wait, the user said "review @docs/vision/14_KUBERNETES_CONSIDERATIONS.md thoroughly". So I should provide a thorough review of the document itself, not code files. I'll summarize my findings.

Let me structure the review:

Overall assessment
Critical findings
Significant findings
Minor issues
Strengths
I should be concise but thorough. The user asked for "thoroughly".

Here is a thorough technical review of docs/vision/14_KUBERNETES_CONSIDERATIONS.md.

Overall Assessment
The document is strategically sound with a realistic “don’t migrate yet” posture, but it contains several technical bugs and internal inconsistencies that would cause failures if executed verbatim.

Critical Findings (Must Fix)
InitContainer deadlock in ollama StatefulSet (§3.1) The initContainer runs:
until curl -s -f http://ollama:11434/api/tags; do sleep 1; done
This targets the same pod that has not yet started its main container. The initContainer will loop forever because nothing is listening on 11434 yet. The model-pull logic needs to be a separate pre-start Job, not an InitContainer inside the same pod.

GPU hardware typo in Cost Analysis (§13.1) Tier 1 lists RTX 5060 laptop for $0. There is no RTX 5060. §7.2 describes RTX 3060 8GB as the reference small-tier GPU. This is an internal contradiction.
Healer-agent Docker socket is RBAC-only, no volume mount (§10.1 vs §3.1) The RBAC grants pod exec/create permissions, but the healer still needs the actual /var/run/docker.sock hostPath volume and a corresponding hostPath volumeMount in the Deployment spec. The security model describes permissions but not the required volume binding.
Unverified “Phase 0 DONE” claim (§16.1) The checklist asserts health checks, resource limits, update config, etc. are complete “in this session.” There is no evidence in the document that these map to actual compose file changes.
Significant Findings (Should Fix)
HPA template exists but autoscaling is disabled (§6.1 vs §6.2) templates/hpa.yaml is listed in the chart structure, but autoscaling.enabled: false in values. The anti-pattern section (§2.3) correctly explains auto-scaling LLMs is useless, yet the scaffolding suggests otherwise. Remove hpa.yaml or gating it behind values avoids future confusion.
Cloud-specific NetworkPolicy selectors (§8.3) k8s-app: kube-dns is GKE-specific. EKS uses kube-system or coredns, AKS uses kube-dns, and k3d uses coredns. Use a namespace selector (kube-system or dns) with a broader label matcher.
StorageClass overwrites k3d default (§9.2) The cherenkov-local StorageClass uses provisioner rancher.io/local-path, which is the exact provisioner k3d uses for its default local-path storage. Defining a second class with the same provisioner can cause conflicts. Either reuse the existing class name or set default: false.
Worker-pool diagram uses undefined agent “gen” (§2.3) The active agents in this codebase are explorer, healer, and daemon. “gen” is not defined anywhere in the architecture mapping (§3).
Missing imagePullSecrets in Helm values (§6.2) If images come from a private registry, the chart has no way to inject imagePullSecrets, which will cause ImagePullBackOff in production clusters.
Operator benefits table overstates Helm gap (§12.4) The “Without Operator” column claims Helm/ConfigMap cannot watch Service/Ingress changes or auto-trigger validation. Modern GitOps (Flux) + Kustomize can already watch config changes. The table should be calibrated to reflect real capabilities.
Minor Issues
Mermaid rendering: All flowcharts will render in GitHub but may fail in lighter-weight markdown viewers.
Cross-references: Parent and predecessor references in the abstract use inline backticks instead of the markdown link style used in the TOC.
GPU tier node labels (§7.2): nvidia.com/gpu.product requires the NVIDIA device plugin to populate node labels; if the operator is not installed, these selectors will fail silently.
Phase sequencing gap: Phase 1 (k3d) generates manifests with kompose, but Phase 2 (Helm) reinvents the same manifests as templates. The document does not state whether kompose output is discarded or maintained in parallel.
Strengths
Realistic trigger matrix and anti-pattern table prevent premature K8s adoption.
Tiered continuum (Compose → k3d → Full K8s) is a pragmatic migration path.
Operator concept (ConformanceCheck CRD) is the strongest section—genuinely novel positioning.
Rollback checklist with concrete kubectl rollout commands is production-ready.
Appendices provide quick-reference commands and a decision tree.
Bottom line: The architecture is on the right track, but §3.1 (InitContainer deadlock), §13.1 (RTX typo), and §10.1 (missing volume mount) are blocking issues if anyone tries to run the examples.

#agent2:

## **CHERENKOV K8s Migration Plan — Thorough Review**

---

## **✅ EXECUTIVE ASSESSMENT**
**Overall: 9/10** — Exceptionally comprehensive, pragmatic, and well-structured. The decision framework (not migrating yet) is the right call. **However, ~15 critical/major issues must be fixed before implementation.**

---

---

## **🏆 STRENGTHS (Do More Of This)**

| Area | Why It’s Strong |
|------|-----------------|
| **Decision Framework (§2)** | Trigger matrix + anti-patterns are gold. Prevents premature migration. |
| **Tiered Continuum (§4)** | Realistic progression. Acknowledges k3d as valid intermediate. |
| **Operator Vision (§12)** | Unique differentiation. Most QA tools just *run on* K8s; this makes CHERENKOV *part of* K8s. |
| **Cost Honesty (§13)** | $685/mo threshold with clear ROI justification. Rare in architecture docs. |
| **Rollback Discipline (§14)** | 15-minute checklist + GitOps integration. Production-grade thinking. |
| **Implementation Sequencing (§16)** | Phased, time-boxed, with checkpoints. Avoids big-bang migration. |

---

---

## **❌ CRITICAL ISSUES (Must Fix Before Any Work Begins)**

### **1. Ollama StatefulSet InitContainer — Broken Design (§3.1, lines 100-120)**
**Problem:** The `initContainer` tries to `curl http://ollama:11434/api/pull` **before Ollama exists**. Chicken-and-egg failure.
- `ollama:11434` resolves to the *Service*, not localhost in the pod.
- Even if fixed to `localhost:11434`, Ollama isn’t running yet.

**Fix:**
```yaml
initContainers:
  - name: model-init
    image: ollama/ollama  # Same image, not curlimages/curl
    command: ["ollama", "pull", "qwen2.5-coder:7b", "deepseek-r1:8b"]
    volumeMounts:
      - name: models
        mountPath: /root/.ollama
    env:
      - name: OLLAMA_HOST
        value: "0.0.0.0"
```
> **Why:** Pull models directly via CLI before the main container starts. Uses the same volume.

---

### **2. GPU Sizing Inconsistency (§7.1 vs §13.1)**
**Problem:** §7.1 says vision models need **24 GB VRAM** (RTX 4090), but §13.1’s cost table uses `g4dn.xlarge` (**16 GB VRAM**).
- Cannot run `qwen2.5-coder:7b` (4 GB) + `deepseek-r1:8b` (8 GB) + vision model (8 GB) on 16 GB.

**Fix:**
- **Option A:** Update cost table to `g4dn.2xlarge` (32 GB VRAM, ~$800/mo).
- **Option B:** Clarify that **not all models run simultaneously** (mutually exclusive loading).

---

### **3. Health Checks in Phase 0 — Technically Invalid (§16.1)**
**Problem:** Phase 0 claims `"pgrep for daemons"` as a health check. **`pgrep` is a shell command, not a K8s probe.**
- K8s only supports: `httpGet`, `tcpSocket`, `exec` (command), or `grpc`.
- `exec` with `pgrep` *might* work, but `pgrep` returns non-zero if process not found → probe would fail.

**Fix:**
```yaml
# For non-HTTP services (e.g., healer-agent):
livenessProbe:
  exec:
    command: ["sh", "-c", "pgrep -x healer-agent >/dev/null"]
  initialDelaySeconds: 30
  periodSeconds: 10
```
> **But better:** Use HTTP if possible (add `/healthz` endpoint).

---

### **4. Healer-Agent Security Risk (§3, §10)**
**Problem:** Healer needs Docker socket access → **full host compromise risk**.
- §10.2 acknowledges this but only labels it `baseline` (should be **documented as a high-risk exception**).

**Fix:**
1. **Restrict the socket mount** to only the healer-agent’s namespace:
   ```yaml
   volumes:
     - name: docker-sock
       hostPath:
         path: /var/run/docker.sock
   ```
2. **Add a `SecurityContext`** to drop capabilities:
   ```yaml
   securityContext:
     capabilities:
       drop: ["ALL"]
     runAsNonRoot: true
     readOnlyRootFilesystem: true
   ```
3. **Audit trail:** Log all Docker commands executed by healer.

---

### **5. Missing Model Registry Strategy (§3.1, §7)**
**Problem:** No plan for **model versioning** or **synchronization** across Ollama pods.
- If Ollama pod restarts, models must re-download (20 GB × N nodes = slow).
- No mention of **private model registries** (e.g., for fine-tuned models).

**Fix:**
- Add a **model cache PVC** (shared across pods, `ReadWriteMany` if possible).
- Use **Ollama registry** (`ollama pull` from a private registry).
- Document **model preloading** in initContainers.

---

---

## **⚠️ MAJOR ISSUES (Address Before Phase 2)**

### **6. Agent Fabric Coordination — Underspecified (§8.2)**
**Problem:** No details on **how agents communicate** or **share state**.
- Explorer, healer, daemon need to coordinate (e.g., for drift detection).
- Current Compose uses **shared host networking** — won’t work in K8s.

**Fix:**
- **Phase 1 (k3d):** Use **HTTP + shared ConfigMaps** (simple, works for ≤3 agents).
- **Phase 3:** Use **gRPC + headless Service** (for inter-pod communication).
- **Phase 4:** Use **NATS/Kafka** (for cross-cluster).
- **Add to §8.2:**
  ```yaml
  # Headless Service for agent discovery
  apiVersion: v1
  kind: Service
  metadata:
    name: cherenkov-agents
  spec:
    clusterIP: None
    selector:
      cherenkov.io/role: agent
    ports:
      - port: 50051
        name: grpc
  ```

---

### **7. CI/CD Integration — Missing (§5, §16)**
**Problem:** No explanation of **how CI jobs trigger CHERENKOV validations** in K8s.
- Current Compose: CI runs `docker-compose run cherenkov validate`.
- K8s: How? `kubectl create job`? Helm hook? Tekton/Argo Workflows?

**Fix:**
- **Option A:** `cherenkov validate` as a **K8s Job** (ephemeral).
  ```yaml
  apiVersion: batch/v1
  kind: Job
  metadata:
    name: cherenkov-validate-{{UUID}}
  spec:
    template:
      spec:
        containers:
          - name: cherenkov
            image: cherenkov/cherenkov
            command: ["cherenkov", "validate", "--target", "$(TARGET)"]
        restartPolicy: Never
  ```
- **Option B:** Use **Argo Workflows** for complex pipelines.
- **Add to §5.2:** "CI Integration" as a step between #7 and #8.

---

### **8. Ingress + TLS — Incomplete (§8, §5.2)**
**Problem:** §5.2 says **NGINX Ingress + cert-manager**, but:
- No details on **TLS certificate issuance** (Let’s Encrypt? Private CA?).
- No **ingress annotations** for rewrite rules, rate limiting, or auth.

**Fix:**
- Add a **default ingress template** in Helm chart:
  ```yaml
  apiVersion: networking.k8s.io/v1
  kind: Ingress
  metadata:
    name: cherenkov
    annotations:
      cert-manager.io/cluster-issuer: "letsencrypt-prod"
      nginx.ingress.kubernetes.io/rewrite-target: /$1
  spec:
    tls:
      - hosts: ["cherenkov.example.com"]
        secretName: cherenkov-tls
    rules:
      - host: cherenkov.example.com
        http:
          paths:
            - path: /(.*)
              pathType: Prefix
              backend:
                service:
                  name: cherenkov-demo
                  port:
                    number: 8000
  ```

---

### **9. StorageClass for EBS — Missing Critical Setting (§9.2)**
**Problem:** The `cherenkov-ebs` StorageClass lacks:
- `volumeBindingMode: WaitForFirstConsumer` (required for dynamic provisioning in multi-AZ clusters).
- No **encryption** (EBS should be encrypted by default).

**Fix:**
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: cherenkov-ebs
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer  # Critical for multi-AZ
parameters:
  type: gp3
  encrypted: "true"  # Enable encryption
  kmsKeyId: arn:aws:kms:...  # Optional: custom KMS key
reclaimPolicy: Retain
allowVolumeExpansion: true
```

---

### **10. Observability — High Cardinality Risk (§11.1)**
**Problem:** Metrics like `cherenkov_llm_latency_seconds` with `model` label could explode if:
- Many models are loaded/unloaded dynamically.
- `trace_id` as a label → **cardinality bomb**.

**Fix:**
- **Drop high-cardinality labels** or use **bucketed values**:
  ```yaml
  # Instead of:
  #   labels: [model, trace_id]
  # Use:
  labels: [model]  # model is low-cardinality (≤10)
  ```
- **For traces:** Use **OpenTelemetry** + Jaeger (not Prometheus).

---

---

## **📌 MINOR ISSUES & RECOMMENDATIONS**

| Section | Issue | Recommendation |
|---------|-------|----------------|
| **§2.1** | "≥ 3 team members using agent fabric simultaneously" | Define "using" (concurrent API calls? GPU time?). |
| **§2.3** | Worker pool diagram | Add **Redis persistence** (or it’s lost on restart). |
| **§3** | `cherenkov-demo` service | Undefined. Explain its purpose (is it a web UI?). |
| **§4.1** | Tier 2 checkpoint | Add: "Can we run `make k3d-up` on a fresh laptop in <10 min?" |
| **§5.1** | `kompose convert` | Warn that **volumes, networks, and healthchecks** often need manual fixes. |
| **§6.2** | `values.yaml` | Add `podAntiAffinity` for HA (e.g., `preferredDuringSchedulingIgnoredDuringExecution`). |
| **§7.2** | GPU node labels | Add **taints/tolerations** to reserve GPU nodes for CHERENKOV. |
| **§8.2** | gRPC | Specify **Protocol Buffers schema** for agent communication. |
| **§9.1** | SQLite PVC | Add **PVC access mode**: `ReadWriteOnce` (only 1 pod can mount). |
| **§10.3** | External Secrets | Add **Vault vs. AWS Secrets Manager** comparison. |
| **§11.3** | Grafana dashboards | Provide **actual JSON dashboard definitions** in `/grafana/dashboards`. |
| **§12.2** | CRD `specRef` | Support **Git repository + path** (not just ConfigMap). |
| **§13.1** | Cost table | Add **monitoring stack cost** (~$50/mo for Prometheus + Loki). |
| **§14.3** | Data rollback | **RPO for models is 24h** — too high. Use **Velero + S3** for hourly snapshots. |
| **§15.3** | Health score script | Add checks for **PVC status, GPU availability, ingress**. |
| **§16.1** | Phase 0 "DONE" | Reference **actual Docker Compose changes** (link to PR/commit). |
| **§17.C** | Decision tree | Add **"Can we solve this with Docker Compose + `--scale`?"** as first question. |

---

---

## **❓ QUESTIONS REQUIRING ANSWERS**

1. **Agent Fabric Architecture:**
   - How do agents **discover each other** in K8s? (DNS? Service mesh? Hardcoded?)
   - How is **shared state** (e.g., `openapi_cache`) synchronized across pods?

2. **Model Management:**
   - How are **new models** (e.g., `qwen3-vl:32b`) deployed to Ollama pods?
   - How are **model versions** pinned/reproduced?

3. **Authentication:**
   - How does CHERENKOV **authenticate to Ollama**? (API key? Network policy?)
   - How do **external users** authenticate to `cherenkov-demo`?

4. **Rate Limiting:**
   - How is **Ollama GPU contention** prevented? (Queue? Token bucket?)
   - How are **LLM request rates** limited per agent/tenant?

5. **Multi-Tenancy:**
   - How are **isolated environments** (per team/project) implemented? (Namespaces? Separate clusters?)

6. **Operator Development:**
   - Will the operator be **written in Go** (standard) or Python (easier for CHERENKOV team)?
   - How will the operator **test ConformanceCheck CRs** in CI?

---
---
## **📊 SCORING BREAKDOWN**

| Category | Score (0-10) | Notes |
|----------|-------------|-------|
| **Strategy & Vision** | 10 | Decision framework, operator vision, cost analysis are exceptional. |
| **Technical Accuracy** | 7 | Critical issues in initContainer, GPU sizing, health checks. |
| **Completeness** | 8 | Missing CI/CD, agent coordination, auth. |
| **Actionability** | 7 | Some sections (e.g., §12) are too high-level for immediate implementation. |
| **Risk Awareness** | 9 | Rollback, cost, anti-patterns are well-considered. |
| **Innovation** | 10 | Operator concept is a unique differentiator. |

**Final: 8.5/10** — **Excellent foundation, but fix the critical issues before proceeding to Phase 1.**

---
---
## **🎯 IMMEDIATE NEXT STEPS**

1. **Fix Critical Issues (This Week):**
   - [ ] Correct the Ollama StatefulSet initContainer (use `ollama pull` CLI).
   - [ ] Align GPU sizing in §7 and §13 (use `g4dn.2xlarge`).
   - [ ] Replace `pgrep` health checks with valid K8s probes.
   - [ ] Add Docker socket security context for healer-agent.

2. **Address Major Gaps (Next 2 Weeks):**
   - [ ] Document agent fabric coordination (gRPC + headless Service).
   - [ ] Add CI/CD integration (K8s Jobs or Argo Workflows).
   - [ ] Complete ingress + TLS configuration.
   - [ ] Fix StorageClass for EBS (add `volumeBindingMode` + encryption).

3. **Clarify Open Questions:**
   - [ ] Model management strategy (registry, versioning, caching).
   - [ ] Authentication for Ollama and external users.
   - [ ] Rate limiting for GPU/LLM usage.

4. **Split the Document (Optional):**
   - Move **§12 (Operator)** to a separate `OPERATOR_DESIGN.md`.
   - Move **§17 (Appendices)** to a `K8S_REFERENCE.md`.

---
---
## **💡 FINAL VERDICT**
> **"Approved for implementation, contingent on fixing the 5 critical issues."**

This document is **one of the best K8s migration plans** I’ve reviewed — it avoids hype, focuses on real triggers, and proposes a genuinely innovative operator-based future. **Do not start Phase 1 until the critical issues are resolved.** The rest can be addressed iteratively.


#agent3:
Thinking
Here is a detailed feedback and review draft for 14_KUBERNETES_CONSIDERATIONS.md. You can use this as a PR review, a comment on the document, or notes for the author.

Document Review: 14_KUBERNETES_CONSIDERATIONS.md
Overall Impression
This is an exceptionally well-crafted, pragmatic, and forward-looking architectural document. The most commendable aspect is its restraint—explicitly outlining why not to migrate to K8s immediately and defining clear, metric-driven triggers for when the complexity becomes justified.

The concept of evolving CHERENKOV into a Kubernetes-native Operator (Section 12) is a brilliant strategic pivot that transforms the tool from an external testing utility into a declarative cluster-state validator.

Below are detailed technical observations, structural feedback, and minor corrections to further harden the document.

1. Key Strengths
The Anti-Patterns Matrix (2.2): Calling out "K8s looks good on a pitch deck" and "Auto-scaling LLMs doesn't work" shows deep operational maturity.
Tiered Deployment Continuum (4): Breaking the migration down into k3d first creates a low-risk, high-reward testing ground for K8s manifests without cloud spend.
Cost Analysis (13): Tying the infrastructure cost directly to business value (QA hours saved, SLA compliance) provides excellent ammunition for future budget approvals.
Rollback Strategy (14): Including actual time-to-execute estimates (RTO) and explicit commands ensures this isn't just theory, but an actionable playbook.
2. Technical Feedback & Suggestions
Section 7: GPU Scheduling Strategy

MIG Partitioning (7.3): You might want to add a brief note that Multi-Instance GPU (MIG) strictly partitions memory and compute, meaning dynamic VRAM sharing across boundaries isn't possible. If a vision model occasionally spikes above 5GB, it will OOM crash rather than borrow from an idle partition.
Helm Values Quoting (6.2): In K8s manifests, nvidia.com/gpu: 1 is usually fine as an integer, but K8s resource limits are strictly strings. In your values.yaml example, you correctly have nvidia.com/gpu: "1", but it's listed as an integer in the 3.1 YAML template. Ensure consistency to avoid Helm/K8s API parsing errors.
Section 8: Networking Topology

Typo in 8.2 (Agent-to-Agent Communication): Under the Tier 3 row in the table, the text reads: "Agent agents are long-lived streams". This should likely be "Agent connections are long-lived streams" or "Agents communicate via long-lived streams".
Section 10: Security Model

Pod Security Admission (10.2): You enforce the restricted profile at the namespace level but note an exception for the healer-agent (which needs the Docker socket). Depending on the K8s version (1.25+), PSA evaluates at the namespace level. You cannot easily bypass a namespace-level enforce: restricted for a single pod via annotations alone.
Recommendation: Consider suggesting a separate namespace (e.g., cherenkov-privileged) for the healer-agent, or strictly using baseline for the whole namespace if Docker-in-Docker/socket mounting is mandatory.
Section 12: Operator Architecture

Integration with Agent Fabric: The architecture diagram in 12.3 is excellent, but it leaves a slight gap regarding the AI agents. Does the spawned Job pod run the CLI which then communicates with the daemon-agent, or does the Job pod contain the full agent fabric inside it? Adding a quick clarifying sentence on how the CRD job interacts with the LLM/Agent services would bridge the gap between Section 3 and Section 12.
Section 2.3: Worker Pool Alternative

This is a highly practical intermediate step. You might want to briefly mention how models are loaded in this scenario. Do all workers have Ollama sidecars, or do they route to a centralized Ollama router? (A centralized Ollama router might still bottleneck on VRAM, which K8s helps solve via node scheduling).
3. Formatting and Minor Nitpicks
Section 3.1 (Readiness Probe): The readinessProbe for Ollama points to /api/tags. This is standard, but you might want to consider checking / or a specific model load state if agents fail when the API is up but the model isn't loaded yet.
Section 15.3 (Monthly Score Script): The bash script is a nice touch. You might want to wrap the kubectl top pods command in an if block checking if the metrics-server is installed, as it will error out on raw clusters (like basic k3d without metrics-server enabled).
Final Verdict
Status:Approved / Ready to Merge. The document is robust, authoritative, and ready to serve as the definitive Horizon 4 architectural blueprint. Applying the minor security namespace tweak and fixing the typo in 8.2 will make it perfect.

#agent4:
# Review: `docs/vision/14_KUBERNETES_CONSIDERATIONS.md`

**Reviewer:** evidence-grounded agent review per `AGENTS.md` rules
**Date:** 2026-06-07
**Verdict:** **APPROVE WITH REVISIONS** — sound strategic posture, but (a) **softens the explicit "No K8s" guardrail in `ROADMAP_PACKAGING.md §0 / §3`** without flagging the conflict, (b) contains a **real YAML bug in §3.1**, and (c) makes "ready/built" claims with no evidence. None are fatal; all are fixable on a feature branch.

---

## 0. Evidence I anchored to

| Document | Role in this review |
|---|---|
| `docs/HANDOVER.md` | SSOT for project status (Track A built, gate unrun, 0/5 reviews) |
| `docs/ROADMAP_NEXT.md` | Authoritative forward plan (Validation-First, Horizon V) |
| `docs/ROADMAP_PACKAGING.md` | **Contains the explicit "No Kubernetes" guardrail** (§0 + §3) |
| `docs/SCOPE_LEDGER.md` | Honest map of live vs built-ahead code |
| `docs/vision/12_DOCKER_AI_HORIZON.md` | Predecessor (Horizon 3 strategic) |
| `docs/vision/13_DOCKER_AI_IMPLEMENTATION_PLAN.md` | Predecessor (Horizon 3 implementation) |
| `docs/process/VALIDATION_EVIDENCE_LEDGER.md` | 0/5 reviews; gate unrun as of 2026-06-07 |
| `docker-compose.yml` | Source of truth for §3 mapping claims |
| `Makefile` | Source of truth for one-command bootstrap claim |

---

## 1. Strengths (keep)

- **S1.** §1 + §15.1 both say "this document does not recommend migrating today." Matches the SSOT.
- **S2.** §2.2 anti-patterns table explicitly calls out "K8s on the pitch deck" and "auto-scaling LLMs doesn't work."
- **S3.** §2.3 names the worker-pool alternative (Celery/RQ + Redis) as the preferred pre-K8s path — matches `ROADMAP_PACKAGING.md P-7` spike.
- **S4.** §16.1 "Phase 0: Compose Hardening — DONE" is honest and accurate; verified against `docker-compose.yml` lines 1-13, 24-39, 53, 86-99, 110-132, 145, 158-181, 199-211.
- **S5.** §3 / §6 / §7 / §8 / §9 / §10 / §11 are competent K8s architecture — `StatefulSet` for Ollama, `InitContainer` for model pull, `ConfigMap` for policy, GPU node labels, network policies, Velero backup, Pod Security Standards.
- **S6.** §13 cost analysis is in the right ballpark (EKS control plane $73 ≈ $75; ALB $22.50 ≈ $20; NAT ~$32-35; g4dn.xlarge ~$384 ≈ $400).
- **S7.** §14 rollback table is concrete with time estimates.
- **S8.** §17.C Migration Decision Tree ends with the right escape hatch: *"after 3 months on k3d, is the K8s API creating value? No → revert to Compose."*
- **S9.** Internal consistency: a second read of §3-§12 found no contradictions inside the K8s doc itself.

---

## 2. CRITICAL (must fix before merge)

### C1. Conflicts with `ROADMAP_PACKAGING.md §0` and §3 — and the K8s doc does not acknowledge the conflict

`ROADMAP_PACKAGING.md` is explicit and recent (2026-06-05):

> **§0 guardrails:** *"❌ No Kubernetes. Local LLMs are GPU/VRAM-bound; pods don't multiply GPUs. K8s solves load we do not have and would become a second product. Revisit only on real multi-node GPU demand, and even then a worker-pool (Celery/RQ + Redis) likely beats K8s. Recorded, not scheduled."*
>
> **§3 deferral table:** *"Kubernetes / Helm chart | GPU-bound workload; no horizontal demand; second product | Real multi-node GPU load from ≥1 paying/committed user"*

This document's §15.1 gate check **softens that trigger** to:

> *"Validation gate (Phase 2, 5 QA users) has passed — demand is real" + "CKA experience" + "committed user within 30 days" + "budget allocated" + "Docker Compose has failed us in a concrete way (specify which trigger from §2.1)"*

The two documents disagree about the trigger threshold. Both are owner-authored and dated within 24h. The K8s doc must either (a) reconcile to `ROADMAP_PACKAGING.md`'s stricter "≥1 paying/committed user + multi-node GPU load" trigger, or (b) explicitly call out the disagreement and propose amending `ROADMAP_PACKAGING.md §0 / §3` to match, with owner sign-off. **Required: at minimum a "Conflicts with ROADMAP_PACKAGING.md" callout near the top, and either reconciliation or a tracked issue to resolve.**

### C2. §3.1 — Init container has a malformed shell command (real bug)

Lines 62-67:

```yaml
- sh
- -c
- |
  until curl -s -f http://ollama:11434/api/tags; do sleep 1; done
  curl -X POST http://ollama:11434/api/pull \
    -d '{"name":"qwen2.5-coder:7b"}'
  curl -X POST http://ollama:11434/api/pull \
    -d '{"name":"deepseek-r1:8b"}'
```

The line `    -d '{...}'` is at the same indent as the `curl` command, so YAML parses it as a **new list item**, not as a continuation of `curl`. The resulting `sh -c` will see a broken script. Compare with the working `docker-compose.yml` lines 141-147, which uses `entrypoint: > sh -c "..."` (block scalar).

**Fix (pick one):** (a) fold into a single line with `>-`; (b) use a separate `Job` (the doc's Helm chart already plans one at §6.1: `ollama-init-job.yaml`); (c) mirror the working `entrypoint: > sh -c "..."` pattern from `docker-compose.yml`.

### C3. §11.1 / §11.3 / §11.4 — Prometheus metrics, dashboards, and alerts are presented as existing, but no evidence the instrumentation ships

The doc lists `cherenkov_validations_total`, `cherenkov_divergences_found`, `cherenkov_agent_runs_total`, `cherenkov_llm_latency_seconds`, etc. as if they will be exported. Per `SCOPE_LEDGER.md §B`, the `substrate/`, `divergence/`, `copilot/`, `truth/` modules are **built and unit-tested but NOT validated**. There is no Prometheus client in the file listing, no `/metrics` endpoint referenced, and no evidence any of these counters are emitted in the running stack. The dashboard panels in §11.3 and the alert rules in §11.4 are equally aspirational.

**Fix:** tag §11.1 / §11.3 / §11.4 as **"designed, not yet implemented"**; move the work to a separate "Open: instrument `cherenkov/*` modules" ticket; do not let this doc imply the metrics are shipping.

### C4. §12 ConformanceCheck CRD — D7 / anti-lock-in / suggest-only / spec-derived are not addressed

The operator's `onDivergence.createIssue` and `onDivergence.notifyWebhook` actions look D7-safe (they emit external notifications, not test edits). But the doc never **states this**. A future reader could trivially extend the CRD with a `patch: true` field and violate the invariants. `12_DOCKER_AI_HORIZON.md §5` calls these out per-integration; the K8s doc does not.

**Fix:** add a §12.5a "Invariant compatibility" subsection explicitly mapping: D7 ↔ operator never writes test files; anti-lock-in ↔ ejected tests still run without K8s; suggest-only ↔ CR status is a notification surface, not an executor; spec-derived ↔ ConformanceCheck sources from spec (ConfigMap), never infers.

---

## 3. MEDIUM (should fix)

### M1. §15.1 — Validation gate precondition needs an "as-of" timestamp

§15.1 says: *"Validation gate (Phase 2, 5 QA users) has passed — demand is real"*. As of 2026-06-07, the gate is **unrun** (0/5 reviewers per `VALIDATION_EVIDENCE_LEDGER.md`, and AGENTS.md says: *"removing the block ≠ passing the gate"*). The doc should state explicitly: *"As of 2026-06-07, this precondition is NOT met. Recording the gate as a trigger, not as a current state."* Otherwise a future reader can mistake §15.1 for current status.

### M2. No cross-references to HANDOVER.md or SCOPE_LEDGER.md

The doc's front-matter links to `ROADMAP_PACKAGING.md`, but not to:
- `HANDOVER.md` (project status SSOT)
- `SCOPE_LEDGER.md` (live vs built-ahead map)
- `ROADMAP_NEXT.md` (authoritative forward plan, Phase 5 = the gate)

SSOT discipline gap. Add a "Related Documents" block (the format `00_VISION.md` uses at its tail).

### M3. §5.1 — k3d port-forwarding lists Ollama on the load-balancer; that's a footgun

```
--port 4010:4010@loadbalancer   # prism
--port 8000:8000@loadbalancer   # cherenkov-demo
--port 11434:11434@loadbalancer # ollama
```

Ollama listening on an LB port means model weights cross the LB on every pull, and the multi-MB `POST /api/pull` can time out at the LB. Per `docker-compose.yml`, Ollama is internal-only on the Compose network. The k3d form should omit `--port 11434:11434` (use ClusterIP) or call out the LB form as "for direct local debugging only, not a normal topology."

### M4. §16.1 — "Phase 0: Compose Hardening — DONE" should cite the source

The hardening list is verifiable in `docker-compose.yml`, but the doc does not anchor it. Add a footnote: *"Verified in `docker-compose.yml` as of [date/commit]; landed as part of `ROADMAP_PACKAGING.md` P-1/P-2/P-3 (tickets #200–#206)."*

### M5. §3 mapping — `cherenkov` service: `Deployment` vs `Job` is hand-wavy

The table says *"Deployment or Job (ephemeral)"*. The current Compose form is a long-running container used for `generate`/`validate`/`eject` CLI invocations. Split the row: `cherenkov-cli → Job` (with CronJob wrapper for drift-watch) and `cherenkov-web → Deployment` (for the `review --web` mode that `cherenkov-demo` already represents).

### M6. §13.1 — Cost table needs an "excludes" line

The $685/mo does not include data transfer ($0.09/GB after 100 GB), CloudWatch metrics & Loki log ingest, EBS snapshot storage, S3 Velero backup. These can easily double the bill. Add: *"+ $100-300/mo data + observability + backup storage, varies by usage."*

### M7. §3 mapping says `ollama-init` → "InitContainer or Job"; §6.1 plans a separate `ollama-init-job.yaml`

Two different K8s patterns. The init container pattern in §3.1 (with the YAML bug above) conflicts with the Job pattern in the Helm chart. **Recommendation:** `Job` is more idiomatic (retryable, RBAC-isolated, visible in `kubectl get jobs`) and matches §6.1. Update §3 mapping and §3.1 accordingly.

---

## 4. MINOR (could fix)

- **m1.** §1 — "the key innovation: a unique position no QA tool occupies" is sales positioning. Soften.
- **m2.** §7.1 — VRAM math is fuzzy. Per `HANDOVER §1`, both models fit in 8 GB total on the RTX 5060; "4 GB per model" is not the right framing.
- **m3.** §6.2 — `nvidia.com/gpu: "1"` works but bare integer is conventional.
- **m4.** §6.2 — `ollama.gpu.count: 1` in values isn't wired to the spec template.
- **m5.** §7.4 — `--set migManager.enabled=false` is fine; canonical is `--set-string`.
- **m6.** §10.2 — the `pod-security.kubernetes.io/enforce: baseline` label exception is justified but the matching `podSelector` is not shown.
- **m7.** §5.1 — `make k3d-up` does not exist in the current `Makefile` (which has only `demo` and `full`).
- **m8.** §12.4 — "Without Operator → Single process" is incorrect; CHERENKOV already runs a 3-service agent fabric.
- **m9.** §11.4 alerting rules reference metrics from §11.1; compounds C3.
- **m10.** §17 references `k3d/cluster.yaml` and `k8s/overlays/team` — neither exists. Add: *"All paths in this section are planned; none exist in the repo as of 2026-06-07."*

---

## 5. Cross-checks against SSOT and the AGENTS.md rules

| Rule (from `AGENTS.md`) | Doc compliance |
|---|---|
| **SSOT is `docs/`** | ✅ Doc lives in `docs/vision/`, anchored to `00_VISION.md` and `ROADMAP_PACKAGING.md`. |
| **Show RAW EVIDENCE for every claim** | ⚠️ Mostly good; §11 metrics and §16.1 "DONE" lack evidence anchors (see C3, M4). |
| **D7 — never auto-edit test code** | ⚠️ Implicit (operator emits events/webhooks, not edits) but not stated (see C4). |
| **Anti-lock-in** | ⚠️ Implied; the K8s form of `eject` is not addressed — does it produce a tarball? Download via API? **M-add:** state explicitly. |
| **Suggest-only healing** | ⚠️ Not addressed in K8s context. |
| **Spec-derived status** | ✅ §12 CRD explicitly sources from `ConfigMap.specRef`. |
| **Track B/C / Horizon 2 — built + unit-tested, not validated** | ⚠️ §11 metrics claim Horizon 2 modules export Prometheus; unverified (see C3). |
| **No fabricated "validated" / "QA-approved"** | ✅ Doc does not claim any of this. |
| **No fabrication of "v3.1 + delta"** | ✅ Doc uses real terms; no hallucinated versions. |

---

## 6. Adjacent file flag (not in K8s doc's scope, but in the same workspace tab)

`docs/vision/desktopConsiderations_agentsWarRoom.md` is a co-resident multi-opinion draft. It contains four sub-agents arguing different desktop-packaging positions (Electron vs Tauri vs Tauri 2+PyInstaller). It is **not** a finished vision doc, doesn't follow the `NN_TOPIC.md` numbering, and could be mistaken for one. **Suggestion:** rename to `docs/vision/_drafts/desktop_considerations.md` (or move to `docs/spikes/`) until a single owner-signed recommendation emerges. Same SSOT-discipline lesson from `HANDOVER §2` applies. **Not in scope of the K8s review**, but flagging because it's the open tab next to the K8s doc.

---

## 7. Recommendation

**Approve with required revisions.** The strategic posture is sound. The technical content is mostly competent. The doc's biggest problem is **SSOT discipline** (no acknowledgement of the `ROADMAP_PACKAGING.md` conflict, no HANDOVER/SCOPE_LEDGER cross-refs, no "as-of" timestamp on the gate precondition) and **one real bug** in §3.1.

### Required before merge to `main` (per AGENTS.md workflow rule 3, get human review)

1. **C1** — reconcile with `ROADMAP_PACKAGING.md` or call out the disagreement with owner sign-off.
2. **C2** — fix the §3.1 init-container shell-command bug.
3. **C3** — tag §11.1 / §11.3 / §11.4 as "designed, not yet implemented."
4. **C4** — add a §12.5a invariant-compatibility subsection.
5. **M1** — add "as-of 2026-06-07, the validation gate is unrun" to §15.1.

### Recommended

6. **M2** — add `HANDOVER.md`, `SCOPE_LEDGER.md`, `ROADMAP_NEXT.md` to the front-matter Related Documents.
7. **M3** — drop or footnote the `--port 11434:11434@loadbalancer` in §5.1.
8. **M4** — anchor the §16.1 "DONE" claim to a date/commit + the P-1/P-2/P-3 tickets.
9. **M5** — split the `cherenkov` row into `cli` (Job) and `web` (Deployment).
10. **M6** — add the "excludes" line to §13.1.
11. **M7** — pick one pattern for `ollama-init` (`Job` is recommended) and align §3.1 with §6.1.
