---
title: Troubleshooting
description: Find answers to common questions and solutions to common issues with CHERENKOV-QA.
---

# Troubleshooting

When something is not working as expected, start here.

---

## :material-frequently-asked-questions: [FAQ](faq.md)

Answers to the most common questions:

- How is CHERENKOV different from Schemathesis?
- Does it work without an LLM?
- What OpenAPI versions are supported?
- Can I use cloud LLMs instead of local?
- Does it support GraphQL and gRPC?
- Is there an enterprise tier?
- What about performance?

---

## :material-bug: [Common Issues](common-issues.md)

Solutions to problems you might encounter:

- Ollama not detected or connection refused
- Zero tests generated
- Slow test generation
- Dashboard not loading
- Redis connection errors
- Memory errors with large specs
- Exit code reference

---

## First Steps

Before diving into specific issues, run diagnostics:

```bash
cherenkov doctor
```

This checks:

- Python version compatibility
- Ollama connectivity and model availability
- Spec file readability
- Target URL reachability
- Disk space and permissions

If `cherenkov doctor` passes and you still have problems, check the [Common Issues](common-issues.md) page or the [FAQ](faq.md).
