"""
CHERENKOV Truth Model — Embedding index and source adapters.

This package provides:
- EmbeddingIndex: Vector index over claims for semantic search
- embed_text: Embed text using Ollama's nomic-embed-text model
- Source adapters: Extract claims from OpenAPI specs, traffic (HAR), and DB schemas
"""

from cherenkov.truth.index import EmbeddingIndex, embed_text

__all__ = ["EmbeddingIndex", "embed_text"]
