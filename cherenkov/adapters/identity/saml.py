import json
from typing import Any, Dict

from cherenkov.domain.ports.identity import IdentityProvider

try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    SAML_AVAILABLE = True
except ImportError:
    SAML_AVAILABLE = False


class SamlIdentityProvider(IdentityProvider):
    """SAML 2.0 Identity Provider using python3-saml."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with python3-saml configuration dictionary."""
        if not SAML_AVAILABLE:
            raise ImportError("python3-saml is required for SAML SSO support.")
        self.config = config

    def _prepare_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert an HTTP request object into the format expected by python3-saml."""
        return {
            'https': 'on' if request_data.get('is_https') else 'off',
            'http_host': request_data.get('host', ''),
            'server_port': request_data.get('port', ''),
            'script_name': request_data.get('path', ''),
            'get_data': request_data.get('query_params', {}),
            'post_data': request_data.get('form_data', {}),
            # 'lowercase_urlencoding': True,
        }

    def get_login_url(self, request_data: Dict[str, Any]) -> str:
        """Get the URL to redirect the user to for authentication."""
        req = self._prepare_request(request_data)
        auth = OneLogin_Saml2_Auth(req, custom_base_path=self.config)
        return auth.login()

    def authenticate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the SAML ACS response and authenticate the user."""
        req = self._prepare_request(request_data)
        auth = OneLogin_Saml2_Auth(req, custom_base_path=self.config)
        
        auth.process_response()
        
        errors = auth.get_errors()
        if errors:
            raise ValueError(f"SAML Authentication failed: {', '.join(errors)}")
            
        if not auth.is_authenticated():
            raise ValueError("SAML Authentication failed: Not authenticated")
            
        # Extract user information from SAML assertion
        user_id = auth.get_nameid()
        attributes = auth.get_attributes()
        
        return {
            "id": user_id,
            "roles": attributes.get("roles", []),
            "email": attributes.get("email", [user_id])[0],
            "session_index": auth.get_session_index()
        }

    def get_user_info(self, session_id: str) -> Dict[str, Any]:
        """Not typically implemented natively by SAML since it's token/assertion based. 
        Usually the ACS step establishes the local session."""
        raise NotImplementedError("SAML is push-based (assertions). Use authenticate() via ACS.")

    def build_metadata(self) -> str:
        """Generate SP metadata for the Identity Provider."""
        auth = OneLogin_Saml2_Auth(self._prepare_request({}), custom_base_path=self.config)
        settings = auth.get_settings()
        metadata = settings.get_sp_metadata()
        errors = settings.validate_metadata(metadata)
        if errors:
            raise ValueError(f"Invalid SP metadata: {', '.join(errors)}")
        return metadata
