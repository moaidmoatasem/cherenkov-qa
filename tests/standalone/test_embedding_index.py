"""
test_embedding_index.py — Unit tests for the E2-3 Embedding Index.
"""
import unittest
import sys
from unittest.mock import patch, MagicMock

try:
    import numpy  # noqa: F401
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False

from cherenkov.core.contracts import Claim, Provenance

if _NUMPY_AVAILABLE:
    from cherenkov.truth.index import EmbeddingIndex
else:
    EmbeddingIndex = None


@unittest.skipUnless(_NUMPY_AVAILABLE, "numpy not installed — skipping EmbeddingIndex tests")
class TestEmbeddingIndex(unittest.TestCase):

    def setUp(self):
        self.index = EmbeddingIndex(model="nomic-embed-text")
        self.prov = Provenance(
            source_type="spec",
            source_uri="test.json",
        )

    @patch("cherenkov.truth.index.requests.post")
    def test_embedding_and_retrieval(self, mock_post):
        # 1. Setup mock embeddings returned by Ollama for our query & claims
        # Let's map prompts to 3D mock embeddings:
        # - Query text "query" maps to [1.0, 0.0, 0.0]
        # - Claim 1 maps to [0.9, 0.1, 0.0] (highly similar to query)
        # - Claim 2 maps to [0.0, 1.0, 0.0] (orthogonal)
        # - Claim 3 maps to [-0.8, 0.0, 0.1] (dissimilar)
        
        embeddings_map = {
            "query": [1.0, 0.0, 0.0],
            "endpoint: POST /users -- {\"status\": 201}": [0.9, 0.1, 0.0],
            "shape: User -- {\"type\": \"object\"}": [0.0, 1.0, 0.0],
            "constraint: age >= 18 -- {\"min\": 18}": [-0.8, 0.0, 0.1],
        }

        def mock_post_side_effect(url, json, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            
            prompt = json.get("prompt")
            if not prompt:
                inputs = json.get("input", [])
                prompt = inputs[0] if inputs else ""
                
            embedding = embeddings_map.get(prompt, [0.0, 0.0, 0.0])
            
            if "/api/embed" in url:
                mock_resp.json.return_value = {"embeddings": [embedding]}
            else:
                mock_resp.json.return_value = {"embedding": embedding}
            return mock_resp

        mock_post.side_effect = mock_post_side_effect

        # 2. Populate the index
        c1 = Claim(
            id="c1",
            category="endpoint",
            subject="POST /users",
            value={"status": 201},
            provenance=self.prov,
        )

        c2 = Claim(
            id="c2",
            category="shape",
            subject="User",
            value={"type": "object"},
            provenance=self.prov,
        )

        c3 = Claim(
            id="c3",
            category="constraint",
            subject="age >= 18",
            value={"min": 18},
            provenance=self.prov,
        )

        self.index.add_claims([c1, c2, c3])
        self.assertEqual(self.index.count, 3)

        # 3. Query the index
        results = self.index.query("query", top_k=2)
        
        # Verify results
        self.assertEqual(len(results), 2)
        # Highly similar claim c1 should be the first result
        self.assertEqual(results[0][0].subject, "POST /users")
        self.assertGreater(results[0][1], 0.8) # Cosine similarity should be ~0.9
        
        # Next should be c2 (orthogonal, similarity ~0.0)
        self.assertEqual(results[1][0].subject, "User")
        self.assertAlmostEqual(results[1][1], 0.0, places=5)

    def test_clear_index(self):
        c = Claim(
            id="c",
            category="c",
            subject="s",
            value="v",
            provenance=self.prov,
        )
        
        self.index.add_claim(c)
        self.assertEqual(self.index.count, 1)
        
        self.index.clear()
        self.assertEqual(self.index.count, 0)


if __name__ == "__main__":
    unittest.main()
