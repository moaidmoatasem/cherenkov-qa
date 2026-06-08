import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from cherenkov.substrate.providers.localai import LocalAIVLMProvider


class TestLocalAIVLMProvider(unittest.TestCase):
    def setUp(self):
        self.provider = LocalAIVLMProvider(
            base_url="http://localhost:8080",
            model="llava",
        )

    def test_init(self):
        self.assertEqual(self.provider.base_url, "http://localhost:8080")
        self.assertEqual(self.provider.model, "llava")

    def test_init_from_config(self):
        with patch("cherenkov.substrate.providers.localai.Config.VLM_LOCALAI_URL", "http://10.0.0.1:8080"):
            with patch("cherenkov.substrate.providers.localai.Config.VLM_LOCALAI_MODEL", "qwen2.5-vl:7b"):
                p = LocalAIVLMProvider()
                self.assertEqual(p.base_url, "http://10.0.0.1:8080")
                self.assertEqual(p.model, "qwen2.5-vl:7b")

    def test_health_unavailable(self):
        self.assertFalse(self.provider.health())

    def test_health_timeout(self):
        import requests
        with patch("cherenkov.substrate.providers.localai.requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("timeout")
            self.assertFalse(self.provider.health())

    def test_health_available(self):
        with patch("cherenkov.substrate.providers.localai.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            self.assertTrue(self.provider.health())

    @patch("cherenkov.substrate.providers.localai.requests.post")
    @patch("cherenkov.substrate.providers.localai._encode_image")
    def test_describe_image(self, mock_encode, mock_post):
        mock_encode.return_value = "base64data"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "A cat sitting on a chair."}}]
        }
        mock_post.return_value = mock_resp

        tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tf.write(b"fake-image-data")
        tf.close()

        result = self.provider.describe_image(tf.name, "What is in this image?")
        self.assertEqual(result, "A cat sitting on a chair.")
        os.unlink(tf.name)

    @patch("cherenkov.substrate.providers.localai.requests.post")
    @patch("cherenkov.substrate.providers.localai._encode_image")
    def test_compare_images(self, mock_encode, mock_post):
        mock_encode.return_value = "base64data"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "description": "Layout shifted right",
                        "kind": "HARMLESS_SHIFT",
                        "confidence": 0.85,
                    })
                }
            }]
        }
        mock_post.return_value = mock_resp

        tf1 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tf2 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tf1.write(b"baseline")
        tf2.write(b"actual")
        tf1.close()
        tf2.close()

        result = self.provider.compare_images(tf1.name, tf2.name)
        self.assertEqual(result["kind"], "HARMLESS_SHIFT")
        self.assertEqual(result["confidence"], 0.85)
        os.unlink(tf1.name)
        os.unlink(tf2.name)

    @patch("cherenkov.substrate.providers.localai.requests.post")
    @patch("cherenkov.substrate.providers.localai._encode_image")
    def test_compare_images_fallback_on_bad_json(self, mock_encode, mock_post):
        mock_encode.return_value = "data"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "not valid json"}}]
        }
        mock_post.return_value = mock_resp

        tf1 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tf2 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tf1.close()
        tf2.close()

        result = self.provider.compare_images(tf1.name, tf2.name)
        self.assertEqual(result["kind"], "UNKNOWN")
        self.assertEqual(result["confidence"], 0.0)
        os.unlink(tf1.name)
        os.unlink(tf2.name)


class TestLocalAIVLMProviderEdgeCases(unittest.TestCase):
    def test_describe_image_file_not_found(self):
        provider = LocalAIVLMProvider()
        with self.assertRaises(FileNotFoundError):
            provider.describe_image("/nonexistent/image.png")

    def test_encode_image(self):
        from cherenkov.substrate.providers.localai import _encode_image
        tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tf.write(b"hello")
        tf.close()
        encoded = _encode_image(tf.name)
        self.assertIsInstance(encoded, str)
        self.assertTrue(len(encoded) > 0)
        os.unlink(tf.name)
