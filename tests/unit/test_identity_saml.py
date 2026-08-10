import pytest
from unittest.mock import patch, MagicMock
from cherenkov.adapters.identity.saml import SamlIdentityProvider

@pytest.fixture
def saml_config():
    return {
        "strict": True,
        "debug": True,
        "sp": {
            "entityId": "test-entity-id",
            "assertionConsumerService": {
                "url": "http://localhost/api/v1/auth/saml/callback",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
        },
        "idp": {
            "entityId": "http://idp.example.com/metadata",
            "singleSignOnService": {
                "url": "http://idp.example.com/sso",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            }
        }
    }

def test_saml_prepare_request(saml_config):
    provider = SamlIdentityProvider(saml_config)
    
    req_data = {
        'is_https': True,
        'host': 'example.com',
        'port': '443',
        'path': '/api/v1/auth/saml/callback',
        'query_params': {'RelayState': 'test'},
        'form_data': {'SAMLResponse': 'fake_response'}
    }
    
    prepared = provider._prepare_request(req_data)
    
    assert prepared['https'] == 'on'
    assert prepared['http_host'] == 'example.com'
    assert prepared['server_port'] == '443'
    assert prepared['script_name'] == '/api/v1/auth/saml/callback'
    assert prepared['get_data'] == {'RelayState': 'test'}
    assert prepared['post_data'] == {'SAMLResponse': 'fake_response'}

@patch('cherenkov.adapters.identity.saml.OneLogin_Saml2_Auth')
def test_saml_get_login_url(mock_auth_class, saml_config):
    mock_auth_instance = MagicMock()
    mock_auth_instance.login.return_value = "http://idp.example.com/sso?SAMLRequest=fake"
    mock_auth_class.return_value = mock_auth_instance
    
    provider = SamlIdentityProvider(saml_config)
    url = provider.get_login_url({})
    
    assert url == "http://idp.example.com/sso?SAMLRequest=fake"
    mock_auth_instance.login.assert_called_once()

@patch('cherenkov.adapters.identity.saml.OneLogin_Saml2_Auth')
def test_saml_authenticate_success(mock_auth_class, saml_config):
    mock_auth_instance = MagicMock()
    mock_auth_instance.get_errors.return_value = []
    mock_auth_instance.is_authenticated.return_value = True
    mock_auth_instance.get_nameid.return_value = "user123"
    mock_auth_instance.get_attributes.return_value = {
        "email": ["user@example.com"],
        "roles": ["admin"],
        "organization_id": ["org-1"]
    }
    mock_auth_instance.get_session_index.return_value = "session-1"
    
    mock_auth_class.return_value = mock_auth_instance
    
    provider = SamlIdentityProvider(saml_config)
    result = provider.authenticate({})
    
    assert result["id"] == "user123"
    assert result["email"] == "user@example.com"
    assert result["roles"] == ["admin"]
    assert result["session_index"] == "session-1"

@patch('cherenkov.adapters.identity.saml.OneLogin_Saml2_Auth')
def test_saml_authenticate_failure(mock_auth_class, saml_config):
    mock_auth_instance = MagicMock()
    mock_auth_instance.get_errors.return_value = ["Invalid signature"]
    mock_auth_class.return_value = mock_auth_instance
    
    provider = SamlIdentityProvider(saml_config)
    
    with pytest.raises(ValueError, match="SAML Authentication failed: Invalid signature"):
        provider.authenticate({})

@patch('cherenkov.adapters.identity.saml.OneLogin_Saml2_Auth')
def test_saml_build_metadata(mock_auth_class, saml_config):
    mock_auth_instance = MagicMock()
    mock_settings = MagicMock()
    mock_settings.get_sp_metadata.return_value = "<xml>SP Metadata</xml>"
    mock_settings.validate_metadata.return_value = []
    mock_auth_instance.get_settings.return_value = mock_settings
    
    mock_auth_class.return_value = mock_auth_instance
    
    provider = SamlIdentityProvider(saml_config)
    metadata = provider.build_metadata()
    
    assert metadata == "<xml>SP Metadata</xml>"
    mock_settings.get_sp_metadata.assert_called_once()
    mock_settings.validate_metadata.assert_called_once_with("<xml>SP Metadata</xml>")
