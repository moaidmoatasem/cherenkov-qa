"""
CHERENKOV ai/bedrock_client.py — AWS Bedrock InferenceClient.
"""

from __future__ import annotations

import os
import json
import re
import time

from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import strip_think, _try_json
from cherenkov.core.errors import ProviderJSONError, get_logger

_log = get_logger("BEDROCK_CLIENT")

_DEFAULT_MODEL = os.getenv("CHERENKOV_BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")


class BedrockInferenceClient(InferenceClient):
    """AWS Bedrock implementation of InferenceClient."""

    def __init__(self) -> None:
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self._token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reprompts": 0,
        }
        self._client = None

    def _get_client(self):
        if self._client:
            return self._client
        try:
            import boto3
        except ImportError as exc:
            raise ImportError(
                "boto3 package not installed. Run: pip install boto3"
            ) from exc
        
        self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def _complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
    ) -> str:
        t0 = time.time()
        client = self._get_client()

        # Build payload assuming anthropic models are heavily used on Bedrock
        # We target the standard Bedrock anthropic.claude-3 Converse API format if supported,
        # but for simplicity we will use InvokeModel with anthropic payload.
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_prompt}],
                }
            ],
        }

        response = client.invoke_model(
            modelId=model,
            body=json.dumps(body),
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response.get('body').read())
        text = response_body.get('content')[0].get('text')
        
        input_tokens = response_body.get('usage', {}).get('input_tokens', 0)
        output_tokens = response_body.get('usage', {}).get('output_tokens', 0)

        elapsed = int((time.time() - t0) * 1000)
        self._token_usage["prompt_tokens"] += input_tokens
        self._token_usage["completion_tokens"] += output_tokens
        _log.info(
            "bedrock completion",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=elapsed,
        )
        return text

    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        model = model or _DEFAULT_MODEL
        raw = self._complete(system_prompt, user_prompt, model, temperature=temperature)
        code = strip_think(raw)
        fenced = re.search(r"```(?:typescript|ts|python)?\s*([\s\S]+?)```", code)
        if fenced:
            code = fenced.group(1).strip()
        return code

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
        model = model or _DEFAULT_MODEL
        for attempt in range(max_reprompts + 1):
            raw = self._complete(
                system_prompt, user_prompt, model, temperature=temperature
            )
            text = strip_think(raw)
            fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
            if fenced:
                text = fenced.group(1).strip()
            else:
                start = next((i for i, c in enumerate(text) if c in "{["), None)
                if start is not None:
                    text = text[start:]
            parsed = _try_json(text)
            if parsed is not None:
                return parsed
            self._token_usage["reprompts"] += 1
        raise ProviderJSONError(
            f"Bedrock failed to return valid JSON after {max_reprompts + 1} attempts"
        )
