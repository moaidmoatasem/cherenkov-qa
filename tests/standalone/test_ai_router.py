import os
import unittest
from cherenkov.ai.router import InferenceRouter

class TestInferenceRouter(unittest.TestCase):
    def test_router_resolution(self):
        # Default
        router = InferenceRouter(provider="ollama")
        client = router.resolve_client()
        self.assertEqual(client.__class__.__name__, "OllamaClient")
        
        # Anthropic
        router.set_provider("anthropic")
        client = router.resolve_client()
        self.assertEqual(client.__class__.__name__, "AnthropicInferenceClient")
        
        # Bedrock
        router.set_provider("bedrock")
        client = router.resolve_client()
        self.assertEqual(client.__class__.__name__, "BedrockInferenceClient")
        
        # HuggingFace
        router.set_provider("huggingface")
        client = router.resolve_client()
        self.assertEqual(client.__class__.__name__, "HuggingFaceInferenceClient")

if __name__ == "__main__":
    unittest.main()
