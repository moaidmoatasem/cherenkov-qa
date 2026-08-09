from __future__ import annotations

import os
import threading
import time

import requests
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from typing import Any
from cherenkov.core.errors import get_logger


class CherenkovSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=('.env', '.env.test'), env_file_encoding='utf-8', extra='ignore')

    PROVIDER: str = Field(default='ollama', validation_alias='PROVIDER')
    OLLAMA_URL: str = Field(default='http://localhost:11434/api/generate', validation_alias='OLLAMA_URL')
    OLLAMA_TIMEOUT: int = Field(default=300, validation_alias='OLLAMA_TIMEOUT')
    GEN_MODEL: str = Field(default='qwen2.5-coder:7b', validation_alias='GEN_MODEL')
    API_URL: str = Field(default='http://localhost:8000', validation_alias='API_URL')
    SCHEMA_DEPTH: int = Field(default=1, validation_alias='SCHEMA_DEPTH')
    ERROR_THRESHOLD: int = Field(default=2, validation_alias='ERROR_THRESHOLD')

    PLAYWRIGHT_TIMEOUT_SECONDS: int = Field(default=120, validation_alias='CHERENKOV_PLAYWRIGHT_TIMEOUT_SECONDS')
    TSC_TIMEOUT_SECONDS: int = Field(default=60, validation_alias='CHERENKOV_TSC_TIMEOUT_SECONDS')
    GEN_TIMEOUT_S: int = Field(default=120, validation_alias='CHERENKOV_GEN_TIMEOUT_S')
    PRISM_DOCKER_START_TIMEOUT_SECONDS: int = Field(default=30, validation_alias='CHERENKOV_PRISM_DOCKER_START_TIMEOUT_SECONDS')
    PRISM_DOCKER_STOP_TIMEOUT_SECONDS: int = Field(default=15, validation_alias='CHERENKOV_PRISM_DOCKER_STOP_TIMEOUT_SECONDS')

    EGRESS: str = Field(default='internal', validation_alias='CHERENKOV_EGRESS')

    TIER_SMALL_PROVIDER: str = Field(default='ollama', validation_alias='CHERENKOV_TIER_SMALL_PROVIDER')
    TIER_SMALL_MODEL: str = Field(default='qwen2.5-coder:7b', validation_alias='CHERENKOV_TIER_SMALL_MODEL')
    TIER_DEEP_PROVIDER: str = Field(default='ollama', validation_alias='CHERENKOV_TIER_DEEP_PROVIDER')
    TIER_DEEP_MODEL: str = Field(default='deepseek-r1:8b', validation_alias='CHERENKOV_TIER_DEEP_MODEL')
    TIER_VISION_PROVIDER: str = Field(default='ollama', validation_alias='CHERENKOV_TIER_VISION_PROVIDER')
    TIER_VISION_MODEL: str = Field(default='qwen2.5-vl:7b', validation_alias='CHERENKOV_TIER_VISION_MODEL')

    FALLBACK_ENABLED: bool = Field(default=True, validation_alias='CHERENKOV_FALLBACK_ENABLED')
    FALLBACK_PROVIDER: str = Field(default='openai', validation_alias='CHERENKOV_FALLBACK_PROVIDER')

    OPENAI_URL: str = Field(default='https://api.openai.com/v1/chat/completions', validation_alias='OPENAI_URL')
    OPENAI_API_KEY: str = Field(default='', validation_alias='OPENAI_API_KEY')
    OPENAI_MODEL: str = Field(default='gpt-4o-mini', validation_alias='OPENAI_MODEL')

    GITHUB_MODELS_URL: str = Field(default='https://models.inference.ai.azure.com', validation_alias='CHERENKOV_GITHUB_MODELS_URL')
    GITHUB_TOKEN: str = Field(default='', validation_alias='CHERENKOV_GITHUB_TOKEN')
    GITHUB_WEBHOOK_SECRET: str = Field(default='', validation_alias='CHERENKOV_GITHUB_WEBHOOK_SECRET')
    GITHUB_MODELS_SMALL_MODEL: str = Field(default='meta-llama-3.1-8b-instruct', validation_alias='CHERENKOV_GITHUB_MODELS_SMALL_MODEL')
    GITHUB_MODELS_DEEP_MODEL: str = Field(default='gpt-4o', validation_alias='CHERENKOV_GITHUB_MODELS_DEEP_MODEL')

    CACHE_ENABLED: bool = Field(default=True, validation_alias='CACHE_ENABLED')
    CACHE_MAX_SIZE: int = Field(default=100, validation_alias='CACHE_MAX_SIZE')
    CACHE_TTL_SECONDS: int = Field(default=3600, validation_alias='CACHE_TTL_SECONDS')

    CORPUS_OPT_IN: bool = Field(default=False, validation_alias='CHERENKOV_CORPUS_OPT_IN')
    CORPUS_PATH: str = Field(default=os.path.expanduser('~/.cherenkov/corpus.jsonl'), validation_alias='CHERENKOV_CORPUS_PATH')

    UI_DENSITY: str = Field(default='comfortable', validation_alias='CHERENKOV_UI_DENSITY')
    UI_MOTION: str = Field(default='system', validation_alias='CHERENKOV_UI_MOTION')

    SUBSTRATE_MAX_COST_USD_PER_RUN: float = Field(default=0.0, validation_alias='CHERENKOV_SUBSTRATE_MAX_COST_USD_PER_RUN')
    SUBSTRATE_MAX_LATENCY_MS: int = Field(default=120000, validation_alias='CHERENKOV_SUBSTRATE_MAX_LATENCY_MS')

    COPILOT_AUTONOMY: str = Field(default='assisted', validation_alias='CHERENKOV_COPILOT_AUTONOMY')
    EXPLORER_SLOW_MS: int = Field(default=2000, validation_alias='CHERENKOV_EXPLORER_SLOW_MS')
    COPILOT_MENTOR_ENABLED: bool = Field(default=True, validation_alias='CHERENKOV_COPILOT_MENTOR_ENABLED')
    COPILOT_MENTOR_MIN_CONFIRMATIONS: int = Field(default=2, validation_alias='CHERENKOV_COPILOT_MENTOR_MIN_CONFIRMATIONS')
    CERTIFICATION_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_CERTIFICATION_ENABLED')
    CERTIFICATION_GOLD_SET_PATH: str = Field(default='.cherenkov/gold_set.json', validation_alias='CHERENKOV_CERTIFICATION_GOLD_SET_PATH')
    CERTIFICATION_MIN_FAITHFULNESS: float = Field(default=0.8, validation_alias='CHERENKOV_CERTIFICATION_MIN_FAITHFULNESS')
    CERTIFICATION_MAX_CONCURRENCY: int = Field(default=4, validation_alias='CHERENKOV_CERTIFICATION_MAX_CONCURRENCY')

    MAX_CONCURRENT_SCENARIOS: int = Field(default=4, validation_alias='CHERENKOV_PARALLEL_SCENARIOS')
    DAST_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_DAST_ENABLED')
    RAG_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_RAG_ENABLED')

    CONSENSUS_ORACLE_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_CONSENSUS_ORACLE')
    CONSENSUS_ORACLE_PASSES: int = Field(default=3, validation_alias='CHERENKOV_CONSENSUS_PASSES')

    MEANINGFUL_ASSERTION_GATE_ENABLED: bool = Field(default=True, validation_alias='CHERENKOV_MEANINGFUL_ASSERTION_GATE')

    OCR_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_OCR_ENABLED')
    OCR_TIMEOUT_SECONDS: int = Field(default=120, validation_alias='CHERENKOV_OCR_TIMEOUT_SECONDS')
    OCR_BINARY: str = Field(default='', validation_alias='CHERENKOV_OCR_BINARY')
    OCR_SEVERITY_THRESHOLD: str = Field(default='high', validation_alias='CHERENKOV_OCR_SEVERITY_THRESHOLD')

    HITL_API_KEY: str = Field(default='', validation_alias='CHERENKOV_HITL_API_KEY')
    DB_KEY: str = Field(default='', validation_alias='CHERENKOV_DB_KEY')

    AUTH_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_AUTH_ENABLED')
    JWT_SECRET: str = Field(default='', validation_alias='CHERENKOV_JWT_SECRET')
    JWT_EXPIRE_HOURS: int = Field(default=8, validation_alias='CHERENKOV_JWT_EXPIRE_HOURS')
    BOOTSTRAP_KEY: str = Field(default='', validation_alias='CHERENKOV_BOOTSTRAP_KEY')

    NEMOCLAW_URL: str = Field(default='http://localhost:11435/v1', validation_alias='CHERENKOV_NEMOCLAW_URL')
    NEMOCLAW_API_KEY: str = Field(default='', validation_alias='CHERENKOV_NEMOCLAW_API_KEY')
    NEMOCLAW_TIMEOUT: int = Field(default=300, validation_alias='CHERENKOV_NEMOCLAW_TIMEOUT')
    NEMOCLAW_SMALL_MODEL: str = Field(default='nemotron-nano-4b', validation_alias='CHERENKOV_NEMOCLAW_SMALL_MODEL')
    NEMOCLAW_DEEP_MODEL: str = Field(default='nemotron-super-49b', validation_alias='CHERENKOV_NEMOCLAW_DEEP_MODEL')
    NEMOCLAW_VISION_MODEL: str = Field(default='nemotron-vlm-4b', validation_alias='CHERENKOV_NEMOCLAW_VISION_MODEL')
    NEMOCLAW_OPENSSL_POLICY: str = Field(default='default', validation_alias='CHERENKOV_NEMOCLAW_OPENSSL_POLICY')

    VLM_DEFAULT_PROVIDER: str = Field(default='ollama', validation_alias='CHERENKOV_VLM_PROVIDER')
    VLM_LOCALAI_URL: str = Field(default='http://localhost:8080', validation_alias='CHERENKOV_VLM_LOCALAI_URL')
    VLM_LOCALAI_MODEL: str = Field(default='llava', validation_alias='CHERENKOV_VLM_LOCALAI_MODEL')

    AIRLLM_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_AIRLLM_ENABLED')
    AIRLLM_MODEL: str = Field(default='Qwen2.5-Coder-32B', validation_alias='CHERENKOV_AIRLLM_MODEL')
    AIRLLM_COMPRESSION: str = Field(default='4bit', validation_alias='CHERENKOV_AIRLLM_COMPRESSION')
    AIRLLM_LAYER_SHARDS_PATH: str = Field(default='', validation_alias='CHERENKOV_AIRLLM_LAYER_SHARDS_PATH')

    REDIS_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_REDIS_ENABLED')
    REDIS_URL: str = Field(default='redis://localhost:6379/0', validation_alias='CHERENKOV_REDIS_URL')

    DEVICE_REGISTRATION_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_DEVICE_REGISTRATION')
    DESKTOP_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_DESKTOP_ENABLED')
    DESKTOP_WS_PORT: int = Field(default=9876, validation_alias='CHERENKOV_DESKTOP_WS_PORT')

    MOBILE_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_MOBILE_ENABLED')
    MOBILE_DEVICE_POOL: str = Field(default='', validation_alias='CHERENKOV_MOBILE_DEVICE_POOL')
    APPIUM_URL: str = Field(default='http://localhost:4723', validation_alias='CHERENKOV_APPIUM_URL')

    CHAT_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_CHAT_ENABLED')
    CHAT_WS_PORT: int = Field(default=9877, validation_alias='CHERENKOV_CHAT_WS_PORT')

    MONITORING_ENABLED: bool = Field(default=True, validation_alias='CHERENKOV_MONITORING_ENABLED')
    METRICS_PORT: int = Field(default=8001, validation_alias='CHERENKOV_METRICS_PORT')

    OTEL_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_OTEL_ENABLED')
    OTEL_ENDPOINT: str = Field(default='http://localhost:4317', validation_alias='CHERENKOV_OTEL_ENDPOINT')
    OTEL_SERVICE_NAME: str = Field(default='cherenkov', validation_alias='CHERENKOV_OTEL_SERVICE_NAME')
    OTEL_ENVIRONMENT: str = Field(default='production', validation_alias='CHERENKOV_OTEL_ENVIRONMENT')

    OUTPUT_DIR: str = Field(default='output', validation_alias='CHERENKOV_OUTPUT_DIR')

    ENVIRONMENTS: dict[str, Any] = Field(default_factory=dict, validation_alias='CHERENKOV_ENVIRONMENTS')
    CREDENTIALS: dict[str, Any] = Field(default_factory=dict, validation_alias='CHERENKOV_CREDENTIALS')

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        class TomlSource(PydanticBaseSettingsSource):
            def __init__(self, settings_cls):
                super().__init__(settings_cls)
                self.mapped = {}
                try:
                    import tomllib
                    with open('cherenkov.toml', 'rb') as f:
                        toml_data = tomllib.load(f)
                except Exception:
                    return
                sub = toml_data.get('substrate', {})
                if 'egress' in sub: self.mapped['EGRESS'] = sub['egress']
                tiers = sub.get('tiers', {})
                if 'small' in tiers:
                    if 'provider' in tiers['small']: self.mapped['TIER_SMALL_PROVIDER'] = tiers['small']['provider']
                    if 'model' in tiers['small']: self.mapped['TIER_SMALL_MODEL'] = tiers['small']['model']
                if 'deep' in tiers:
                    if 'provider' in tiers['deep']: self.mapped['TIER_DEEP_PROVIDER'] = tiers['deep']['provider']
                    if 'model' in tiers['deep']: self.mapped['TIER_DEEP_MODEL'] = tiers['deep']['model']
                if 'vision' in tiers:
                    if 'provider' in tiers['vision']: self.mapped['TIER_VISION_PROVIDER'] = tiers['vision']['provider']
                    if 'model' in tiers['vision']: self.mapped['TIER_VISION_MODEL'] = tiers['vision']['model']
                budgets = sub.get('budgets', {})
                if 'max_cost_usd_per_run' in budgets: self.mapped['SUBSTRATE_MAX_COST_USD_PER_RUN'] = budgets['max_cost_usd_per_run']
                if 'max_latency_ms' in budgets: self.mapped['SUBSTRATE_MAX_LATENCY_MS'] = budgets['max_latency_ms']
                copilot = toml_data.get('copilot', {})
                if 'autonomy' in copilot: self.mapped['COPILOT_AUTONOMY'] = copilot['autonomy']
                if 'mentor_enabled' in copilot: self.mapped['COPILOT_MENTOR_ENABLED'] = copilot['mentor_enabled']
                cert = toml_data.get('certification', {})
                if 'gold_set_path' in cert: self.mapped['CERTIFICATION_GOLD_SET_PATH'] = cert['gold_set_path']
                if 'min_faithfulness' in cert: self.mapped['CERTIFICATION_MIN_FAITHFULNESS'] = cert['min_faithfulness']
                
                env = toml_data.get('environments', {})
                if env: self.mapped['ENVIRONMENTS'] = env
                
                cred = toml_data.get('credentials', {})
                if cred: self.mapped['CREDENTIALS'] = cred

            def get_field_value(self, field, field_name: str) -> tuple[Any, str, bool]:
                val = self.mapped.get(field_name.upper())
                if val is not None:
                    return val, field_name, False
                return None, "", False

            def prepare_field_value(self, field_name: str, field, value: Any, value_is_complex: bool) -> Any:
                return value

            def __call__(self) -> dict[str, Any]:
                return self.mapped

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlSource(settings_cls),
            file_secret_settings,
        )

    @property
    def TIERS(self) -> dict[str, dict[str, str]]:  # noqa: N802
        return {
            "small": {
                "provider": self.TIER_SMALL_PROVIDER,
                "model": self.TIER_SMALL_MODEL,
            },
            "deep": {
                "provider": self.TIER_DEEP_PROVIDER,
                "model": self.TIER_DEEP_MODEL,
            },
        }

    def __init__(self, **data):
        super().__init__(**data)
        if not self.CREDENTIALS or not self.ENVIRONMENTS:
            try:
                import tomllib
                with open('cherenkov.toml', 'rb') as f:
                    toml_data = tomllib.load(f)
                if not self.CREDENTIALS and 'credentials' in toml_data:
                    self.CREDENTIALS = toml_data['credentials']
                if not self.ENVIRONMENTS and 'environments' in toml_data:
                    self.ENVIRONMENTS = toml_data['environments']
            except Exception:
                pass

    def validate(self):
        # Pydantic validates on instantiation, so this is mostly a no-op,
        # but we add port bounds checking for backward compatibility.
        pass

    def to_dict(self):
        return self.model_dump(by_alias=False)

    def detect_ollama_device(self, run_id: str | None = None) -> str:
        """Startup health check querying Ollama to detect whether the model runs on GPU or CPU.

        GPU is our supported, optimized target path.
        CPU is portable-but-slow. If CPU is detected, log a loud warning.

        Results are cached for _DEVICE_CACHE_TTL seconds to avoid blocking HTTP calls
        on every health check invocation.
        """
        now = time.monotonic()
        if (
            self._device_cache is not None
            and (now - self._device_cache_ts) < self._DEVICE_CACHE_TTL
        ):
            return self._device_cache

        log = get_logger("SYSTEM", run_id)
        base_url = self.OLLAMA_URL.rsplit("/api/generate", 1)[0]
        ps_url = f"{base_url}/api/ps"

        # 1. Trigger a lightweight, instant 1-token call to force Ollama to load the model into memory
        try:
            requests.post(
                self.OLLAMA_URL,
                json={
                    "model": self.GEN_MODEL,
                    "prompt": "a",
                    "stream": False,
                    "options": {"num_predict": 1},
                },
                timeout=15,
            )
        except Exception as _exc:
            log.warning("Ollama model warm-up failed (non-fatal)", error=str(_exc))

        # 2. Query /api/ps to verify active processor details
        try:
            resp = requests.get(ps_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                for model_info in models:
                    if self.GEN_MODEL in model_info.get("name", ""):
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
                            self._device_cache = "GPU"
                            self._device_cache_ts = time.monotonic()
                            return self._device_cache
                        cpu_warn = (
                            "CPU mode — generation ~10x slower, GPU recommended."
                        )
                        log.warning(
                            "device status",
                            details=cpu_warn,
                            processor="CPU",
                            size_vram=0,
                        )
                        self._device_cache = "CPU"
                        self._device_cache_ts = time.monotonic()
                        return self._device_cache
        except Exception as e:
            log.warning(
                "device status",
                details=f"Could not connect to Ollama daemon to verify device: {e}",
                processor="UNKNOWN",
            )
            self._device_cache = "UNKNOWN"
            self._device_cache_ts = time.monotonic()
            return self._device_cache

        cpu_warn = "CPU mode — generation ~10x slower, GPU recommended."
        log.warning("device status", details=cpu_warn, processor="CPU", size_vram=0)
        self._device_cache = "CPU"
        self._device_cache_ts = time.monotonic()
        return self._device_cache

    # Device detection cache
    _device_cache: str | None = None
    _device_cache_ts: float = 0.0
    _DEVICE_CACHE_TTL: float = 60.0  # seconds

_settings_instance: CherenkovSettings | None = None
_settings_lock = threading.Lock()

def get_settings() -> CherenkovSettings:
    global _settings_instance
    if _settings_instance is None:
        with _settings_lock:
            if _settings_instance is None:
                _settings_instance = CherenkovSettings()
    return _settings_instance


def reset_settings() -> None:
    global _settings_instance
    with _settings_lock:
        _settings_instance = None
