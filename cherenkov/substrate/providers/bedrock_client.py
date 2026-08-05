"""
CHERENKOV ai/bedrock_client.py — AWS Bedrock InferenceClient.
"""

from __future__ import annotations

import json
import os
import time

from cherenkov.core.errors import get_logger
from cherenkov.substrate.providers.fenced_client import FencedCompletionClient

_log = get_logger("BEDROCK_CLIENT")

_DEFAULT_MODEL = os.getenv("CHERENKOV_BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")


class BedrockInferenceClient(FencedCompletionClient):
    """AWS Bedrock implementation of InferenceClient."""

    provider_label = "Bedrock"
    default_model = _DEFAULT_MODEL

    def __init__(self) -> None:
        super().__init__()
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self._client = None

    def _get_client(self):
        if self._client:
            return self._client
        try:
            import boto3
        except ImportError as exc:
            raise ImportError("boto3 package not installed. Run: pip install boto3") from exc

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
        t0 = time.monotonic()
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
            contentType="application/json",
        )

        response_body = json.loads(response.get("body").read())
        text = response_body.get("content")[0].get("text")

        input_tokens = response_body.get("usage", {}).get("input_tokens", 0)
        output_tokens = response_body.get("usage", {}).get("output_tokens", 0)

        elapsed = int((time.monotonic() - t0) * 1000)
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
