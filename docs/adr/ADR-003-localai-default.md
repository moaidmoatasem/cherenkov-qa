# ADR-003: LocalAI as Default LLM Backend

**Date:** 2026-06-08
**Status:** Accepted
**Deciders:** Project Owner + AI Agents
**Related EPIC:** #277 (Phase -1), #281 (Phase 2)

---

## Context

CHERENKOV-QA requires an LLM backend for:
- Test generation (qwen2.5-coder:7b)
- Test planning (deterministic Python — no LLM call)
- Visual testing (qwen2.5-vl:7b)
- Chat agents (any model)

Options considered:
1. **Ollama** (current, local, no Docker)
2. **LocalAI** (Docker-native, OpenAI-compatible API)
3. **Cloud APIs** (OpenAI, Anthropic, Google)

## Decision

**LocalAI as default, Ollama as fallback, cloud opt-in**:
- **LocalAI** (Docker-native, OpenAI-compatible API, VLM built-in) is the default
- **Ollama** remains as fallback for users who don't want Docker
- **Cloud APIs** (OpenAI, Anthropic) are opt-in via egress policy

### Rationale

1. **Zero-config Docker**: `docker compose up` starts LocalAI + Redis + CHERENKOV
2. **No separate runtime**: LocalAI runs in Docker, no Ollama binary needed
3. **VLM built-in**: LocalAI supports vision models natively (qwen2.5-vl:7b)
4. **OpenAI-compatible API**: Same `/v1/chat/completions` endpoint, easy adapter
5. **Solo dev zero-cost**: Everything local, cloud opt-in only
6. **Egress policy**: Respects `egress = "none"` (no outbound network)

### Architecture

```
┌─────────────────────────────────────┐
│  CHERENKOV Substrate Router         │
│  - DeviceClass → VLMTier mapping    │
│  - Provider selection               │
│  - Fallback chain                   │
└──────────────┬──────────────────────┘
               │
               ├─→ LocalAI (default)
               │   - Docker container
               │   - OpenAI-compatible API
               │   - VLM built-in
               │
               ├─→ Ollama (fallback)
               │   - Local binary
               │   - No Docker required
               │   - No VLM support
               │
               └─→ OpenAI/Anthropic (opt-in)
                   - Cloud API
                   - Requires egress = "any"
                   - Pay-per-use
```

### Fallback Chain

```python
def get_vlm_provider(self):
    """Get VLM provider based on tier."""
    if self.vlm_tier == VLMTier.PIXEL_DIFF_ONLY:
        return None  # No VLM, pixel diff only

    # Try LocalAI first
    if self.localai.is_available():
        return self.localai

    # Fallback to Ollama
    if self.ollama.is_available():
        return self.ollama

    # Fallback to OpenAI (if egress allowed)
    if self.openai.is_available():
        return self.openai

    # No VLM available
    return None
```

### Configuration

```toml
# cherenkov.toml
[substrate]
provider = "localai"  # localai, ollama, openai
egress = "none"       # none, internal, any

[localai]
base_url = "http://localhost:8080"
model = "qwen2.5-vl:7b"

[ollama]
base_url = "http://localhost:11434"
model = "qwen2.5-coder:7b"

[openai]
api_key = "${OPENAI_API_KEY}"  # from environment
model = "gpt-4o-mini"
```

### Consequences

**Positive:**
- Zero-config Docker setup
- VLM built-in (no separate vision model)
- OpenAI-compatible API (easy adapter)
- Solo dev zero-cost (everything local)
- Respects egress policy (no outbound network by default)

**Negative:**
- Requires Docker (not available on all systems)
- Docker overhead (memory, CPU)
- LocalAI is less mature than Ollama
- VLM models are large (7GB+ download)

**Mitigations:**
- Ollama fallback for systems without Docker
- Graceful degradation (pixel_diff_only if no VLM available)
- Model caching (download once, reuse)
- Clear documentation of Docker requirements

## Alternatives Considered

### Alternative 1: Ollama as Default
Keep Ollama as default (current setup).

**Rejected because:**
- No VLM support (Ollama doesn't support vision models yet)
- Requires separate binary installation
- No Docker integration (manual setup)
- Less mature API (not OpenAI-compatible)

### Alternative 2: Cloud APIs as Default
Use OpenAI/Anthropic as default.

**Rejected because:**
- Requires internet connection (not localhost-first)
- Pay-per-use (not zero-cost for solo dev)
- Privacy concerns (sending code to cloud)
- Violates egress policy (requires `egress = "any"`)

### Alternative 3: Hybrid (LocalAI + Ollama)
Use LocalAI for VLM, Ollama for text generation.

**Rejected because:**
- Adds complexity (two runtimes)
- Confusing for users (which one to install?)
- Docker overhead for LocalAI anyway
- LocalAI supports both text and VLM

## Implementation Plan

### Phase 2: LocalAI Integration (2 weeks)
- Create `LocalAIVLMProvider` adapter (ticket #339)
- Add tier-aware routing to `SubstrateRouter` (ticket #340)
- Test LocalAI Docker integration (ticket #341)
- Add `/healthz` endpoint (ticket #342)
- Extend `launcher.py` with NDJSON events (ticket #343)
- Add `cherenkov doctor --vlm --localai` (ticket #344)

### Phase 0b: Docker Compose AI (1 week)
- Create `docker-compose.ai.yml` (ticket #317)
- Start LocalAI + Redis + CHERENKOV with one command
- Health checks for all services
- Volume mounts for model caching

## References

- EPIC #281 (Phase 2: VLM + LocalAI)
- `cherenkov/substrate/providers/vlm.py` (existing VLM provider)
- `cherenkov/substrate/router.py` (existing router)
- LocalAI documentation: https://localai.io/
- `docker-compose.ai.yml` (to be created)

## Notes

This ADR establishes LocalAI as the default LLM backend. All Phase 2 tickets must follow the LocalAI-first pattern with Ollama fallback.

If LocalAI proves unstable or too resource-intensive, this ADR will be revisited and Ollama may become the default again.
