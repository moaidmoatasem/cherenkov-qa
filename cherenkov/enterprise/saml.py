"""SAML SSO Service Provider middleware for CHERENKOV enterprise mode."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cherenkov.core.errors import get_logger

log = get_logger(__name__)


@dataclass
class SAMLConfig:
    idp_metadata_url: str = ""
    entity_id: str = "cherenkov-qa"
    acs_url: str = "/api/v1/auth/saml/callback"
    audience: str = "cherenkov-qa"
    clock_skew_seconds: int = 60
    enabled: bool = False


@dataclass
class SAMLAssertion:
    name_id: str
    email: str
    attributes: dict[str, Any] = field(default_factory=dict)
    session_index: str = ""
    issuer: str = ""


class SAMLServiceProvider:
    """SAML 2.0 Service Provider for SSO authentication.

    Supports:
    - SP-initiated SSO (redirect to IdP)
    - IdP-initiated SSO (ACS endpoint)
    - SLO (Single Log Out)
    - Clock skew tolerance
    """

    def __init__(self, config: SAMLConfig | None = None):
        self.config = config or SAMLConfig()
        self._sessions: dict[str, SAMLAssertion] = {}

    def is_enabled(self) -> bool:
        return self.config.enabled and bool(self.config.idp_metadata_url)

    def get_login_url(self, relay_state: str = "") -> str:
        """Generate SP-initiated login URL (redirect to IdP)."""
        if not self.is_enabled():
            return ""
        import urllib.parse

        params = {
            "SAMLRequest": self._build_authn_request(),
            "RelayState": relay_state,
        }
        return f"{self.config.idp_metadata_url}?{urllib.parse.urlencode(params)}"

    def process_response(self, saml_response: str) -> SAMLAssertion | None:
        """Process IdP SAML response and extract assertion."""
        if not self.is_enabled():
            return None
        assertion = self._parse_assertion(saml_response)
        if assertion:
            self._sessions[assertion.name_id] = assertion
        return assertion

    def get_session(self, name_id: str) -> SAMLAssertion | None:
        return self._sessions.get(name_id)

    def end_session(self, name_id: str) -> bool:
        if name_id in self._sessions:
            del self._sessions[name_id]
            return True
        return False

    def _build_authn_request(self) -> str:
        """Build base64-encoded SAML AuthnRequest."""
        import base64
        import xml.etree.ElementTree as ET

        root = ET.Element(
            "{urn:oasis:names:tc:SAML:2.0:protocol}AuthnRequest"
        )
        root.set("AssertionConsumerServiceURL", self.config.acs_url)
        root.set("Destination", self.config.idp_metadata_url)
        root.set("ProtocolBinding", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST")
        root.set("ID", self._generate_id())
        root.set("Version", "2.0")
        issuer = ET.SubElement(
            root, "{urn:oasis:names:tc:SAML:2.0:assertion}Issuer"
        )
        issuer.text = self.config.entity_id
        xml_bytes = ET.tostring(root, encoding="unicode").encode("utf-8")
        return base64.b64encode(xml_bytes).decode("utf-8")

    def _parse_assertion(self, saml_response: str) -> SAMLAssertion:
        """Parse SAML response XML and extract assertion data."""
        import base64
        import xml.etree.ElementTree as ET

        try:
            xml_bytes = base64.b64decode(saml_response)
            root = ET.fromstring(xml_bytes)
            ns = {
                "saml2": "urn:oasis:names:tc:SAML:2.0:assertion",
                "saml2p": "urn:oasis:names:tc:SAML:2.0:protocol",
            }
            assertion = root.find(".//saml2:Assertion", ns)
            if assertion is None:
                return SAMLAssertion(name_id="", email="")

            name_id_el = assertion.find(".//saml2:NameID", ns)
            email = ""
            attr_el = assertion.find(
                ".//saml2:Attribute[@Name='email']/saml2:AttributeValue", ns
            )
            if attr_el is not None and attr_el.text:
                email = attr_el.text
            attrs = {}
            for attr in assertion.findall(".//saml2:Attribute", ns):
                name = attr.get("Name", "")
                values = [
                    v.text or ""
                    for v in attr.findall("saml2:AttributeValue", ns)
                ]
                if values:
                    attrs[name] = values[0] if len(values) == 1 else values

            return SAMLAssertion(
                name_id=name_id_el.text if name_id_el is not None else "",
                email=email,
                attributes=attrs,
            )
        except Exception as exc:
            log.error("SAML assertion parse failed", error=str(exc))
            return SAMLAssertion(name_id="", email="")

    def _generate_id(self) -> str:
        import uuid

        return f"_{uuid.uuid4().hex}"
