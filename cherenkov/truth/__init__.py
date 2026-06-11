"""
CHERENKOV Truth Model — Embedding index and source adapters.

This package provides:
- EmbeddingIndex: Vector index over claims for semantic search
- embed_text: Embed text using Ollama's nomic-embed-text model
- Source adapters: Extract claims from OpenAPI specs, traffic (HAR), and DB schemas
"""

try:
    from cherenkov.truth.index import EmbeddingIndex, embed_text
    _index_available = True
except ImportError:
    EmbeddingIndex = None  # type: ignore[assignment,misc]
    embed_text = None  # type: ignore[assignment]
    _index_available = False

__all__ = ["EmbeddingIndex", "embed_text"]
