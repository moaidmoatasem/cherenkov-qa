"""
CHERENKOV substrate/providers/airllm_client.py — AirLLM inference client.

AirLLM runs massive LLMs on consumer GPUs via layer-wise inference.
It is a local Python library, not an HTTP service: this client calls
airllm.AutoModel.generate() directly.

Default model: Qwen2.5-Coder-32B with 4-bit compression.
Enable with CHERENKOV_AIRLLM_ENABLED=true.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from cherenkov.core.errors import ProviderJSONError, get_logger
from cherenkov.core.settings import get_settings
from cherenkov.substrate.interfaces import InferenceClient

logger = logging.getLogger(__name__)

_RE_FENCE_START = _RE_FENCE_END = None


def _get_fence_regexes():
    global _RE_FENCE_START, _RE_FENCE_END
    if _RE_FENCE_START is None:
        import re
        _RE_FENCE_START = re.compile(r"^```[a-z]*\n?")
        _RE_FENCE_END = re.compile(r"\n?```$")
    return _RE_FENCE_START, _RE_FENCE_END


def _strip_fences(text: str) -> str:
    start_re, end_re = _get_fence_regexes()
    text = start_re.sub("", text)
    text = end_re.sub("", text)
    return text.strip()


class AirLLMInferenceClient(InferenceClient):
    """Local AirLLM inference client for massive models on constrained GPUs."""

    def __init__(self) -> None:
        self._token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reprompts": 0,
        }
        self._model = None
        self._model_name = ""
        self._compression = ""
        self._device = "cpu"

    def _load_model(self) -> Any:
        if self._model is not None and self._model_name == get_settings().AIRLLM_MODEL:
            return self._model

        try:
            from airllm import AutoModel
        except ImportError as exc:
            raise ProviderJSONError(
                "AirLLM is not installed. Run: pip install airllm"
            ) from exc

        settings = get_settings()
        model_name = settings.AIRLLM_MODEL
        compression = settings.AIRLLM_COMPRESSION
        shards_path = settings.AIRLLM_LAYER_SHARDS_PATH

        self._model_name = model_name
        self._compression = compression

        kwargs: dict[str, Any] = {}
        if shards_path:
            kwargs["layer_shards_saving_path"] = shards_path
        if compression and compression != "none":
            kwargs["compression"] = compression

        load_kwargs: dict[str, Any] = {}
        if compression and compression != "none":
            load_kwargs["compression"] = compression

        logger.info(
            "airllm loading model",
            model=model_name,
            compression=compression,
            shards_path=shards_path or "(default)",
        )

        t0 = time.monotonic()
        model = AutoModel.from_pretrained(model_name, **kwargs)
        dt = time.monotonic() - t0
        logger.info("airllm model loaded", model=model_name, duration_s=round(dt, 1))

        self._model = model
        self._device = _detect_device()
        return model

    def _tokenize(self, text: str, model: Any) -> Any:
        max_length = 2048
        return model.tokenizer(
            [text],
            return_tensors="pt",
            return_attention_mask=False,
            truncation=True,
            max_length=max_length,
            padding=False,
        )

    def _decode(self, output: Any, model: Any) -> str:
        if hasattr(output, "sequences") and hasattr(output, "sequences_scores"):
            token_ids = output.sequences[0]
        elif hasattr(output, "cpu"):
            token_ids = output.cpu()[0]
        else:
            token_ids = output

        if hasattr(token_ids, "tolist"):
            token_ids = token_ids.tolist()

        return model.tokenizer.decode(token_ids, skip_special_tokens=True)

    def _estimate_tokens(self, text: object) -> int:
        return max(1, len(str(text)) // 4)

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        max_reprompts: int = 2,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> dict:
        log = get_logger("airllm", run_id)
        attempt = 0
        last_raw = ""
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "reprompts": 0}

        combined = (
            f"System: {system_prompt}\n\nUser: {user_prompt}\n\n"
            "Please respond with valid JSON only, no markdown fences."
        )

        while attempt <= max_reprompts:
            t0 = time.monotonic()
            loaded_model = self._load_model()
            tokenized = self._tokenize(combined, loaded_model)
            input_ids = tokenized["input_ids"]

            device_input = input_ids
            if self._device == "cuda":
                device_input = input_ids.cuda()

            gen_kwargs: dict[str, Any] = {
                "max_new_tokens": 1024,
                "use_cache": True,
                "return_dict_in_generate": True,
            }
            if hasattr(loaded_model, "generate"):
                try:
                    import inspect
                    sig = inspect.signature(loaded_model.generate)
                    if "temperature" in sig.parameters:
                        gen_kwargs["temperature"] = temperature
                except (ImportError, ValueError, TypeError):
                    pass

            output = loaded_model.generate(device_input, **gen_kwargs)
            raw = self._decode(output, loaded_model)
            last_raw = raw
            dt_ms = int((time.monotonic() - t0) * 1000)

            self._token_usage["prompt_tokens"] = self._estimate_tokens(combined)
            self._token_usage["completion_tokens"] = self._estimate_tokens(raw)

            cleaned = _strip_fences(raw)
            cleaned = cleaned.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.lstrip("`")
            if cleaned.endswith("```"):
                cleaned = cleaned.rstrip("`")
            cleaned = cleaned.strip()

            import json
            parsed = None
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                start = cleaned.find("{")
                end = cleaned.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        parsed = json.loads(cleaned[start : end + 1])
                    except json.JSONDecodeError:
                        parsed = None

            if parsed is not None:
                log.info("json ok", model=model, attempt=attempt, duration_ms=dt_ms)
                return parsed

            attempt += 1
            self._token_usage["reprompts"] = attempt
            log.warning(
                "json invalid, reprompting",
                model=model,
                attempt=attempt,
                duration_ms=dt_ms,
            )

        raise ProviderJSONError(
            f"{model} did not return valid JSON after {max_reprompts} reprompts. "
            f"Last 200 chars: {last_raw[:200]!r}"
        )

    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        max_reprompts: int = 2,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        log = get_logger("airllm", run_id)
        attempt = 0
        text = ""
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "reprompts": 0}

        combined = f"System: {system_prompt}\n\nUser: {user_prompt}"

        while attempt <= max_reprompts:
            t0 = time.monotonic()
            model = self._load_model()
            tokenized = self._tokenize(combined, model)
            input_ids = tokenized["input_ids"]

            device_input = input_ids
            if self._device == "cuda":
                device_input = input_ids.cuda()

            gen_kwargs: dict[str, Any] = {
                "max_new_tokens": 2048,
                "use_cache": True,
                "return_dict_in_generate": True,
            }
            if hasattr(model, "generate"):
                try:
                    import inspect
                    sig = inspect.signature(model.generate)
                    if "temperature" in sig.parameters:
                        gen_kwargs["temperature"] = temperature
                except (ImportError, ValueError, TypeError):
                    pass

            output = model.generate(device_input, **gen_kwargs)
            raw = self._decode(output, model)
            dt_ms = int((time.monotonic() - t0) * 1000)

            self._token_usage["prompt_tokens"] = self._estimate_tokens(combined)
            self._token_usage["completion_tokens"] = self._estimate_tokens(raw)

            text = _strip_fences(raw)
            text = text.strip()
            log.info(
                "code ok",
                model=get_settings().AIRLLM_MODEL,
                attempt=attempt,
                duration_ms=dt_ms,
            )
            if text:
                return text

            attempt += 1
            self._token_usage["reprompts"] = attempt
            log.warning(
                "empty code response, reprompting",
                model=get_settings().AIRLLM_MODEL,
                attempt=attempt,
            )

        return text

    def complete_vision(
        self,
        system_prompt: str,
        user_prompt: str,
        image_data: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        raise NotImplementedError("Vision not supported by AirLLM provider")

    def chat(
        self,
        messages: list[dict],
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        raise NotImplementedError("Chat not supported by AirLLM provider")

    def health(self) -> bool:
        try:
            from airllm import AutoModel
            return True
        except ImportError:
            return False


def _detect_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"
