"""
CHERENKOV core/config.py — structured configuration and environment loading.
Authority: v3.1 + delta.
"""

from __future__ import annotations

# Load .env file if present (python-dotenv optional dependency)
try:
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(override=False)  # .env values don't override existing env vars
except ImportError:
    pass  # dotenv not installed, env vars only

import os
import time as _time
import requests
from cherenkov.core.errors import get_logger


class Config:
    """Strongly-typed central configuration parser loading environment variables with safe defaults."""

    PROVIDER: str = os.getenv("PROVIDER", "ollama")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "300"))
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

    TIER_VISION_PROVIDER: str = os.getenv("CHERENKOV_TIER_VISION_PROVIDER", "ollama")
    TIER_VISION_MODEL: str = os.getenv("CHERENKOV_TIER_VISION_MODEL", "qwen2.5-vl:7b")

    # Structured tier config — prefer this over accessing individual TIER_* attributes
    TIERS: dict = {}  # populated after class definition

    FALLBACK_ENABLED: bool = (
        os.getenv("CHERENKOV_FALLBACK_ENABLED", "true").lower() == "true"
    )
    FALLBACK_PROVIDER: str = os.getenv("CHERENKOV_FALLBACK_PROVIDER", "openai")

    OPENAI_URL: str = os.getenv(
        "OPENAI_URL", "https://api.openai.com/v1/chat/completions"
    )
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # ── GitHub Models ──────────────────────────────────────────────────────────
    GITHUB_MODELS_URL: str = os.getenv(
        "CHERENKOV_GITHUB_MODELS_URL", "https://models.inference.ai.azure.com"
    )
    GITHUB_TOKEN: str = os.getenv(
        "CHERENKOV_GITHUB_TOKEN", os.getenv("GITHUB_TOKEN", "")
    )
    GITHUB_MODELS_SMALL_MODEL: str = os.getenv(
        "CHERENKOV_GITHUB_MODELS_SMALL_MODEL", "meta-llama-3.1-8b-instruct"
    )
    GITHUB_MODELS_DEEP_MODEL: str = os.getenv(
        "CHERENKOV_GITHUB_MODELS_DEEP_MODEL", "gpt-4o"
    )

    # ── E1-5 Cache & Accounting ──────────────────────────────────────────
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "100"))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

    # -- E6 Federation Corpus --
    CORPUS_OPT_IN: bool = (
        os.getenv("CHERENKOV_CORPUS_OPT_IN", "false").lower() == "true"
    )
    CORPUS_PATH: str = os.getenv(
        "CHERENKOV_CORPUS_PATH", os.path.expanduser("~/.cherenkov/corpus.jsonl")
    )

    # ── E10 Copilot (Explorer + manual-QA pillar) ─────────────────────────
    # Autonomy ladder; E10 ships "assisted". E13 grows it (augmented/agentic/predictive).
    COPILOT_AUTONOMY: str = os.getenv("CHERENKOV_COPILOT_AUTONOMY", "assisted")
    EXPLORER_SLOW_MS: int = int(os.getenv("CHERENKOV_EXPLORER_SLOW_MS", "2000"))
    COPILOT_MENTOR_ENABLED: bool = (
        os.getenv("CHERENKOV_COPILOT_MENTOR_ENABLED", "true").lower() == "true"
    )
    COPILOT_MENTOR_MIN_CONFIRMATIONS: int = int(
        os.getenv("CHERENKOV_COPILOT_MENTOR_MIN_CONFIRMATIONS", "2")
    )
    CERTIFICATION_ENABLED: bool = (
        os.getenv("CHERENKOV_CERTIFICATION_ENABLED", "false").lower() == "true"
    )
    CERTIFICATION_GOLD_SET_PATH: str = os.getenv(
        "CHERENKOV_CERTIFICATION_GOLD_SET_PATH", ".cherenkov/gold_set.json"
    )
    CERTIFICATION_MIN_FAITHFULNESS: float = float(
        os.getenv("CHERENKOV_CERTIFICATION_MIN_FAITHFULNESS", "0.8")
    )

    # ── Pipeline parallelism ──────────────────────────────────────────────
    MAX_CONCURRENT_SCENARIOS: int = int(os.getenv("CHERENKOV_PARALLEL_SCENARIOS", "4"))

    # ── Issue #194: DAST security mutation profile ────────────────────────
    DAST_ENABLED: bool = os.getenv("CHERENKOV_DAST_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    # ── Issue #195: Semantic chunking / RAG for large specs ──────────────
    RAG_ENABLED: bool = os.getenv("CHERENKOV_RAG_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    # ── Research: CANDOR consensus oracle (Gate 7 in ReviewStage) ────────
    # Opt-in: each pass costs one LLM call, so default=off. Enable when you
    # want multi-pass oracle validation on top of the 6-gate static review.
    CONSENSUS_ORACLE_ENABLED: bool = os.getenv(
        "CHERENKOV_CONSENSUS_ORACLE", "false"
    ).lower() in ("1", "true", "yes")
    CONSENSUS_ORACLE_PASSES: int = int(os.getenv("CHERENKOV_CONSENSUS_PASSES", "3"))

    # ── Issue #196: HITL auth API key + at-rest encryption ───────────────
    HITL_API_KEY: str = os.getenv("CHERENKOV_HITL_API_KEY", "")
    DB_KEY: str = os.getenv("CHERENKOV_DB_KEY", "")

    # ── NVIDIA NemoClaw (local Nemotron via OpenShell runtime) ──────────────
    NEMOCLAW_URL: str = os.getenv("CHERENKOV_NEMOCLAW_URL", "http://localhost:11435/v1")
    NEMOCLAW_API_KEY: str = os.getenv("CHERENKOV_NEMOCLAW_API_KEY", "")
    NEMOCLAW_TIMEOUT: int = int(os.getenv("CHERENKOV_NEMOCLAW_TIMEOUT", "300"))
    NEMOCLAW_SMALL_MODEL: str = os.getenv(
        "CHERENKOV_NEMOCLAW_SMALL_MODEL", "nemotron-nano-4b"
    )
    NEMOCLAW_DEEP_MODEL: str = os.getenv(
        "CHERENKOV_NEMOCLAW_DEEP_MODEL", "nemotron-super-49b"
    )
    NEMOCLAW_VISION_MODEL: str = os.getenv(
        "CHERENKOV_NEMOCLAW_VISION_MODEL", "nemotron-vlm-4b"
    )
    NEMOCLAW_OPENSSL_POLICY: str = os.getenv(
        "CHERENKOV_NEMOCLAW_OPENSSL_POLICY", "default"
    )

    # ── Phase 0b: VLM (Phase 2) ──────────────────────────────────────────
    VLM_DEFAULT_PROVIDER: str = os.getenv("CHERENKOV_VLM_PROVIDER", "ollama")
    VLM_LOCALAI_URL: str = os.getenv(
        "CHERENKOV_VLM_LOCALAI_URL", "http://localhost:8080"
    )
    VLM_LOCALAI_MODEL: str = os.getenv("CHERENKOV_VLM_LOCALAI_MODEL", "llava")

    # ── Phase 0b: Redis / Event Bus ──────────────────────────────────────
    REDIS_ENABLED: bool = os.getenv("CHERENKOV_REDIS_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    REDIS_URL: str = os.getenv("CHERENKOV_REDIS_URL", "redis://localhost:6379/0")

    # ── Phase 0b: Device / Desktop (Phase 3) ─────────────────────────────
    DEVICE_REGISTRATION_ENABLED: bool = os.getenv(
        "CHERENKOV_DEVICE_REGISTRATION", "false"
    ).lower() in ("1", "true", "yes")
    DESKTOP_ENABLED: bool = os.getenv("CHERENKOV_DESKTOP_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    DESKTOP_WS_PORT: int = int(os.getenv("CHERENKOV_DESKTOP_WS_PORT", "9876"))

    # ── Phase 0b: Mobile (Phase 5-6) ─────────────────────────────────────
    MOBILE_ENABLED: bool = os.getenv("CHERENKOV_MOBILE_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    MOBILE_DEVICE_POOL: str = os.getenv("CHERENKOV_MOBILE_DEVICE_POOL", "")
    APPIUM_URL: str = os.getenv("CHERENKOV_APPIUM_URL", "http://localhost:4723")

    # ── Phase 0b: Agent / Chat (Phase 4) ─────────────────────────────────
    CHAT_ENABLED: bool = os.getenv("CHERENKOV_CHAT_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    CHAT_WS_PORT: int = int(os.getenv("CHERENKOV_CHAT_WS_PORT", "9877"))

    # ── Phase 0b: Monitoring (Phase 0b) ──────────────────────────────────
    MONITORING_ENABLED: bool = os.getenv(
        "CHERENKOV_MONITORING_ENABLED", "true"
    ).lower() in ("1", "true", "yes")
    METRICS_PORT: int = int(os.getenv("CHERENKOV_METRICS_PORT", "8001"))


    # ── Issue #457: OpenTelemetry export ──────────────────────────────────
    OTEL_ENABLED: bool = os.getenv("CHERENKOV_OTEL_ENABLED", "false").lower() in (
        "1", "true", "yes"
    )
    OTEL_ENDPOINT: str = os.getenv("CHERENKOV_OTEL_ENDPOINT", "http://localhost:4317")
    OTEL_SERVICE_NAME: str = os.getenv("CHERENKOV_OTEL_SERVICE_NAME", "cherenkov")
    OTEL_ENVIRONMENT: str = os.getenv("CHERENKOV_OTEL_ENVIRONMENT", "production")

    # ── Device detection cache ────────────────────────────────────────────
    _device_cache: str | None = None
    _device_cache_ts: float = 0.0
    _DEVICE_CACHE_TTL: float = 60.0  # seconds

    @classmethod
    def validate(cls) -> None:
        """Validate all config values are within acceptable bounds. Raises ValueError on violation."""
        errors = []

        # Timeout bounds
        if hasattr(cls, "OLLAMA_TIMEOUT"):
            if not (1 <= cls.OLLAMA_TIMEOUT <= 3600):
                errors.append(
                    f"OLLAMA_TIMEOUT={cls.OLLAMA_TIMEOUT} must be between 1 and 3600 seconds"
                )

        # Retry bounds
        for attr in ("OLLAMA_RETRIES", "MAX_RETRIES", "GEN_RETRIES"):
            if hasattr(cls, attr):
                val = getattr(cls, attr)
                if not (0 <= val <= 20):
                    errors.append(f"{attr}={val} must be between 0 and 20")

        # Egress policy (EGRESS attribute)
        if hasattr(cls, "EGRESS"):
            if cls.EGRESS not in ("none", "internal", "any"):
                errors.append(
                    f"EGRESS={cls.EGRESS!r} must be one of: none, internal, any"
                )

        # Egress policy alias (EGRESS_POLICY attribute if present)
        if hasattr(cls, "EGRESS_POLICY"):
            if cls.EGRESS_POLICY not in ("none", "internal", "any"):
                errors.append(
                    f"EGRESS_POLICY={cls.EGRESS_POLICY!r} must be one of: none, internal, any"
                )

        # Port numbers
        for attr in (
            "OLLAMA_PORT",
            "API_PORT",
            "WEB_PORT",
            "DESKTOP_WS_PORT",
            "CHAT_WS_PORT",
            "METRICS_PORT",
        ):
            if hasattr(cls, attr):
                val = getattr(cls, attr)
                if val is not None and not (1 <= int(val) <= 65535):
                    errors.append(f"{attr}={val} must be a valid port (1-65535)")

        if errors:
            raise ValueError(
                "Config validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

    @classmethod
    def to_dict(cls) -> dict[str, str | int | bool]:
        return {
            "PROVIDER": cls.PROVIDER,
            "OLLAMA_URL": cls.OLLAMA_URL,
            "OLLAMA_TIMEOUT": cls.OLLAMA_TIMEOUT,
            "GEN_MODEL": cls.GEN_MODEL,
            "API_URL": cls.API_URL,
            "SCHEMA_DEPTH": cls.SCHEMA_DEPTH,
            "ERROR_THRESHOLD": cls.ERROR_THRESHOLD,
            "EGRESS": cls.EGRESS,
            "TIER_SMALL_PROVIDER": cls.TIER_SMALL_PROVIDER,
            "TIER_SMALL_MODEL": cls.TIER_SMALL_MODEL,
            "TIER_DEEP_PROVIDER": cls.TIER_DEEP_PROVIDER,
            "TIER_DEEP_MODEL": cls.TIER_DEEP_MODEL,
            "TIER_VISION_PROVIDER": cls.TIER_VISION_PROVIDER,
            "TIER_VISION_MODEL": cls.TIER_VISION_MODEL,
            "FALLBACK_ENABLED": cls.FALLBACK_ENABLED,
            "FALLBACK_PROVIDER": cls.FALLBACK_PROVIDER,
            "OPENAI_MODEL": cls.OPENAI_MODEL,
            "NEMOCLAW_URL": cls.NEMOCLAW_URL,
            "NEMOCLAW_API_KEY": bool(cls.NEMOCLAW_API_KEY),
            "NEMOCLAW_SMALL_MODEL": cls.NEMOCLAW_SMALL_MODEL,
            "NEMOCLAW_DEEP_MODEL": cls.NEMOCLAW_DEEP_MODEL,
            "NEMOCLAW_VISION_MODEL": cls.NEMOCLAW_VISION_MODEL,
            "CACHE_ENABLED": cls.CACHE_ENABLED,
            "CACHE_MAX_SIZE": cls.CACHE_MAX_SIZE,
            "CACHE_TTL_SECONDS": cls.CACHE_TTL_SECONDS,
            "CORPUS_OPT_IN": cls.CORPUS_OPT_IN,
            "CORPUS_PATH": cls.CORPUS_PATH,
            "COPILOT_AUTONOMY": cls.COPILOT_AUTONOMY,
            "EXPLORER_SLOW_MS": cls.EXPLORER_SLOW_MS,
            "COPILOT_MENTOR_ENABLED": cls.COPILOT_MENTOR_ENABLED,
            "COPILOT_MENTOR_MIN_CONFIRMATIONS": cls.COPILOT_MENTOR_MIN_CONFIRMATIONS,
            "CERTIFICATION_ENABLED": cls.CERTIFICATION_ENABLED,
            "CERTIFICATION_GOLD_SET_PATH": cls.CERTIFICATION_GOLD_SET_PATH,
            "CERTIFICATION_MIN_FAITHFULNESS": cls.CERTIFICATION_MIN_FAITHFULNESS,
            "DAST_ENABLED": cls.DAST_ENABLED,
            "RAG_ENABLED": cls.RAG_ENABLED,
            "HITL_API_KEY": bool(cls.HITL_API_KEY),
            "DB_KEY_ENABLED": bool(cls.DB_KEY),
            "VLM_DEFAULT_PROVIDER": cls.VLM_DEFAULT_PROVIDER,
            "VLM_LOCALAI_URL": cls.VLM_LOCALAI_URL,
            "VLM_LOCALAI_MODEL": cls.VLM_LOCALAI_MODEL,
            "REDIS_ENABLED": cls.REDIS_ENABLED,
            "REDIS_URL": cls.REDIS_URL,
            "DEVICE_REGISTRATION_ENABLED": cls.DEVICE_REGISTRATION_ENABLED,
            "DESKTOP_ENABLED": cls.DESKTOP_ENABLED,
            "DESKTOP_WS_PORT": cls.DESKTOP_WS_PORT,
            "MOBILE_ENABLED": cls.MOBILE_ENABLED,
            "MOBILE_DEVICE_POOL": cls.MOBILE_DEVICE_POOL,
            "APPIUM_URL": cls.APPIUM_URL,
            "CHAT_ENABLED": cls.CHAT_ENABLED,
            "CHAT_WS_PORT": cls.CHAT_WS_PORT,
            "MONITORING_ENABLED": cls.MONITORING_ENABLED,
            "METRICS_PORT": cls.METRICS_PORT,
        }

    @classmethod
    def detect_ollama_device(cls, run_id: str | None = None) -> str:
        """Startup health check querying Ollama to detect whether the model runs on GPU or CPU.

        GPU is our supported, optimized target path.
        CPU is portable-but-slow. If CPU is detected, log a loud warning warning.

        Results are cached for _DEVICE_CACHE_TTL seconds to avoid blocking HTTP calls
        on every health check invocation.
        """
        now = _time.monotonic()
        if (
            cls._device_cache is not None
            and (now - cls._device_cache_ts) < cls._DEVICE_CACHE_TTL
        ):
            return cls._device_cache

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
                    "options": {"num_predict": 1},
                },
                timeout=15,
            )
        except Exception:
            pass  # Ignore loading failures here; let ps check report the status

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
                            log.info(
                                "device status",
                                details=gpu_msg,
                                processor="GPU",
                                size_vram=size_vram,
                                size=size,
                            )
                            cls._device_cache = "GPU"
                            cls._device_cache_ts = _time.monotonic()
                            return cls._device_cache
                        else:
                            cpu_warn = (
                                "CPU mode — generation ~10x slower, GPU recommended."
                            )
                            log.warning(
                                "device status",
                                details=cpu_warn,
                                processor="CPU",
                                size_vram=0,
                            )
                            cls._device_cache = "CPU"
                            cls._device_cache_ts = _time.monotonic()
                            return cls._device_cache
        except Exception as e:
            log.warning(
                "device status",
                details=f"Could not connect to Ollama daemon to verify device: {e}",
                processor="UNKNOWN",
            )
            cls._device_cache = "UNKNOWN"
            cls._device_cache_ts = _time.monotonic()
            return cls._device_cache

        cpu_warn = "CPU mode — generation ~10x slower, GPU recommended."
        log.warning("device status", details=cpu_warn, processor="CPU", size_vram=0)
        cls._device_cache = "CPU"
        cls._device_cache_ts = _time.monotonic()
        return cls._device_cache


# Populate structured tier config after class definition
Config.TIERS = {
    "small": {
        "provider": Config.TIER_SMALL_PROVIDER,
        "model": Config.TIER_SMALL_MODEL,
    },
    "deep": {
        "provider": Config.TIER_DEEP_PROVIDER,
        "model": Config.TIER_DEEP_MODEL,
    },
}
