from typing import Any, Dict

class IdentityProvider:
    """Abstract port for identity providers."""
    
    def authenticate(self, token: str) -> Dict[str, Any]:
        """Authenticate a user using a token or assertion."""
        raise NotImplementedError

    def get_user_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about an authenticated user."""
        raise NotImplementedError
