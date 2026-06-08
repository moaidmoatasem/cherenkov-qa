# CHERENKOV — Packaging & Distribution Epic ("Friction Kill: one-command run")

**Date:** 2026-06-05 · **Status:** Agent-ready tickets. Subordinate to
[ROADMAP_NEXT.md](ROADMAP_NEXT.md) (Validation-First, authoritative) and
[HANDOVER.md](HANDOVER.md) (honest state). This epic implements **Phase 1 — Friction Kill**
of the forward roadmap via containerized distribution. It is **not** a scaling project.

---

## 0. Decision & guardrails (read first)

**Why this epic exists.** The single open blocker is the validation gate: 5 real QA people must
run the golden path and leave attributable evidence. The biggest barriers to that today are
*install friction* (GPU + Ollama + `npm install` + Python env + Docker-for-Prism) and
*"works on my machine."* A one-command container collapses that friction and makes the gate
demo **reproducible** — which is the whole point.

**What this epic IS:** packaging the *existing* golden path (init → generate → validate → review →
eject) into a `docker compose up`-grade experience, plus a no-GPU demo mode.

**What this epic is NOT (explicit guardrails):**
- ❌ **No Kubernetes.** Local LLMs are GPU/VRAM-bound; pods don't multiply GPUs. K8s solves load
  we do not have and would become a second product. Revisit only on real multi-node GPU demand,
  and even then a worker-pool (Celery/RQ + Redis) likely beats K8s. Recorded, not scheduled.

  **✅ OVERRIDDEN by Phase 0 operator spike** — owner: @moaid, date: 2026-06-07, rationale: GitOps + multi-tenant demand + K8s-native conformance validator innovation. This spike is scoped to k3d (single-node, no multi-node complexity) and does not replace the Compose-based validation gate. Track A continues unchanged. See [Phase 0 Plan](../k8s/README.md) and [K8s Vision](vision/14_KUBERNETES_CONSIDERATIONS.md).
- ❌ **No new product scope.** No new backend epochs, no un-quarantining Track B/C. This wires
  *existing* surfaces into a container.
- ❌ **No autoscaling / parallel-agent fan-out infra.** Out of altitude until post-gate.

**Evidence rule (inherited from HANDOVER §2).** Every ticket below exits on **raw evidence**
(terminal log + `docker images` / `docker compose ps` output + a screen recording where a human
path is involved). A summary is not a pass.

**Sequencing.** P0 (golden path real-data wiring, [ROADMAP_NEXT.md](ROADMAP_NEXT.md) Phase 0) is a
hard prerequisite for the human-facing parts here. Tickets P-1/P-2/P-3 (the engine image, compose,
demo mode) can start in parallel with Phase 0 since they package CLI surfaces that already exist.

---

## 1. Target experience (the "definition of done" for the epic)

```
# Full mode (has GPU + wants real LLM generation):
git clone … && cd cherenkov-qa
docker compose up                 # brings up ollama + cherenkov + review UI
# → browser opens the Findings queue on the bundled petstore target

# Demo mode (laptop / Mac, no GPU):
docker compose --profile demo up  # uses cached run, no Ollama, no model pull
# → reviewer sees real findings in < 2 min, zero local toolchain
```

Acceptance for the epic as a whole: a fresh user on a clean machine with **only Docker installed**
reaches the web Findings queue with real data in **< 10 min (full)** / **< 2 min (demo)**, and can
`eject` standalone Playwright out of the container to their host. Recorded end-to-end.

---

## 2. Tickets (agent-ready)

Each ticket: scope, files, acceptance (raw-evidence), dependencies, out-of-scope. Label all
`agent-ready`, `packaging`. **Filed as GitHub issues 2026-06-05:**
[#200](https://github.com/moaidmoatasem/cherenkov-qa/issues/200) (P-1),
[#201](https://github.com/moaidmoatasem/cherenkov-qa/issues/201) (P-2),
[#202](https://github.com/moaidmoatasem/cherenkov-qa/issues/202) (P-3),
[#203](https://github.com/moaidmoatasem/cherenkov-qa/issues/203) (P-4),
[#204](https://github.com/moaidmoatasem/cherenkov-qa/issues/204) (P-5),
[#205](https://github.com/moaidmoatasem/cherenkov-qa/issues/205) (P-6),
[#206](https://github.com/moaidmoatasem/cherenkov-qa/issues/206) (P-7 spike).

---

### P-1 — `Dockerfile` for the CHERENKOV engine image
**Label:** `agent-ready` `packaging`
**Depends on:** none (packages existing Track A CLI)

**Scope.** A multi-stage `Dockerfile` that produces a runnable `cherenkov` CLI image:
- Python 3.10+ base, install `requirements.txt`.
- Node toolchain for `openapi-typescript` + Playwright (browsers via `playwright install --with-deps`).
- Docker-in-nothing: Prism runs as its *own* compose service (P-2), not nested here.
- `ENTRYPOINT ["python", "cherenkov.py"]` so `docker run cherenkov <args>` works.
- `.dockerignore` excluding `track-b-c-deferred/`, `node_modules`, `.git`, caches.

**Acceptance (raw evidence):**
- `docker build -t cherenkov:dev .` succeeds; paste the final build log lines + `docker images`.
- `docker run --rm cherenkov:dev doctor` runs and prints the preflight report.
- `docker run --rm cherenkov:dev --help` lists init/generate/validate/review/eject.
- Image size reported (target < 2 GB; note if Playwright browsers blow past it).

**Out of scope.** GPU passthrough (that's the Ollama service, P-3), the web UI build (P-4).

---

### P-2 — `docker-compose.yml`: engine + Prism wiring
**Label:** `agent-ready` `packaging`
**Depends on:** P-1

**Scope.** Compose file wiring the engine to the Prism mock server it already expects
(`cherenkov/execution/prism_mock.py`):
- `cherenkov` service (built from P-1), mounts a host workdir for output/tests so `eject` lands on host.
- `prism` service (`stoplight/prism` image) serving the bundled petstore spec.
- A named volume for the openapi-fetch / prefix cache.
- `cherenkov generate` inside compose talks to the `prism` service by hostname (not localhost).

**Acceptance (raw evidence):**
- `docker compose up` brings both services healthy; paste `docker compose ps`.
- `docker compose run cherenkov generate` produces tests against the petstore via the `prism` service;
  paste terminal output + the generated test file path on the host mount.
- Confirm ejected tests on the host run with `npx playwright test` *outside* the container (anti-lock-in invariant).

**Out of scope.** Ollama (P-3), the review UI (P-4).

---

### P-3 — Ollama service + GPU profile (full mode)
**Label:** `agent-ready` `packaging`
**Depends on:** P-2

**Scope.** Add an `ollama` service to compose, gated behind a `full` profile:
- `ollama/ollama` image with the NVIDIA runtime (`deploy.resources.reservations.devices` GPU).
- An init step (entrypoint script or one-shot service) that pulls `qwen2.5-coder:7b` and
  `deepseek-r1:8b` on first run; cache to a named volume so re-runs are instant.
- `cherenkov` service points `OLLAMA_HOST` at the `ollama` service.
- Document the host prerequisite: NVIDIA Container Toolkit. Fail loudly with an actionable message
  if GPU isn't visible (don't silently fall back to CPU and hang on an 8B model).

**Acceptance (raw evidence):**
- On the RTX 5060 host: `docker compose --profile full up`, model pull completes, paste the
  Ollama log showing layers on GPU + a warm generation timing.
- A full `generate` run through the container hits the model and produces a reviewed test; paste log.

**Out of scope.** CPU-only inference (covered by demo mode P-5, which avoids the model entirely).

---

### P-4 — Bundle the web review UI into the image (no `npm install` for users)
**Label:** `agent-ready` `packaging`
**Depends on:** ROADMAP_NEXT Phase 0 (real-data API wiring: `cherenkov/web/api.py`)

**Scope.** Make `cherenkov review` serve a **prebuilt** dashboard from inside the container:
- Build the React/Vite UI in a Dockerfile stage; copy the static `dist/` into the engine image.
- `cherenkov review --web` launches the FastAPI app (`cherenkov/web/api.py`, real `HitlQueue`) and
  serves `dist/` — no Node, no `npm install` at user runtime.
- Expose the port in compose; print the URL on startup.

**Acceptance (raw evidence):**
- `docker compose --profile full up` → open the printed URL → Findings queue renders **real**
  findings from a prior `validate` run (not mock data). Screen recording.
- Approve / reject / "Why?" round-trip hits the real API; paste the API log lines for one action.

**Out of scope.** New UI features. This packages the Phase-0-wired UI; it does not build new screens.

**Blocker note.** Per [ROADMAP_NEXT.md §9a](ROADMAP_NEXT.md) there is untracked WIP for
`cherenkov/web/api.py` + `cherenkov/web/divergences.py`. Land that via its own reviewed PR before
this ticket; do not vendor mock data into the image.

---

### P-5 — No-Ollama **demo mode** (the laptop/Mac path)
**Label:** `agent-ready` `packaging` `validation-gate`
**Depends on:** P-2, P-4

**Scope.** A `demo` compose profile that needs **no GPU and no model pull**:
- Ship a cached, pre-generated run against the bundled petstore (tests + a real `validate` findings
  set incl. the 422-vs-400 drift) as fixture data baked into the image.
- `cherenkov review --web --demo` loads that fixture into the real `HitlQueue` and serves the UI.
- Clearly badge the UI as "Demo data" so it's never mistaken for a live run (anti-drift).

---

## 4. Next Horizon: Distribution Channels (Spike Findings)

For future releases, we will expand distribution beyond local source checkouts and Docker:

### 4.1 PyPI Distribution
- **Strategy**: Migrate `requirements.txt` to `pyproject.toml` or `setup.py`.
- **UI Bundling**: The pre-built React UI (`cherenkov/web/ui/dist`) must be included in the Python wheel via `MANIFEST.in`.
- **CI Action**: Implement `.github/workflows/publish-pypi.yml` triggering on `refs/tags/v*` using PyPA's `gh-action-pypi-publish`.
- **Challenge**: Playwright requires browser binaries. Running `cherenkov validate` from a `pip install` environment will either require a post-install hook or a runtime check to prompt the user to run `playwright install`.

### 4.2 Docker Hub Distribution
- **Strategy**: Leverage the existing multi-stage `Dockerfile`.
- **CI Action**: Implement `.github/workflows/publish-docker.yml` triggering on tags, using Docker's official `build-push-action`.
- **Multi-arch**: The Node UI build and Python slim base support both `amd64` and `arm64`, but Playwright binaries on ARM can sometimes be tricky. This requires QEMU setup in the GitHub Action and explicit multi-arch tags (`cherenkov:latest-amd64`, `cherenkov:latest-arm64`).

**Acceptance (raw evidence):**
- On a machine with **no GPU**: `docker compose --profile demo up` → Findings queue with real
  petstore drift in < 2 min, no model download. Screen recording from a clean Docker install.

**Why this is gate-critical.** This is the artifact the 5 QA reviewers click through
([ROADMAP_NEXT.md](ROADMAP_NEXT.md) Phase 2). It removes the GPU as a recruiting filter.

---

### P-6 — Quickstart docs + `make`/one-liner + CI image build
**Label:** `agent-ready` `packaging`
**Depends on:** P-3, P-5

**Scope.**
- Rewrite the top of [GETTING_STARTED.md](GETTING_STARTED.md) with the two `docker compose`
  paths (full / demo) as the **primary** install story; keep the from-source path below.
- Add a CI job that builds the image on PR (catches Dockerfile rot) — does **not** push anywhere.
- Optional: a tiny `Makefile` (`make demo`, `make full`) as sugar over compose.

**Acceptance (raw evidence):**
- A reviewer who has never seen the repo follows only the new quickstart and reaches the demo
  queue; capture their terminal + the wall-clock time.
- CI image-build job green on the PR; paste the run link.

**Out of scope.** Publishing to a registry / Docker Hub (deferred — that's a launch concern, and
launch is gated; see [ROADMAP_NEXT.md §9d](ROADMAP_NEXT.md)).

---

### P-7 — SPIKE: scaling architecture (worker-pool vs Kubernetes) — research only
**Label:** `agent-ready` `packaging` `spike`
**Depends on:** none (read-only investigation; can run anytime)

**Scope.** A **time-boxed (≤1 day), read-only** investigation that produces a written
recommendation — **no infrastructure built.** Answer, with evidence:
- What is the *actual* concurrency bottleneck for CHERENKOV runs? (GPU/VRAM for the 7B/8B models,
  Prism, Playwright browsers, or the Python orchestrator.) Measure on the RTX 5060: how many
  concurrent `generate` runs before VRAM/throughput collapses?
- For the realistic near-term need (a single user, occasional concurrent runs), compare:
  **(a)** in-process async / a local worker-pool (Celery/RQ/Arq + Redis), vs **(b)** Kubernetes +
  a model-serving layer (vLLM/Ray Serve/KServe). Cost, ops burden, and what each actually buys.
- A concrete "revisit trigger": the demand signal that would justify (b) over (a).

**Acceptance (raw evidence):** a markdown memo in `docs/research/` with the VRAM/throughput
measurements (paste `nvidia-smi` + timings) and a one-paragraph recommendation. **Deliverable is a
decision, not code.**

**Out of scope.** Building either option. Per [§0 guardrails](#0-decision--guardrails-read-first)
this stays research until a real demand trigger fires.

---

## 3. Explicitly deferred (recorded, NOT scheduled)

Per the guardrails in §0 — captured so the ambition isn't lost, but **not** actioned pre-gate:

| Idea | Why deferred | Revisit trigger |
|------|--------------|-----------------|
| Kubernetes / Helm chart | GPU-bound workload; no horizontal demand; second product | Real multi-node GPU load from ≥1 paying/committed user |
| Parallel-agent fan-out via a job queue (Celery/RQ + Redis) | Premature; one user can't saturate one GPU | When a single user demonstrably needs concurrent runs |
| Registry publish / `docker pull cherenkov` | Launch concern; launch is gated | Gate passes (≥3/5 yes) |
| Multi-arch (arm64 Mac) demo image | Nice-to-have once demo mode exists | If a QA recruit is blocked on Apple Silicon |

---

## 4. Dependency graph (for the orchestrator)

```
P-1 ──> P-2 ──> P-3 ───────────────┐
                 │                  ├──> P-6 (docs + CI)
Phase 0 (real    └──> (full mode)   │
 API wiring) ──> P-4 ──> P-5 ───────┘
                         (demo, gate-critical)
```

Critical path to the validation gate runs **Phase 0 → P-4 → P-5**. Prioritize that lane; the
engine/compose/GPU lane (P-1→P-2→P-3) is parallelizable but lower urgency than getting a
clickable demo into reviewers' hands.
