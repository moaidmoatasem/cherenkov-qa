from unittest.mock import patch, MagicMock
import pytest
from cherenkov.adapters.exporters.jira_client import JiraClient

@pytest.fixture
def configured_client():
    return JiraClient(url="https://jira.example.com", email="user@example.com", token="token")

@pytest.fixture
def unconfigured_client():
    return JiraClient(url="", email="", token="")

def test_is_configured(configured_client, unconfigured_client):
    assert configured_client.is_configured is True
    assert unconfigured_client.is_configured is False

@patch("cherenkov.adapters.exporters.jira_client.requests.post")
def test_create_issue_success(mock_post, configured_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "10000", "key": "QA-123"}
    mock_post.return_value = mock_resp

    result = configured_client.create_issue(
        project_key="QA",
        summary="Test summary",
        description="Test description",
        labels=["test"]
    )

    assert result["key"] == "QA-123"
    mock_post.assert_called_once()
    kwargs = mock_post.call_args[1]
    assert kwargs["json"]["fields"]["project"]["key"] == "QA"
    assert kwargs["json"]["fields"]["summary"] == "Test summary"
    assert kwargs["json"]["fields"]["labels"] == ["test"]
    assert "Test description" in str(kwargs["json"]["fields"]["description"])

def test_create_issue_unconfigured(unconfigured_client):
    with pytest.raises(ValueError, match="credentials not configured"):
        unconfigured_client.create_issue("QA", "Summary", "Desc")

@patch("cherenkov.adapters.exporters.jira_client.requests.post")
def test_link_test_run(mock_post, configured_client):
    mock_resp = MagicMock()
    mock_post.return_value = mock_resp

    configured_client.link_test_run(issue_key="QA-123", verdict_id="verdict-456")
    mock_post.assert_called_once()

@patch("cherenkov.adapters.exporters.jira_client.requests.post")
@patch("cherenkov.adapters.exporters.jira_client.requests.get")
def test_transition_issue(mock_get, mock_post, configured_client):
    mock_get_resp = MagicMock()
    mock_get_resp.json.return_value = {"transitions": [{"id": "21", "name": "Done"}]}
    mock_get.return_value = mock_get_resp
    
    mock_post_resp = MagicMock()
    mock_post.return_value = mock_post_resp

    configured_client.transition_issue(issue_key="QA-123", transition="Done")
    
    mock_get.assert_called_once()
    mock_post.assert_called_once()
    kwargs = mock_post.call_args[1]
    assert kwargs["json"]["transition"]["id"] == "21"

@patch("cherenkov.adapters.exporters.jira_client.requests.get")
def test_transition_issue_not_found(mock_get, configured_client):
    mock_get_resp = MagicMock()
    mock_get_resp.json.return_value = {"transitions": [{"id": "11", "name": "In Progress"}]}
    mock_get.return_value = mock_get_resp
    
    with pytest.raises(ValueError, match="Transition 'Done' not found"):
        configured_client.transition_issue(issue_key="QA-123", transition="Done")
