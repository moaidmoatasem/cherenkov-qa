---
title: VS Code Extension
description: The CHERENKOV-QA VS Code extension — run validations, view conformance results, and fix drift directly in your editor.
---

# VS Code Extension

The CHERENKOV-QA VS Code extension brings conformance testing directly into your editor.

---

## Installation

1. Open VS Code
2. Press `Ctrl+Shift+X` (Extensions panel)
3. Search for **"CHERENKOV-QA"**
4. Click **Install**

Or install from the command line:

```bash
code --install-extension cherenkov-qa.cherenkov-vscode
```

---

## Features

### 11 Commands (Command Palette)

| Command | Description |
|---------|-------------|
| `CHERENKOV: Validate` | Run conformance check against target |
| `CHERENKOV: Generate Tests` | Generate tests from a spec file |
| `CHERENKOV: Eject` | Eject current tests to vanilla Playwright |
| `CHERENKOV: Open Dashboard` | Open the web dashboard |
| `CHERENKOV: Doctor` | Run environment diagnostics |
| `CHERENKOV: Init` | Initialize CHERENKOV in current workspace |
| `CHERENKOV: View Divergences` | Open conformance violations panel |
| `CHERENKOV: Approve Verdict` | Approve a HITL item |
| `CHERENKOV: Reject Verdict` | Reject a HITL item |
| `CHERENKOV: Memory Status` | Show knowledge mesh stats |
| `CHERENKOV: Knowledge Query` | Query the second brain |

### Right-Click Integration

Right-click any `.yaml` or `.json` OpenAPI spec in the file explorer:

```
Right-click petstore.yaml → "Generate tests from this spec"
```

### Gutter Indicators

Endpoints in your spec file show live status indicators:

- 🟢 Green dot — all tests passing
- 🔴 Red dot — drift detected
- ⚪ Grey dot — untested

### CodeLens

Above each path in your spec, see live test stats:

```yaml
/pets:          ← [4 tests passing]
  get:          ← [✅ Conformant]
/pets/{petId}:  ← [1 conformance violation]
  get:          ← [❌ DRIFT: Expected 200, got 404]
```

### Diagnostics Panel

Red squiggles appear on drifting endpoints. Press `Ctrl+.` for Quick Fix:

```
⚡ Apply suggested assertion for GET /pets/{petId}
⚡ Update spec: change expected status to 404
⚡ View full divergence report
```

### Test Explorer

The CHERENKOV sidebar shows a test explorer tree:

```
CHERENKOV
├── petstore.yaml
│   ├── ✅ GET /pets
│   ├── ✅ POST /pets
│   └── ❌ GET /pets/{petId}  [drift]
└── stripe-api.yaml
    └── ✅ POST /v1/charges
```

---

## Configuration

```json
// .vscode/settings.json
{
  "cherenkov.specPath": "./api/openapi.yaml",
  "cherenkov.targetUrl": "http://localhost:8000",
  "cherenkov.autoValidate": true,
  "cherenkov.autoValidateOnSave": true
}
```

---

## Publish / Build from Source

```bash
cd vscode/
npm install
vsce package
# Produces cherenkov-qa-X.Y.Z.vsix

# Install locally
code --install-extension cherenkov-qa-X.Y.Z.vsix
```
