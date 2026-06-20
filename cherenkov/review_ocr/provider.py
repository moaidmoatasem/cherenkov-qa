from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from cherenkov.review_ocr.models import OCRProvider


def _default_config_path() -> str:
    return os.path.join(str(Path.home()), ".opencodereview", "config.json")


class OCRProviderManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or _default_config_path()
        self._config: dict = {}
        self._load()

    def _load(self):
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._config = {}

    def _save(self):
        parent = os.path.dirname(self.config_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    def get_active_provider(self) -> OCRProvider:
        env_url = os.environ.get("OCR_LLM_URL", "")
        env_token = os.environ.get("OCR_LLM_TOKEN", "")
        env_model = os.environ.get("OCR_LLM_MODEL", "")
        env_auth_header = os.environ.get("OCR_LLM_AUTH_HEADER", "")
        env_anthropic = os.environ.get("OCR_USE_ANTHROPIC", "")

        if env_url:
            is_anthropic = ("anthropic" in env_url.lower() or env_anthropic.lower() in ("true", "1"))
            return OCRProvider(
                name="env",
                base_url=env_url,
                model=env_model or "claude-sonnet-4-6",
                protocol="anthropic" if is_anthropic else "openai",
                auth_header=env_auth_header or "x-api-key",
                auth_token=env_token,
            )

        provider_name = self._config.get("provider", "anthropic")
        providers = self._config.get("providers", {})
        provider_cfg = providers.get(provider_name, {})
        return OCRProvider(
            name=provider_name,
            base_url=provider_cfg.get("url", ""),
            model=provider_cfg.get("model", "claude-sonnet-4-6"),
            protocol=provider_cfg.get("protocol", "anthropic"),
            auth_header=provider_cfg.get("auth_header", "x-api-key"),
            auth_token=provider_cfg.get("api_key", ""),
        )

    def list_providers(self) -> list[str]:
        return list(self._config.get("providers", {}).keys()) + ["anthropic", "openai", "dashscope", "deepseek"]

    def set_provider(self, name: str, config: dict):
        providers = self._config.setdefault("providers", {})
        providers[name] = config
        self._config["provider"] = name
        self._save()

    def set_active_provider(self, name: str):
        self._config["provider"] = name
        self._save()

    def get_provider(self, name: str) -> Optional[OCRProvider]:
        providers = self._config.get("providers", {})
        cfg = providers.get(name)
        if not cfg:
            return None
        return OCRProvider(
            name=name,
            base_url=cfg.get("url", ""),
            model=cfg.get("model", ""),
            protocol=cfg.get("protocol", "anthropic"),
            auth_header=cfg.get("auth_header", "x-api-key"),
            auth_token=cfg.get("api_key", ""),
        )

    def set_llm_config(self, key: str, value: str):
        self._config["llm"] = self._config.get("llm", {})
        self._config["llm"][key] = value
        self._save()

    def get_llm_config(self, key: str, default: str = "") -> str:
        return self._config.get("llm", {}).get(key, default)
