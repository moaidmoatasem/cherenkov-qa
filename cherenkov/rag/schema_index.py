"""
cherenkov/rag/schema_index.py — Issue #195: Semantic chunking / RAG for large specs.

Indexes OpenAPI component schemas via nomic-embed-text embeddings and
retrieves semantically relevant schemas per endpoint + mutation.

This is an alternative populator of EndpointSlice.schemas — no change to
the generate/review contract downstream.
"""

from __future__ import annotations

import json
import hashlib
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests

from cherenkov.core.settings import get_settings
from cherenkov.core.errors import get_logger


# ── Chunk data model ────────────────────────────────────────────────────────
class Chunk:
    """A single indexed schema chunk: one component schema entry."""

    def __init__(self, name: str, text: str, source: dict[str, Any]):
        self.name = name
        self.text = text
        self.source = source
        self.embedding: list[float] | None = None


# ── Embedding helpers (reuses pattern from cherenkov/truth/index.py) ─────────
def _normalise(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def embed_text(text: str, model: str = "nomic-embed-text") -> list[float]:
    """Embed a single text string via Ollama's nomic-embed-text model."""
    base_url = get_settings().OLLAMA_URL.rsplit("/api/generate", 1)[0]

    try:
        resp = requests.post(
            f"{base_url}/api/embed",
            json={"model": model, "input": [text]},
            timeout=30,
        )
        if resp.status_code == 200:
            embeddings = resp.json().get("embeddings", [])
            if embeddings:
                return embeddings[0]
    except Exception:
        pass

    resp = requests.post(
        f"{base_url}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("embedding", [])


# ── Schema Index (RAG) ──────────────────────────────────────────────────────
class SchemaIndex:
    """In-memory embedding index over OpenAPI component schemas with cosine-similarity retrieval.

    Indexes once per spec (cached to disk keyed by spec hash), then
    queries per (endpoint, mutation) to retrieve only the semantically
    relevant schemas needed for test generation.
    """

    def __init__(self, cache_dir: str = ".cherenkov/rag_cache"):
        self._log = get_logger("schema-index")
        self._chunks: list[Chunk] = []
        self._embeddings: list[np.ndarray] = []
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def count(self) -> int:
        return len(self._chunks)

    # ── Chunk preparation ────────────────────────────────────────────────

    @classmethod
    def _build_chunk_text(cls, name: str, schema: dict[str, Any]) -> str:
        """Build a flat text representation of one component schema for embedding."""
        parts = [f"schema: {name}"]
        if "description" in schema:
            parts.append(f"description: {schema['description']}")
        if "type" in schema:
            parts.append(f"type: {schema['type']}")
        properties = schema.get("properties", {})
        if properties:
            prop_lines = []
            for pname, pschema in properties.items():
                ptype = (
                    pschema.get("type", "unknown")
                    if isinstance(pschema, dict)
                    else "unknown"
                )
                pdesc = (
                    pschema.get("description", "") if isinstance(pschema, dict) else ""
                )
                prop_lines.append(f"{pname} ({ptype}){': ' + pdesc if pdesc else ''}")
            parts.append("properties: " + ", ".join(prop_lines))
        if "required" in schema:
            parts.append("required: " + ", ".join(schema["required"]))
        return " | ".join(parts)

    @classmethod
    def _get_spec_hash(cls, spec: dict[str, Any]) -> str:
        """Compute a stable hash of the spec's component schemas for cache invalidation."""
        schemas = spec.get("components", {}).get("schemas", {})
        return hashlib.sha256(json.dumps(schemas, sort_keys=True).encode()).hexdigest()[
            :16
        ]

    def _cache_path(self, spec_hash: str) -> Path:
        return self._cache_dir / f"rag_{spec_hash}.json"

    # ── Build index ──────────────────────────────────────────────────────

    def index_spec(self, spec: dict[str, Any]) -> None:
        """Index all component schemas from an OpenAPI spec, using disk cache."""
        spec_hash = self._get_spec_hash(spec)
        cache_path = self._cache_path(spec_hash)

        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                for item in data:
                    chunk = Chunk(item["name"], item["text"], item["source"])
                    self._chunks.append(chunk)
                self._log.info(
                    "loaded from cache", spec_hash=spec_hash, chunks=len(self._chunks)
                )
                return
            except Exception as e:
                self._log.warning("cache load failed, re-indexing", error=str(e))

        schemas = spec.get("components", {}).get("schemas", {})
        t0 = time.time()
        for name, schema in schemas.items():
            if not isinstance(schema, dict):
                continue
            text = self._build_chunk_text(name, schema)
            self._chunks.append(Chunk(name=name, text=text, source=schema))

        # Embed all chunks
        self._embed_all()

        # Write cache
        try:
            cache_data = [
                {"name": c.name, "text": c.text, "source": c.source}
                for c in self._chunks
            ]
            cache_path.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
        except Exception as e:
            self._log.warning("cache write failed", error=str(e))

        dt = int((time.time() - t0) * 1000)
        self._log.info("indexed spec", chunks=len(self._chunks), duration_ms=dt)

    def _embed_all(self) -> None:
        if len(self._embeddings) == len(self._chunks):
            return
        start = len(self._embeddings)
        for i in range(start, len(self._chunks)):
            vec = embed_text(self._chunks[i].text)
            self._chunks[i].embedding = vec
            self._embeddings.append(_normalise(np.array(vec, dtype=np.float32)))
            if (i + 1) % 10 == 0:
                self._log.info("embedded", count=i + 1, total=len(self._chunks))

    # ── Retrieve relevant schemas ────────────────────────────────────────

    def retrieve(
        self,
        query_text: str,
        explicit_refs: set[str] | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Return a dict of schemas relevant to the given query.

        Always unions with explicitly-named $ref components (never drop
        correctness-critical refs). Retrieval augments, it doesn't replace.
        """
        result: dict[str, Any] = {}

        # Always include explicitly-referenced schemas
        if explicit_refs:
            for chunk in self._chunks:
                if chunk.name in explicit_refs:
                    result[chunk.name] = chunk.source
                    explicit_refs.discard(chunk.name)

        if not self._chunks:
            return result

        self._embed_all()
        q_vec = _normalise(np.array(embed_text(query_text), dtype=np.float32))

        scores: list[tuple[int, float]] = []
        for i, emb in enumerate(self._embeddings):
            sim = float(np.dot(q_vec, emb))
            scores.append((i, sim))

        scores.sort(key=lambda x: x[1], reverse=True)

        for idx, score in scores[:top_k]:
            name = self._chunks[idx].name
            if name not in result:
                result[name] = self._chunks[idx].source

        return result

    def clear(self) -> None:
        self._chunks.clear()
        self._embeddings.clear()
