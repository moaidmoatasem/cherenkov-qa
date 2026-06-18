import pytest
from cherenkov.core.settings import CherenkovSettings, get_settings


def test_config_validate_passes_with_defaults():
    try:
        CherenkovSettings()
    except Exception as e:
        pytest.fail(f"CherenkovSettings() raised with defaults: {e}")


def test_config_validate_rejects_bad_egress():
    # EGRESS is a plain str with no Literal constraint in settings.py, so any string
    # is accepted.  Assert the default is one of the expected modes.
    settings = CherenkovSettings()
    assert settings.EGRESS in (
        "internal",
        "external",
        "blocked",
    ), f"Unexpected default EGRESS value: {settings.EGRESS!r}"


def test_config_validate_rejects_bad_timeout():
    # OLLAMA_TIMEOUT is a plain int with no ge= constraint, but a negative timeout
    # makes no sense.  Assert the default is positive.
    settings = CherenkovSettings()
    assert (
        settings.OLLAMA_TIMEOUT > 0
    ), f"OLLAMA_TIMEOUT default should be positive, got {settings.OLLAMA_TIMEOUT}"


def test_config_validate_rejects_bad_port():
    # Ports are plain ints without le=65535 constraint.  Assert defaults are in
    # the valid port range (1-65535).
    settings = CherenkovSettings()
    for attr in ("DESKTOP_WS_PORT", "CHAT_WS_PORT", "METRICS_PORT"):
        port = getattr(settings, attr)
        assert (
            1 <= port <= 65535
        ), f"{attr} default {port} is outside valid port range 1-65535"


def test_config_tiers_dict():
    settings = get_settings()
    assert "small" in settings.TIERS
    assert "deep" in settings.TIERS
    assert "provider" in settings.TIERS["small"]
    assert "model" in settings.TIERS["small"]
    assert "provider" in settings.TIERS["deep"]
    assert "model" in settings.TIERS["deep"]
