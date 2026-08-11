"""Unit tests for cherenkov/web/pr_comments.py and PR comment webhook (#766)."""
from __future__ import annotations

import os

os.environ.setdefault("CHERENKOV_ENV", "development")

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from cherenkov.web import pr_comments
from cherenkov.web.api import app


class TestFormatCoverageComment:
    """Placeholder docstring.

<description>"""
    def test_format_includes_header(self):
        """Placeholder docstring.

:return: <description>"""
        coverage = {
            "coveragePct": 75.0,
            "testedCount": 3,
            "totalEndpoints": 4,
            "openIssueCount": 1,
            "endpoints": [],
        }
        comment = pr_comments.format_coverage_comment(coverage)
        assert "## Spec coverage report" in comment
        assert "Coverage" in comment

    def test_format_shows_percentage(self):
        """Placeholder docstring.

:return: <description>"""
        coverage = {
            "coveragePct": 50.0,
            "testedCount": 2,
            "totalEndpoints": 4,
            "openIssueCount": 0,
            "endpoints": [],
        }
        comment = pr_comments.format_coverage_comment(coverage)
        assert "50.0%" in comment
        assert "(2/4" in comment
        assert "Open divergences:** 0" in comment

    def test_format_shows_gaps(self):
        """Placeholder docstring.

:return: <description>"""
        coverage = {
            "coveragePct": 25.0,
            "testedCount": 1,
            "totalEndpoints": 4,
            "openIssueCount": 0,
            "endpoints": [
                {"method": "GET", "path": "/pets", "tested": True, "divergenceCount": 0, "activeSeverity": None},
                {"method": "POST", "path": "/pets", "tested": False, "divergenceCount": 0, "activeSeverity": None},
                {"method": "DELETE", "path": "/pets/{id}", "tested": False, "divergenceCount": 0, "activeSeverity": None},
            ],
        }
        comment = pr_comments.format_coverage_comment(coverage)
        assert "### Untested endpoints (gaps)" in comment
        assert "| Method | Path |" in comment
        assert "/pets/{id}" in comment

    def test_format_shows_active_divergences(self):
        """Placeholder docstring.

:return: <description>"""
        coverage = {
            "coveragePct": 50.0,
            "testedCount": 2,
            "totalEndpoints": 2,
            "openIssueCount": 1,
            "endpoints": [
                {"method": "GET", "path": "/pets", "tested": True, "divergenceCount": 1, "activeSeverity": "high"},
            ],
        }
        comment = pr_comments.format_coverage_comment(coverage)
        assert "### Endpoints with active divergences" in comment
        assert "| Severity | Divergences |" in comment
        assert "high" in comment

    def test_format_omits_empty_sections(self):
        """Placeholder docstring.

:return: <description>"""
        coverage = {
            "coveragePct": 100.0,
            "testedCount": 1,
            "totalEndpoints": 1,
            "openIssueCount": 0,
            "endpoints": [
                {"method": "GET", "path": "/pets", "tested": True, "divergenceCount": 0, "activeSeverity": None},
            ],
        }
        comment = pr_comments.format_coverage_comment(coverage)
        assert "### Untested endpoints" not in comment
        assert "### Endpoints with active divergences" not in comment

    def test_format_includes_generator_footer(self):
        """Placeholder docstring.

:return: <description>"""
        coverage = {
            "coveragePct": 100.0,
            "testedCount": 1,
            "totalEndpoints": 1,
            "openIssueCount": 0,
            "endpoints": [],
        }
        comment = pr_comments.format_coverage_comment(coverage)
        assert "CHERENKOV-QA" in comment

    def test_format_limits_gap_list(self):
        """Placeholder docstring.

:return: <description>"""
        coverage = {
            "coveragePct": 0.0,
            "testedCount": 0,
            "totalEndpoints": 25,
            "openIssueCount": 0,
            "endpoints": [
                {"method": "GET", "path": f"/ep{i}", "tested": False, "divergenceCount": 0, "activeSeverity": None}
                for i in range(25)
    """Placeholder docstring.

<description>"""
            ],
        }
        comment = pr_comments.format_coverage_comment(coverage)
        assert "..._ more_" in comment or "5 more" in comment


class TestShouldComment:
    @pytest.mark.parametrize("action", ["opened", "synchronize", "reopened", "ready_for_review"])
    def test_actions_that_trigger_comment(self, action):
        """Placeholder docstring.

:param action: <description>
:return: <description>"""
    """Placeholder docstring.

<description>"""
        assert pr_comments.should_comment(action) is True

    @pytest.mark.parametrize("action", ["closed", "edited", "labeled", "", "unknown"])
    def test_actions_that_do_not_trigger(self, action):
        """Placeholder docstring.

:param action: <description>
:return: <description>"""
        assert pr_comments.should_comment(action) is False


class TestBuildCommentBodyIntegration:
    def test_build_comment_body_uses_coverage_service(self):
        """Placeholder docstring.

:return: <description>"""
        fake_map = {
            "coveragePct": 50.0,
            "testedCount": 2,
            "totalEndpoints": 4,
    """Placeholder docstring.

<description>"""
            "openIssueCount": 1,
            "endpoints": [],
        }
        with patch("cherenkov.web.coverage_map.build_coverage_map", return_value=fake_map):
            body = pr_comments.build_comment_body()
        assert "50.0%" in body
        assert "Spec coverage report" in body


class TestGitHubClient:
    def test_post_pr_comment_success(self):
        """Placeholder docstring.

:return: <description>"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"html_url": "https://github.com/x/y/pull/1#issuecomment-1"}

        with patch("requests.post", return_value=mock_resp):
            client = pr_comments.GitHubClient(token="fake-token")
            result = client.post_pr_comment("owner/repo", 1, "test body")

        assert result["html_url"] == "https://github.com/x/y/pull/1#issuecomment-1"

    def test_post_pr_comment_raises_without_token(self):
        """Placeholder docstring.

:return: <description>"""
        client = pr_comments.GitHubClient(token=None)
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
            client.post_pr_comment("owner/repo", 1, "test body")
    """Placeholder docstring.

<description>"""

    def test_post_pr_comment_raises_on_http_error(self):
        """Placeholder docstring.

:return: <description>"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = __import__("requests").HTTPError("403")

        with patch("requests.post", return_value=mock_resp):
            client = pr_comments.GitHubClient(token="fake-token")
            with pytest.raises(__import__("requests").HTTPError):
                client.post_pr_comment("owner/repo", 1, "test body")


class TestPostCoverageComment:
    def test_post_coverage_comment_calls_github(self):
        """Placeholder docstring.

:return: <description>"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"html_url": "https://github.com/x/y/pull/1#issuecomment-1"}

        fake_map = {
            "coveragePct": 100.0,
            "testedCount": 1,
            "totalEndpoints": 1,
    """Placeholder docstring.

<description>"""
            "openIssueCount": 0,
            "endpoints": [],
        }
        with (
            patch("cherenkov.web.coverage_map.build_coverage_map", return_value=fake_map),
            patch("cherenkov.web.pr_comments._get_github_token", return_value="fake-token"),
            patch("requests.post", return_value=mock_resp),
        ):
            result = pr_comments.post_coverage_comment("owner/repo", 1)

        assert "html_url" in result


class TestWebhookIntegration:
    @pytest.fixture
    def _isolate_store(self):
        from cherenkov.persistence import run_store as rs_module
        with patch.object(rs_module, "_store", None):
            with patch.object(rs_module, "get_run_store", return_value=None):
                yield

    @staticmethod
    def _close_coro(coro):
        """Mock side_effect that closes the coroutine passed to create_task."""
        coro.close()
        return MagicMock()

    def test_pr_opened_queues_comment(self, _isolate_store):
        """Placeholder docstring.

:param _isolate_store: <description>
:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 42},
        }
        with (
            patch("cherenkov.web.routes.webhooks_github._get_github_token_safely", return_value="token"),
            patch("requests.post", return_value=MagicMock(
                raise_for_status=lambda *a, **k: None,
                json=lambda *a, **k: {"html_url": "http://x/y"},
            )),
            patch("asyncio.create_task", side_effect=self._close_coro) as mock_task,
        ):
            r = client.post(
                "/api/v1/webhooks/github/events",
                json=payload,
                headers={"x-github-event": "pull_request"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["coverage_comment"] == "queued"
        assert mock_task.called

    def test_pr_closed_does_not_comment(self, _isolate_store):
        """Placeholder docstring.

:param _isolate_store: <description>
:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
        payload = {
            "action": "closed",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 42},
        }
        with (
            patch("requests.post") as mock_post,
            patch("asyncio.create_task") as mock_task,
        ):
            r = client.post(
                "/api/v1/webhooks/github/events",
                json=payload,
                headers={"x-github-event": "pull_request"},
            )
        assert r.status_code == 200
        assert mock_post.called is False
        assert mock_task.called is False

    def test_pr_opened_no_token_skips_comment(self, _isolate_store):
        """Placeholder docstring.

:param _isolate_store: <description>
:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 42},
        }
        with patch("cherenkov.web.routes.webhooks_github._get_github_token_safely", return_value=""):
            r = client.post(
                "/api/v1/webhooks/github/events",
                json=payload,
                headers={"x-github-event": "pull_request"},
            )
        assert r.status_code == 200

    def test_non_pr_event_ignored(self, _isolate_store):
        """Placeholder docstring.

:param _isolate_store: <description>
:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/api/v1/webhooks/github/events",
            json={"action": "created", "repository": {"full_name": "x/y"}},
            headers={"x-github-event": "issues"},
        )
        assert r.status_code == 200

    def test_push_event_ignored(self, _isolate_store):
        """Placeholder docstring.

:param _isolate_store: <description>
:return: <description>"""
        client = TestClient(app, raise_server_exceptions=False)
        with patch("asyncio.create_task") as mock_task:
            r = client.post(
                "/api/v1/webhooks/github/events",
                json={"ref": "refs/heads/main", "repository": {"full_name": "x/y"}},
                headers={"x-github-event": "push"},
            )
        assert r.status_code == 200
        assert mock_task.called is False