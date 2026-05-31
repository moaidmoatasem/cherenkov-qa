"""
CHERENKOV core/config.py — structured configuration and environment loading.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os

class Config:
    """Strongly-typed central configuration parser loading environment variables with safe defaults."""
    
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    GEN_MODEL: str = os.getenv("GEN_MODEL", "qwen2.5-coder:7b")
    API_URL: str = os.getenv("API_URL", "http://localhost:8000")
    SCHEMA_DEPTH: int = int(os.getenv("SCHEMA_DEPTH", "1"))
    ERROR_THRESHOLD: int = int(os.getenv("ERROR_THRESHOLD", "2"))
    
    @classmethod
    def to_dict(cls) -> dict[str, str | int]:
        return {
            "OLLAMA_URL": cls.OLLAMA_URL,
            "GEN_MODEL": cls.GEN_MODEL,
            "API_URL": cls.API_URL,
            "SCHEMA_DEPTH": cls.SCHEMA_DEPTH,
            "ERROR_THRESHOLD": cls.ERROR_THRESHOLD,
        }
