import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from cherenkov.substrate.providers.localai import LocalAIVLMProvider


def test_localai_provider_init():
    provider = LocalAIVLMProvider(base_url="http://localhost:8080", model="llava")
    assert provider.base_url == "http://localhost:8080"
    assert provider.model == "llava"


def test_localai_provider_init_from_config():
    with patch(
        "cherenkov.substrate.providers.localai.get_settings().VLM_LOCALAI_URL",
        "http://10.0.0.1:8080",
    ):
        with patch(
            "cherenkov.substrate.providers.localai.get_settings().VLM_LOCALAI_MODEL",
            "qwen2.5-vl:7b",
        ):
            p = LocalAIVLMProvider()
            assert p.base_url == "http://10.0.0.1:8080"
            assert p.model == "qwen2.5-vl:7b"


def test_localai_health_unavailable():
    provider = LocalAIVLMProvider(base_url="http://localhost:8080", model="llava")
    assert not provider.health()


def test_localai_health_timeout():
    import requests

    provider = LocalAIVLMProvider(base_url="http://localhost:8080", model="llava")
    with patch("cherenkov.substrate.providers.localai.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("timeout")
        assert not provider.health()


def test_localai_health_available():
    provider = LocalAIVLMProvider(base_url="http://localhost:8080", model="llava")
    with patch("cherenkov.substrate.providers.localai.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        assert provider.health()


@patch("cherenkov.substrate.providers.localai.requests.post")
@patch("cherenkov.substrate.providers.localai._encode_image")
def test_localai_describe_image(mock_encode, mock_post):
    provider = LocalAIVLMProvider(base_url="http://localhost:8080", model="llava")
    mock_encode.return_value = "base64data"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "A cat sitting on a chair."}}]
    }
    mock_post.return_value = mock_resp

    tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tf.write(b"fake-image-data")
    tf.close()

    result = provider.describe_image(tf.name, "What is in this image?")
    assert result == "A cat sitting on a chair."
    os.unlink(tf.name)


@patch("cherenkov.substrate.providers.localai.requests.post")
@patch("cherenkov.substrate.providers.localai._encode_image")
def test_localai_compare_images(mock_encode, mock_post):
    provider = LocalAIVLMProvider(base_url="http://localhost:8080", model="llava")
    mock_encode.return_value = "base64data"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "description": "Layout shifted right",
                            "kind": "HARMLESS_SHIFT",
                            "confidence": 0.85,
                        }
                    )
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    tf1 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tf2 = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tf1.write(b"baseline")
    tf2.write(b"actual")
    tf1.close()
    tf2.close()

    result = provider.compare_images(tf1.name, tf2.name)
    assert result["kind"] == "HARMLESS_SHIFT"
    assert result["confidence"] == 0.85
    os.unlink(tf1.name)
    os.unlink(tf2.name)


@patch("cherenkov.substrate.providers.localai.requests.post")
@patch("cherenkov.substrate.providers.localai._encode_image")
def test_localai_compare_images_fallback_on_bad_json(mock_encode, mock_post):
    provider = LocalAIVLMProvider(base_url="http://localhost:8080", model="llava")
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

    result = provider.compare_images(tf1.name, tf2.name)
    assert result["kind"] == "UNKNOWN"
    assert result["confidence"] == 0.0
    os.unlink(tf1.name)
    os.unlink(tf2.name)


def test_localai_describe_image_file_not_found():
    provider = LocalAIVLMProvider()
    with pytest.raises(FileNotFoundError):
        provider.describe_image("/nonexistent/image.png")


def test_localai_encode_image():
    from cherenkov.substrate.providers.localai import _encode_image

    tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tf.write(b"hello")
    tf.close()
    encoded = _encode_image(tf.name)
    assert isinstance(encoded, str)
    assert len(encoded) > 0
    os.unlink(tf.name)
