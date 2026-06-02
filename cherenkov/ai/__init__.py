# CHERENKOV ai sub-package
from cherenkov.ai.interface import InferenceClient
from cherenkov.ai.ollama_client import OllamaInferenceClient

__all__ = ["InferenceClient", "OllamaInferenceClient"]
