"""Unit tests for Buf Schema Registry Client."""

import unittest
from unittest.mock import patch, MagicMock

from cherenkov.validate.buf_registry import BufRegistryClient


class TestBufRegistryClient(unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_fetch_schema_success(self, mock_urlopen):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"repository": "test"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with patch.dict("os.environ", {"BUF_TOKEN": "fake-token"}):
            client = BufRegistryClient()
            result = client.fetch_schema("acme/paymentapis")
            self.assertIsNotNone(result)
            self.assertIn("repository", result)

    def test_fetch_schema_no_token(self):
        with patch.dict("os.environ", {}, clear=True):
            client = BufRegistryClient()
            result = client.fetch_schema("acme/paymentapis")
            self.assertIsNone(result)

    def test_fetch_schema_invalid_module_name(self):
        with patch.dict("os.environ", {"BUF_TOKEN": "fake-token"}):
            client = BufRegistryClient()
            result = client.fetch_schema("invalidname")
            self.assertIsNone(result)

    @patch("urllib.request.urlopen")
    def test_fetch_proto_content(self, mock_urlopen):
        # Setup mock for fetch_schema call
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"repository": "test"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with patch.dict("os.environ", {"BUF_TOKEN": "fake-token"}):
            client = BufRegistryClient()
            content = client.fetch_proto_content("acme/paymentapis")
            self.assertIsNotNone(content)
            self.assertIn("BufTestService", content)

if __name__ == "__main__":
    unittest.main()
