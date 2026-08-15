---
title: Common Issues
description: Solutions to common problems with CHERENKOV-QA — Ollama connectivity, generation failures, dashboard issues, and more.
---

# Common Issues

---

## Start Here: Run Diagnostics

Before troubleshooting individual issues, run:

```bash
cherenkov doctor
```

This checks Python version, Ollama connectivity, spec readability, target reachability, and disk space. Most issues show up here.

---

## Ollama Not Detected / Connection Refused

**Symptoms:**

- `cherenkov doctor` reports Ollama as unreachable
- Error: `Connection refused` or `Could not connect to Ollama`

**Solutions:**

1. **Check if Ollama is running:**

    ```bash
    ollama list
    ```

    If this fails, Ollama is not running. Start it:

    ```bash
    ollama serve
    ```

2. **Check the URL:**

    CHERENKOV connects to Ollama at `http://localhost:11434` by default. If Ollama is running on a different host or port:

    ```bash
    export OLLAMA_HOST=http://your-host:11434
    ```

3. **Check if a model is available:**

    ```bash
    ollama list
    ```

    If no models are listed, pull one:

    ```bash
    ollama pull qwen2.5-coder
    ```

4. **Docker/CI environments:**

    In Docker or CI, Ollama runs as a separate service. Make sure the service is listed and the hostname resolves:

    ```yaml
    # Docker Compose
    services:
      ollama:
        image: ollama/ollama:latest
        ports:
          - "11434:11434"
    ```

    Then set `OLLAMA_HOST=http://ollama:11434`.

5. **Skip Ollama entirely:**

    Many commands do not need an LLM. Use `verify`, `check-suite`, `certify`, or `generate --no-repair` instead.

---

## Zero Tests Generated

**Symptoms:**

- `cherenkov generate` completes but produces no test files
- Output directory is empty

**Solutions:**

1. **Check spec richness:**

    Specs with minimal content (no response schemas, no examples) may not generate meaningful tests. A good spec includes:

    - Response schemas with concrete types
    - Multiple response status codes (200, 400, 404)
    - Request body schemas
    - Path and query parameter definitions

2. **Check for inline schemas:**

    Older CHERENKOV versions had issues with deeply nested inline schemas. Update to the latest version:

    ```bash
    pip install --upgrade cherenkov-qa
    ```

3. **Check the spec is valid:**

    ```bash
    cherenkov doctor
    ```

    Look for spec parsing errors in the output.

4. **Try template fallback:**

    If LLM generation fails, templates always produce output:

    ```bash
    cherenkov generate --spec openapi.yaml --no-repair
    ```

---

## Slow Test Generation

**Symptoms:**

- `cherenkov generate` or `cherenkov validate` takes many minutes
- Progress appears stuck

**Causes and solutions:**

1. **CPU-only inference:**

    LLM inference on CPU is 5-10x slower than GPU. Check if Ollama is using your GPU:

    ```bash
    ollama ps
    ```

    If the model is loaded on CPU, ensure your GPU drivers are installed and Ollama detects the GPU.

2. **Large spec:**

    A spec with 100+ endpoints will generate many tests. Use `--max-probes` to limit:

    ```bash
    cherenkov validate --spec large-api.yaml --target http://localhost:8000 --max-probes 20
    ```

3. **Model downloading:**

    The first run may pull the model, which takes time. Check:

    ```bash
    ollama list
    ```

    If the model is not listed, the first `generate` call will download it (several GB).

4. **Skip generation when possible:**

    For quick feedback, use `verify` (no generation, ~9 seconds):

    ```bash
    cherenkov verify --url http://localhost:8000 --spec openapi.yaml
    ```

---

## Dashboard Not Loading

**Symptoms:**

- Browser shows connection refused on `http://localhost:8000`
- Dashboard command runs but the page is blank

**Solutions:**

1. **Check if the dashboard is running:**

    ```bash
    cherenkov dashboard
    ```

    The dashboard starts a web server on port 8000 by default.

2. **Check port conflicts:**

    If port 8000 is already in use (common with Django, FastAPI dev servers):

    ```bash
    lsof -i :8000
    ```

    Stop the conflicting process or configure CHERENKOV to use a different port.

3. **Check the URL:**

    Open `http://localhost:8000` in your browser. The dashboard should show 5 workspaces: Overview, Author & Generate, Triage, Coverage & Intelligence, and Settings.

4. **Firewall/proxy issues:**

    In Docker or remote environments, ensure port 8000 is exposed and accessible.

---

## Redis Connection Errors

**Symptoms:**

- Error: `Redis connection refused` or `Cannot connect to Redis`
- Warnings about caching being disabled

**Solution:**

Redis is **optional**. CHERENKOV works without it. If you see Redis errors and do not need Redis:

```bash
export CHERENKOV_REDIS_ENABLED=false
cherenkov validate --spec openapi.yaml --target http://localhost:8000
```

Redis is used for caching and session state in multi-user dashboard deployments. For single-user or CI usage, it is not needed.

---

## Memory Errors with Large Specs

**Symptoms:**

- `MemoryError` or `Killed` during validation
- System becomes unresponsive during generation

**Solutions:**

1. **Limit probes:**

    ```bash
    cherenkov validate --spec large-api.yaml --target http://localhost:8000 --max-probes 20
    ```

2. **Validate subsets:**

    If your spec has hundreds of endpoints, consider splitting validation by path prefix or tag.

3. **Use `verify` instead:**

    `verify` uses lightweight probes and is much less memory-intensive than full test generation:

    ```bash
    cherenkov verify --url http://localhost:8000 --spec large-api.yaml --max-probes 20
    ```

4. **Check available memory:**

    LLM inference (via Ollama) and Playwright both consume memory. For large specs, ensure at least 8 GB of available RAM. GPU VRAM helps offload LLM memory usage.

---

## `cherenkov doctor` Output Walkthrough

A healthy `cherenkov doctor` output looks like:

```
CHERENKOV Doctor
================
Python:     3.11.5          OK
Ollama:     localhost:11434  OK (qwen2.5-coder loaded)
Playwright: 1.40.0          OK
Spec:       openapi.yaml    OK (24 paths, 48 operations)
Target:     localhost:8000   OK (200 in 45ms)
Disk:       12.4 GB free    OK
```

**Common failures and what they mean:**

| Check | Failure | Fix |
|-------|---------|-----|
| Python | Version too old | Upgrade to Python 3.9+ |
| Ollama | Connection refused | Start Ollama: `ollama serve` |
| Ollama | No model loaded | Pull a model: `ollama pull qwen2.5-coder` |
| Playwright | Not installed | Run `playwright install` |
| Spec | Parse error | Check YAML/JSON syntax in your spec file |
| Spec | 0 paths | Your spec has no path definitions |
| Target | Connection refused | Start your API server |
| Target | Timeout | Check network connectivity, firewall rules |
| Disk | Low space | Free disk space (Ollama models can be several GB) |

---

## Exit Code Reference

Every CHERENKOV command uses these exit codes:

| Code | Meaning | What to do |
|------|---------|------------|
| `0` | **Pass** — all conformant, no findings | Nothing. Your API matches the spec. |
| `1` | **Drift detected** — one or more divergences | Review the output. Fix the implementation or update the spec. |
| `2` | **Configuration error** — invalid flags or settings | Check command syntax and configuration. |
| `3` | **Configuration error** — spec parse failure | Validate your OpenAPI spec file (syntax, version). |
| `4` | **Network error** — target unreachable | Check that your API server is running and reachable. |

In CI pipelines, exit code 1 should fail the build (drift detected). Exit codes 2-4 indicate setup problems, not API issues.

```bash
cherenkov validate --spec openapi.yaml --target http://localhost:8000
echo "Exit code: $?"
```

---

## Still Stuck?

1. Run `cherenkov doctor` and review every line
2. Check the [FAQ](faq.md) for conceptual questions
3. Search [GitHub Issues](https://github.com/moaidmoatasem/cherenkov-qa/issues) for your error message
4. Open a new issue with `cherenkov doctor` output and the full error message

---

## Next Steps

- [FAQ](faq.md) — answers to common questions
- [CLI Reference](../cli/reference.md) — full command documentation
- [Getting Started](../getting-started/index.md) — start fresh if needed
