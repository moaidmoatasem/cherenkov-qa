---
title: Local LLM Setup
description: Configure CHERENKOV-QA to use Ollama, LocalAI, or cloud LLM providers.
---

# Local LLM Setup

CHERENKOV uses a local LLM by default. No cloud. No API keys. Your spec never leaves your machine.

---

## Default Setup (Ollama)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull qwen2.5-coder:7b    # Code generation (~4GB)
ollama pull deepseek-r1:8b      # Planning/reasoning (~5GB)

# Verify
ollama list
```

CHERENKOV will automatically detect and use Ollama at `http://localhost:11434`.

---

## Model Tiers

| Tier | Default Model | Use Case | RAM |
|------|--------------|---------|-----|
| Small | `qwen2.5-coder:7b` | Test code generation | 8GB |
| Deep | `deepseek-r1:8b` | Reasoning, planning | 8GB |
| Vision | LocalAI VLM | Screenshot analysis | 8GB |
| Cloud | OpenAI/Anthropic | Fallback | API |

---

## Configure via `cherenkov.toml`

```toml
[substrate]
default_tier = "small"

[substrate.ollama]
base_url = "http://localhost:11434"
small_model = "qwen2.5-coder:7b"
deep_model = "deepseek-r1:8b"

[substrate.localai]
base_url = "http://localhost:8080"
vision_model = "llava"

# Optional cloud fallback
[substrate.openai]
api_key = "${OPENAI_API_KEY}"
model = "gpt-4o"
```

---

## LocalAI (Vision Support)

LocalAI provides VLM (vision-language model) support for screenshot analysis:

```bash
# Start LocalAI via Docker
docker compose -f docker-compose.ai.yml up localai

# Verify
curl http://localhost:8080/v1/models
```

---

## Smaller Models (Low-RAM Machines)

```bash
# 4-bit quantized variants for 8GB RAM machines
ollama pull qwen2.5-coder:3b         # 2GB
ollama pull deepseek-r1:1.5b         # 1GB

# Update config
```

```toml
[substrate.ollama]
small_model = "qwen2.5-coder:3b"
deep_model = "deepseek-r1:1.5b"
```

!!! warning "Quality tradeoff"
    Smaller models generate valid but simpler tests. The 7B/8B defaults are recommended for best conformance coverage.

---

## Cloud Fallback (Optional)

```bash
export OPENAI_API_KEY=sk-...
```

```toml
[substrate]
default_tier = "cloud"  # Force cloud for all tasks
```

CHERENKOV will route through OpenAI if local models are unavailable.
