# Migrating from Dredd to CHERENKOV-QA

Dredd was a pioneer in API contract testing, but it has officially been deprecated and is no longer maintained. If you are looking for a modern, AI-native replacement that supports OpenAPI 3.x, generative testing, and intelligent healing without the pain of writing manual hooks, CHERENKOV is your answer.

This guide will walk you through replacing Dredd with CHERENKOV in your workflow.

## Why CHERENKOV?

| Feature | Dredd | CHERENKOV-QA |
|---------|-------|--------------|
| **OpenAPI 3.x Support** | Partial / Buggy | 100% Native |
| **Test Generation** | Very limited (example-only) | Full AI generation (edge cases, 400s) |
| **Hook Writing** | Mandatory JS/Python hooks | Zero manual hooks required |
| **Maintenance** | Deprecated | Active development |
| **Healing** | None | Suggest-only healing |
| **Lock-in** | High (Dredd specific hooks) | Zero (`cherenkov eject`) |

## Step 1: Remove Dredd

Remove Dredd from your project's dependencies:

```bash
# Using npm
npm uninstall dredd
rm dredd.yml

# Using pip
pip uninstall dredd-hooks
```

## Step 2: Install CHERENKOV

You can install CHERENKOV via our zero-install script or globally via pip/npm:

```bash
# Zero-install bootstrap (recommended)
npx cherenkov init --spec api.yaml --target http://localhost:8080

# Or via pip
pip install cherenkov
```

## Step 3: Replace the CI Command

In your CI pipeline (GitHub Actions, GitLab CI, etc.), replace your `dredd` execution step.

**Old Dredd Command:**
```bash
dredd api.yaml http://localhost:8080 --hookfiles=hooks.js
```

**New CHERENKOV Command:**
```bash
cherenkov run --spec api.yaml --target http://localhost:8080
```

## Step 4: Say Goodbye to Manual Hooks

With Dredd, you likely wrote extensive hook files (`hooks.js` or `hooks.py`) to handle setup, teardown, and authentication. 

CHERENKOV handles authentication via the `cherenkov.yaml` configuration and uses a local LLM to automatically infer relationships between endpoints, eliminating the need for 90% of manual hooks. 

To set up global headers (like Bearer tokens), just edit your `.cherenkov/cherenkov.yaml`:

```yaml
auth:
  type: bearer
  token: ${ENV_VAR_TOKEN}
```

Welcome to the future of API testing!
