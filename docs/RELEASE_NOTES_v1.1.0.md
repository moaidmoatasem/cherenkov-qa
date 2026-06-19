# Release Notes: CHERENKOV-QA v1.1.0

**Date:** 2026-06-19
**Tag:** `v1.1.0`

## What's New Since v1.0.0

v1.1.0 delivers the full extended roadmap (Phases 9-16): multi-protocol support, enterprise tier, IDE integration, CI/CD native actions, and platform foundation.

### Multi-Protocol Support
- **GraphQL:** Ingest GraphQL schemas/introspection queries → generate typed Apollo/urql test code
- **gRPC/Protobuf:** Parse `.proto` via Buf CLI → generate gRPC client conformance tests
- **AsyncAPI:** WebSocket and event-driven API support with publish/subscribe test templates
- All protocols follow the same `cherenkov eject` path for zero-lock-in

### Enterprise Tier
- **SAML 2.0 / SSO:** Okta, Azure AD, Google Workspace integration
- **SOC2 Readiness:** Report generator with compliance evidence export
- **GDPR Compliance:** Data residency, right-to-delete, privacy controls
- **RBAC:** Admin, Developer, Viewer roles
- **Audit Logging:** Append-only JSONL-based audit trail with CSV/JSON export
- **Org Management:** Multi-tenant organization/team/project structure with quotas
- **BYO-LLM:** Azure OpenAI and AWS Bedrock provider wrappers

### VS Code Extension
- 11 commands (validate, generate, eject, doctor, init, dashboard, etc.)
- Right-click OpenAPI spec → "Generate tests from this spec"
- Gutter icons: green dot (passing), red dot (drift), grey dot (untested)
- CodeLens above each path: `4 tests passing` / `1 conformance violation`
- Diagnostics panel: red squiggles on drifting endpoints
- Quick Fix: Ctrl+. on a violation → "Apply suggested assertion"
- Test Explorer sidebar for conformance results

### CI/CD Native
- **GitHub Actions:** `cherenkov-qa/action@v1` with SARIF output for GitHub Security tab
- **GitLab CI:** `.gitlab-ci-template.yml` include
- **CircleCI:** `cherenkov-circleci-orb.yml`
- **JUnit XML:** Standard CI test result parsing
- **SARIF:** Code scanning alerts in GitHub Security tab
- **Jira Integration:** REST v3 client with `--export-jira` CLI flag
- **Pre-commit hook:** `.pre-commit-hooks.yaml` for drift detection before push

### Launch Materials
- Product Hunt launch kit (`docs/launch/PRODUCT_HUNT_HN_KIT.md`)
- Demo script (90-second storyboard, `docs/launch/DEMO_SCRIPT.md`)
- Discord setup guide (`docs/launch/DISCORD_SETUP.md`)
- v1.0.0 release notes and changelog

### Spec Guardian
- Continuous conformance monitoring daemon
- PR-comment integration on spec changes
- Coverage map and regression detection
- Spec change attribution to git commits

### Training Pipeline (Foundation)
- Dataset collector for (spec, scenario, test, verdict) tuples
- LoRA fine-tune trainer on qwen2.5-coder-7b base
- Evaluation harness for compile rate and conformance hit rate

## Quick Start

```bash
# Zero-install quickstart
npx cherenkov-cli init

# Run against a spec
cherenkov validate --spec petstore.yaml --target http://localhost:8000

# Export results
cherenkov validate --spec petstore.yaml --target http://localhost:8000 --export-jira --jira-project QA
```

## Community

Star the repo, join our Discord, and help define AI-native API testing.
