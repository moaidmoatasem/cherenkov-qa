# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.x     | ✅ (Active development) |

## Reporting a Vulnerability

**Do not file a public GitHub issue for security vulnerabilities.**

Use GitHub's private vulnerability reporting:
**[Report a vulnerability](https://github.com/moaidmoatasem/cherenkov-qa/security/advisories/new)**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

You will receive an acknowledgement within 48 hours and a mitigation target within 7 days.

## Security Practices

- All dependencies are pinned in `pyproject.toml` and `package.json`
- Secrets never logged — API keys, tokens, and credentials are env-var only
- No telemetry, no phone-home, no third-party analytics
- LLM calls are local-first (LocalAI, Ollama); cloud providers require explicit opt-in
- Agents running inside CI/CD use the same env-var-only credential model
- Ejected test suites contain zero CHERENKOV imports (anti-lock-in by design)
