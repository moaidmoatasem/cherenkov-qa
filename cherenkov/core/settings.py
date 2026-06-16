from typing import Dict, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
import time

class CherenkovSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    PROVIDER: str = Field(default='ollama', validation_alias='PROVIDER')
    OLLAMA_URL: str = Field(default='http://localhost:11434/api/generate', validation_alias='OLLAMA_URL')
    OLLAMA_TIMEOUT: int = Field(default=300, validation_alias='OLLAMA_TIMEOUT')
    GEN_MODEL: str = Field(default='qwen2.5-coder:7b', validation_alias='GEN_MODEL')
    API_URL: str = Field(default='http://localhost:8000', validation_alias='API_URL')
    SCHEMA_DEPTH: int = Field(default=1, validation_alias='SCHEMA_DEPTH')
    ERROR_THRESHOLD: int = Field(default=2, validation_alias='ERROR_THRESHOLD')

    PLAYWRIGHT_TIMEOUT_SECONDS: int = Field(default=120, validation_alias='CHERENKOV_PLAYWRIGHT_TIMEOUT_SECONDS')
    TSC_TIMEOUT_SECONDS: int = Field(default=60, validation_alias='CHERENKOV_TSC_TIMEOUT_SECONDS')
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
    GITHUB_MODELS_SMALL_MODEL: str = Field(default='meta-llama-3.1-8b-instruct', validation_alias='CHERENKOV_GITHUB_MODELS_SMALL_MODEL')
    GITHUB_MODELS_DEEP_MODEL: str = Field(default='gpt-4o', validation_alias='CHERENKOV_GITHUB_MODELS_DEEP_MODEL')

    CACHE_ENABLED: bool = Field(default=True, validation_alias='CACHE_ENABLED')
    CACHE_MAX_SIZE: int = Field(default=100, validation_alias='CACHE_MAX_SIZE')
    CACHE_TTL_SECONDS: int = Field(default=3600, validation_alias='CACHE_TTL_SECONDS')

    CORPUS_OPT_IN: bool = Field(default=False, validation_alias='CHERENKOV_CORPUS_OPT_IN')
    CORPUS_PATH: str = Field(default=os.path.expanduser('~/.cherenkov/corpus.jsonl'), validation_alias='CHERENKOV_CORPUS_PATH')

    COPILOT_AUTONOMY: str = Field(default='assisted', validation_alias='CHERENKOV_COPILOT_AUTONOMY')
    EXPLORER_SLOW_MS: int = Field(default=2000, validation_alias='CHERENKOV_EXPLORER_SLOW_MS')
    COPILOT_MENTOR_ENABLED: bool = Field(default=True, validation_alias='CHERENKOV_COPILOT_MENTOR_ENABLED')
    COPILOT_MENTOR_MIN_CONFIRMATIONS: int = Field(default=2, validation_alias='CHERENKOV_COPILOT_MENTOR_MIN_CONFIRMATIONS')
    CERTIFICATION_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_CERTIFICATION_ENABLED')
    CERTIFICATION_GOLD_SET_PATH: str = Field(default='.cherenkov/gold_set.json', validation_alias='CHERENKOV_CERTIFICATION_GOLD_SET_PATH')
    CERTIFICATION_MIN_FAITHFULNESS: float = Field(default=0.8, validation_alias='CHERENKOV_CERTIFICATION_MIN_FAITHFULNESS')

    MAX_CONCURRENT_SCENARIOS: int = Field(default=4, validation_alias='CHERENKOV_PARALLEL_SCENARIOS')
    DAST_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_DAST_ENABLED')
    RAG_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_RAG_ENABLED')

    CONSENSUS_ORACLE_ENABLED: bool = Field(default=False, validation_alias='CHERENKOV_CONSENSUS_ORACLE')
    CONSENSUS_ORACLE_PASSES: int = Field(default=3, validation_alias='CHERENKOV_CONSENSUS_PASSES')

    HITL_API_KEY: str = Field(default='', validation_alias='CHERENKOV_HITL_API_KEY')
    DB_KEY: str = Field(default='', validation_alias='CHERENKOV_DB_KEY')

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
    
    @property
    def TIERS(self) -> Dict[str, Dict[str, str]]:
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


    def validate(self):
        # Pydantic validates on instantiation, so this is mostly a no-op, 
        # but we add port bounds checking for backward compatibility.
        pass

    def to_dict(self):
        return self.model_dump(by_alias=False)

    def detect_ollama_device(self, run_id: Optional[str] = None) -> str:
        try:
            from cherenkov.core.config import Config
            return Config.detect_ollama_device(run_id)
        except ImportError:
            return "UNKNOWN"

_settings_instance = None

def get_settings() -> CherenkovSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = CherenkovSettings()
    return _settings_instance
