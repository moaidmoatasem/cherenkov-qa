"""tests/unit/test_openclaw_notify.py — openclaw notification wiring.

Both wiring branches in OpenClawAdapter.__init__ were dead on arrival:
the Slack branch called SlackNotifier(url) (ctor took no args) and
registered a nonexistent .notify; the webhook branch registered a
nonexistent self._generic_webhook_notify. These tests pin the repaired
NotifyCallback contract (Callable[[HitlEnvelope], None]) on both paths.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from cherenkov.adapters.notifiers.slack import SlackNotifier
from cherenkov.hitl.contracts import HitlEnvelope, HitlError, ok_envelope
from cherenkov.openclaw.adapter import OpenClawAdapter
from cherenkov.openclaw.contracts import OpenClawConfig


def _adapter(endpoint: str) -> OpenClawAdapter:
    return OpenClawAdapter(
        queue=MagicMock(),
        feedback_store=MagicMock(),
        config=OpenClawConfig(notification_endpoint=endpoint),
    )


def test_slack_notifier_accepts_url_and_posts_envelope():
    notifier = SlackNotifier("https://hooks.slack.com/services/T/B/x")
    assert notifier.webhook_url == "https://hooks.slack.com/services/T/B/x"
    with patch("cherenkov.adapters.notifiers.slack.requests.post") as post:
        post.return_value.status_code = 200
        notifier.notify(ok_envelope(command="hitl.approve", payload={"id": "42"}))
    post.assert_called_once()
    assert "hitl.approve" in post.call_args.kwargs["json"]["text"]


def test_slack_notify_includes_error_message():
    notifier = SlackNotifier("https://hooks.slack.com/services/T/B/x")
    envelope = HitlEnvelope(
        ok=False,
        command="hitl.reject",
        error=HitlError(code="E1", message="quorum not reached"),
    )
    with patch("cherenkov.adapters.notifiers.slack.requests.post") as post:
        post.return_value.status_code = 200
        notifier.notify(envelope)
    assert "quorum not reached" in post.call_args.kwargs["json"]["text"]


def test_slack_notify_noops_without_url(monkeypatch):
    monkeypatch.delenv("CHERENKOV_SLACK_WEBHOOK_URL", raising=False)
    notifier = SlackNotifier()
    with patch("cherenkov.adapters.notifiers.slack.requests.post") as post:
        notifier.notify(ok_envelope(command="noop", payload=None))
    post.assert_not_called()


def test_adapter_wires_slack_branch_without_crashing():
    adapter = _adapter("https://hooks.slack.com/services/T/B/x")
    assert len(adapter._notify_callbacks) == 1
    assert callable(adapter._notify_callbacks[0])


def test_adapter_wires_webhook_branch_without_crashing():
    adapter = _adapter("https://example.com/hook")
    assert len(adapter._notify_callbacks) == 1
    assert callable(adapter._notify_callbacks[0])
