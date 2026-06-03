# CHERENKOV Getting Started Guide

Welcome to CHERENKOV! This usage-first guide will walk you from initial installation to running your first passing test suite and ejecting standalone Playwright tests in under 5 minutes.

---

## 🛠️ Prerequisites & Installation

Ensure you have the following installed in your environment:
- Node.js (v18 or higher)
- Python (v3.10 or higher)

### 1. Setup WSL/Local Environment
Clone this repository and run standard package installations inside the workspace:

```bash
# Set up Python Virtual Environment and install packages
python3 -m venv .venv
source .venv/bin/activate
pip install -r target/requirements.txt

# Set up Node/Playwright in the stub folder
cd stub
npm install
npx playwright install
cd ..
```

---

## 🚀 CLI Commands & Usage

CHERENKOV exposes all operations natively through a unified CLI tool: `./bin/cherenkov`.

### Display CLI Command Help
To view all supported commands and options:
```bash
./bin/cherenkov --help
```

---

### Command 1: `validate`
Executes your Playwright test suite against a real server, programmatically parses trace files, compares request vs response payloads, and suggests value assertions.

#### Command Help:
```bash
./bin/cherenkov validate --help
```

#### Standard Usage:
1. Ensure your Target API is healthy and online:
   ```bash
   cd target && uvicorn target_api:app --host 127.0.0.1 --port 8000
   ```
2. Execute validation:
   ```bash
   ./bin/cherenkov validate --target http://localhost:8000
   ```

---

### Command 2: `eject`
Copies all your generated specs and TypeScript compilation files, emits a clean `client.ts` completely stripped of trace interception metadata, and generates standard Playwright and package settings.

#### Command Help:
```bash
./bin/cherenkov eject --help
```

#### Standard Usage:
Eject the suite to a standalone folder with ZERO tool dependencies:
```bash
./bin/cherenkov eject --output ejected_suite
```
The ejected folder `ejected_suite/` is 100% clean and can be executed natively with vanilla Playwright commands:
```bash
cd ejected_suite
npm install
npx playwright test
```

---

### Command 3: `visual` (optional Track B capability layer)
Runs visual-regression checks against a rendered URL. Auto-initializes a baseline on first run; compares against it on subsequent runs. Reuses Track A contracts (`VisualSlice`, `VisualReport`) and the Track A `PlaywrightRunner` — never replaces API conformance.

#### Command Help:
```bash
./bin/cherenkov visual --help
```

#### Standard Usage:
```bash
./bin/cherenkov visual --target http://localhost:3000/checkout
```

Override the baseline-directory label:
```bash
./bin/cherenkov visual --target http://localhost:3000/checkout --baseline-dir stub/visual_baselines
```

---

### Command 4: `init` (E5-1 — zero-config project setup)
Auto-detects OpenAPI specs and generates a sensible `cherenkov.toml` with defaults that are offline, free, and deterministic.

#### Command Help:
```bash
./bin/cherenkov init --help
```

#### Standard Usage:
```bash
./bin/cherenkov init
```

Override profile and force overwrite existing config:
```bash
./bin/cherenkov init --profile ci --force
```

---

### Command 5: `doctor` (E5-3 — system health check)
Reports effective configuration, device health (GPU vs CPU), model availability, egress policy consistency, and environmental dependencies (Node, Playwright, Docker/Prism).

#### Command Help:
```bash
./bin/cherenkov doctor --help
```

#### Standard Usage:
```bash
./bin/cherenkov doctor
```

---

### Command 6: `dashboard` (E5-4 — Truth Model + divergences view)
Displays the Truth Model claim graph and any open divergences. Uses mock data when no Truth Model has been built.

#### Command Help:
```bash
./bin/cherenkov dashboard --help
```

#### Standard Usage:
```bash
./bin/cherenkov dashboard
```

---

### Command 7: `perf` (optional Track B capability layer)
Runs performance baseline checks against an API endpoint using k.  Records latency per run in a local SQLite store (`.cherenkov/perf_metrics.db`) and flags standard-deviation outlier regressions once >= 3 runs exist. If `k6` is not installed, the stage degrades to a simulated baseline tick (HITL verdict) so it still runs in any env.

#### Command Help:
```bash
./bin/cherenkov perf --help
```

#### Standard Usage:
```bash
./bin/cherenkov perf --target http://localhost:8000 --endpoint /health --method GET
```

Tune load profile:
```bash
./bin/cherenkov perf --target http://localhost:8000 --endpoint /users --method POST --vus 10 --duration 10
```

---

### Command 8: `map` (E11 — claims mapping)
Generates the static truth graph map connecting specifications with code and active traces.

#### Command Help:
```bash
./bin/cherenkov map --help
```

#### Standard Usage:
```bash
./bin/cherenkov map
```

---

### Command 9: `daemon` (background observability daemon)
Starts the background websocket server monitoring traffic and coordination logic.

#### Command Help:
```bash
./bin/cherenkov daemon --help
```

#### Standard Usage:
```bash
./bin/cherenkov daemon --port 8080
```

---

### Command 10: `explore` (autonomous exploration crawler)
Crawls targets to inspect anomalies, console/network exceptions, and visual baselines.

#### Command Help:
```bash
./bin/cherenkov explore --help
```

#### Standard Usage:
```bash
./bin/cherenkov explore --target http://localhost:3000
```

---

### Command 11: `author` (intent-driven test generator)
Enables NL-to-Playwright E2E interactive testing loops.

#### Command Help:
```bash
./bin/cherenkov author --help
```

#### Standard Usage:
```bash
./bin/cherenkov author --intent "Register new test user"
```

---

## 🔒 The Anti-Lock-In Promise
CHERENKOV does not lock you into a proprietary framework. Every test generated is a standard, pure Playwright TypeScript file (`.spec.ts`) that imports a pure `openapi-fetch` client. 

Running `eject` strips all CHERENKOV-specific trace monkey-patching and hooks cleanly, leaving you with a standard open-source suite.
