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

## 🔒 The Anti-Lock-In Promise
CHERENKOV does not lock you into a proprietary framework. Every test generated is a standard, pure Playwright TypeScript file (`.spec.ts`) that imports a pure `openapi-fetch` client. 

Running `eject` strips all CHERENKOV-specific trace monkey-patching and hooks cleanly, leaving you with a standard open-source suite.
