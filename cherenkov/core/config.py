"""
CHERENKOV core/config.py — structured configuration and environment loading.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import requests
from cherenkov.core.errors import get_logger

class Config:
    """Strongly-typed central configuration parser loading environment variables with safe defaults."""
    
    PROVIDER: str = os.getenv("PROVIDER", "ollama")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    GEN_MODEL: str = os.getenv("GEN_MODEL", "qwen2.5-coder:7b")
    API_URL: str = os.getenv("API_URL", "http://localhost:8000")
    SCHEMA_DEPTH: int = int(os.getenv("SCHEMA_DEPTH", "1"))
    ERROR_THRESHOLD: int = int(os.getenv("ERROR_THRESHOLD", "2"))

    # ── Substrate Router (Epoch 1) ────────────────────────────────────────
    EGRESS: str = os.getenv("CHERENKOV_EGRESS", "internal")

    TIER_SMALL_PROVIDER: str = os.getenv("CHERENKOV_TIER_SMALL_PROVIDER", "ollama")
    TIER_SMALL_MODEL: str = os.getenv("CHERENKOV_TIER_SMALL_MODEL", "qwen2.5-coder:7b")
    TIER_DEEP_PROVIDER: str = os.getenv("CHERENKOV_TIER_DEEP_PROVIDER", "ollama")
    TIER_DEEP_MODEL: str = os.getenv("CHERENKOV_TIER_DEEP_MODEL", "deepseek-r1:8b")

    FALLBACK_ENABLED: bool = os.getenv("CHERENKOV_FALLBACK_ENABLED", "true").lower() == "true"
    FALLBACK_PROVIDER: str = os.getenv("CHERENKOV_FALLBACK_PROVIDER", "openai")

    OPENAI_URL: str = os.getenv("OPENAI_URL", "https://api.openai.com/v1/chat/completions")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # ── E1-5 Cache & Accounting ──────────────────────────────────────────
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() in ("1", "true", "yes")
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "100"))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    
    # -- E6 Federation Corpus --
    CORPUS_OPT_IN: bool = os.getenv("CHERENKOV_CORPUS_OPT_IN", "false").lower() == "true"
    CORPUS_PATH: str = os.getenv("CHERENKOV_CORPUS_PATH", os.path.expanduser("~/.cherenkov/corpus.jsonl"))

    # ── E10 Copilot (Explorer + manual-QA pillar) ─────────────────────────
    # Autonomy ladder; E10 ships "assisted". E13 grows it (augmented/agentic/predictive).
    COPILOT_AUTONOMY: str = os.getenv("CHERENKOV_COPILOT_AUTONOMY", "assisted")
    EXPLORER_SLOW_MS: int = int(os.getenv("CHERENKOV_EXPLORER_SLOW_MS", "2000"))

    @classmethod
    def to_dict(cls) -> dict[str, str | int | bool]:
        return {
            "PROVIDER": cls.PROVIDER,
            "OLLAMA_URL": cls.OLLAMA_URL,
            "GEN_MODEL": cls.GEN_MODEL,
            "API_URL": cls.API_URL,
            "SCHEMA_DEPTH": cls.SCHEMA_DEPTH,
            "ERROR_THRESHOLD": cls.ERROR_THRESHOLD,
            "EGRESS": cls.EGRESS,
            "TIER_SMALL_PROVIDER": cls.TIER_SMALL_PROVIDER,
            "TIER_SMALL_MODEL": cls.TIER_SMALL_MODEL,
            "TIER_DEEP_PROVIDER": cls.TIER_DEEP_PROVIDER,
            "TIER_DEEP_MODEL": cls.TIER_DEEP_MODEL,
            "FALLBACK_ENABLED": cls.FALLBACK_ENABLED,
            "FALLBACK_PROVIDER": cls.FALLBACK_PROVIDER,
            "OPENAI_MODEL": cls.OPENAI_MODEL,
            "CACHE_ENABLED": cls.CACHE_ENABLED,
            "CACHE_MAX_SIZE": cls.CACHE_MAX_SIZE,
            "CACHE_TTL_SECONDS": cls.CACHE_TTL_SECONDS,
            "CORPUS_OPT_IN": cls.CORPUS_OPT_IN,
            "CORPUS_PATH": cls.CORPUS_PATH,
            "COPILOT_AUTONOMY": cls.COPILOT_AUTONOMY,
            "EXPLORER_SLOW_MS": cls.EXPLORER_SLOW_MS,
        }

    @classmethod
    def detect_ollama_device(cls, run_id: str | None = None) -> str:
        """Startup health check querying Ollama to detect whether the model runs on GPU or CPU.
        
        GPU is our supported, optimized target path.
        CPU is portable-but-slow. If CPU is detected, log a loud warning warning.
        """
        log = get_logger("SYSTEM", run_id)
        base_url = cls.OLLAMA_URL.rsplit("/api/generate", 1)[0]
        ps_url = f"{base_url}/api/ps"
        
        # 1. Trigger a lightweight, instant 1-token call to force Ollama to load the model into memory
        try:
            requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": cls.GEN_MODEL,
                    "prompt": "a",
                    "stream": False,
                    "options": {"num_predict": 1}
                },
                timeout=15
            )
        except Exception:
            pass # Ignore loading failures here; let ps check report the status
        
        # 2. Query /api/ps to verify active processor details
        try:
            resp = requests.get(ps_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                for model_info in models:
                    if cls.GEN_MODEL in model_info.get("name", ""):
                        size_vram = model_info.get("size_vram", 0)
                        size = model_info.get("size", 1)
                        
                        # Size VRAM > 0 indicates GPU execution (layers offloaded)
                        if size_vram > 0:
                            vram_pct = int(100 * size_vram / size)
                            gpu_msg = f"GPU mode verified — {vram_pct}% of model layers offloaded to VRAM."
                            log.info("device status", details=gpu_msg, processor="GPU", size_vram=size_vram, size=size)
                            return "GPU"
                        else:
                            cpu_warn = "CPU mode — generation ~10x slower, GPU recommended."
                            log.warning("device status", details=cpu_warn, processor="CPU", size_vram=0)
                            return "CPU"
        except Exception as e:
            log.warning("device status", details=f"Could not connect to Ollama daemon to verify device: {e}", processor="UNKNOWN")
            return "UNKNOWN"
            
        cpu_warn = "CPU mode — generation ~10x slower, GPU recommended."
        log.warning("device status", details=cpu_warn, processor="CPU", size_vram=0)
        return "CPU"
