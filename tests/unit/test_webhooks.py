import unittest
from unittest.mock import MagicMock, patch

import requests

from cherenkov.webhooks.dispatcher import HttpWebhookDispatcher, WebhookEvent


class TestHttpWebhookDispatcher(unittest.TestCase):
    @patch('requests.post')
    def test_dispatch_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dispatcher = HttpWebhookDispatcher("http://dummy.url")
        event = WebhookEvent("test_complete", {"id": 123})
        result = dispatcher.dispatch(event)

        self.assertTrue(result)
        mock_post.assert_called_once_with(
            "http://dummy.url",
            json={"type": "test_complete", "data": {"id": 123}},
            timeout=5
        )

    @patch('requests.post')
    def test_dispatch_retry_failure(self, mock_post):
        mock_post.side_effect = requests.RequestException("Network Error")

        dispatcher = HttpWebhookDispatcher("http://dummy.url", max_retries=2)
        event = WebhookEvent("test_complete", {"id": 123})
        result = dispatcher.dispatch(event)

        self.assertFalse(result)
        self.assertEqual(mock_post.call_count, 2)

if __name__ == '__main__':
    unittest.main()
