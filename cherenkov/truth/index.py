"""
cherenkov/truth/index.py — E2-3: Embedding index over claims.
Authority: v3.1 + delta.

Index claims via nomic-embed-text for retrieval by the Skeptic.
Uses numpy for cosine similarity (no external vector DB dependency).
"""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import requests

from cherenkov.core.config import Config
from cherenkov.core.contracts import Claim
from cherenkov.core.errors import get_logger


def _normalise(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def embed_text(text: str, model: str = "nomic-embed-text") -> list[float]:
    """Embed a single text string via Ollama's nomic-embed-text model."""
    resp = requests.post(
        Config.OLLAMA_URL,
        json={"model": model, "prompt": text, "stream": False},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("embedding", [])


class EmbeddingIndex:
    """In-memory embedding index over claims with cosine-similarity retrieval.

    Claims are embedded lazily on first query. The index is append-only during
    a session — callers add claims, then query top-k.
    """

    def __init__(self, model: str = "nomic-embed-text"):
        self._model = model
        self._claims: list[Claim] = []
        self._embeddings: list[np.ndarray] = []
        self._log = get_logger("embedding-index")

    def add_claim(self, claim: Claim) -> None:
        self._claims.append(claim)

    def add_claims(self, claims: list[Claim]) -> None:
        self._claims.extend(claims)

    @property
    def count(self) -> int:
        return len(self._claims)

    def _embed_all(self) -> None:
        if len(self._embeddings) == len(self._claims):
            return
        start = len(self._embeddings)
        for i in range(start, len(self._claims)):
            text = f"{self._claims[i].category}: {self._claims[i].subject} -- {json.dumps(self._claims[i].value)}"
            vec = embed_text(text, self._model)
            self._embeddings.append(_normalise(np.array(vec, dtype=np.float32)))
            if (i + 1) % 10 == 0:
                self._log.info("embedded", count=i + 1, total=len(self._claims))

    def query(self, text: str, top_k: int = 5) -> list[tuple[Claim, float]]:
        """Return top-k claims most similar to `text`, with cosine similarity scores."""
        if not self._claims:
            return []

        self._embed_all()
        q_vec = _normalise(np.array(embed_text(text, self._model), dtype=np.float32))

        scores = []
        for i, emb in enumerate(self._embeddings):
            sim = float(np.dot(q_vec, emb))
            scores.append((i, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        top = scores[:top_k]

        return [(self._claims[i], score) for i, score in top]

    def query_by_claim(self, claim: Claim, top_k: int = 5) -> list[tuple[Claim, float]]:
        """Return top-k claims similar to the given claim."""
        text = f"{claim.category}: {claim.subject} -- {json.dumps(claim.value)}"
        return self.query(text, top_k=top_k)

    def clear(self) -> None:
        self._claims.clear()
        self._embeddings.clear()
