"""
cherenkov/rag/ — Issue #195: Semantic chunking / RAG for large OpenAPI specs.
Authority: v3.1 + delta.
"""
try:
    from cherenkov.rag.schema_index import SchemaIndex, embed_text, Chunk
    _schema_available = True
except ImportError:
    SchemaIndex = None  # type: ignore[assignment,misc]
    embed_text = None  # type: ignore[assignment]
    Chunk = None  # type: ignore[assignment,misc]
    _schema_available = False

from cherenkov.rag.mobile_index import MobileRAGIndex

__all__ = [
    "SchemaIndex",
    "embed_text",
    "Chunk",
    "MobileRAGIndex",
]
