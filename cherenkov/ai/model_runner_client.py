"""
CHERENKOV ai/model_runner_client.py — Docker Model Runner adapter.
Authority: v3.1 + delta.

Anti-lock-in: conforms to the same interface as OllamaClient.
Non-Docker fallback: ollama_client.py.
"""

from __future__ import annotations

import json
import subprocess


class ModelRunnerClient:
    def __init__(self, model: str = "qwen2.5-coder:7b"):
        self.model = model

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        cmd = ["docker", "model", "run", self.model, "--prompt", prompt]
        if system_prompt:
            cmd += ["--system", system_prompt]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    def list_models(self) -> list[str]:
        result = subprocess.run(
            ["docker", "model", "list", "--format", "json"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return []
        try:
            return [m["name"] for m in json.loads(result.stdout)]
        except (json.JSONDecodeError, KeyError):
            return []
