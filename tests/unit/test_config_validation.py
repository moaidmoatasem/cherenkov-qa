import pytest


def test_config_validate_passes_with_defaults():
    from cherenkov.core.settings import get_settings

    # Should not raise with valid defaults
    try:
        Config.validate()
    except ValueError as e:
        pytest.fail(f"Config.validate() raised with defaults: {e}")


def test_config_validate_rejects_bad_egress():
    from cherenkov.core.settings import get_settings

    original = getattr(Config, "EGRESS", "internal")
    get_settings().EGRESS = "invalid_value"
    try:
        with pytest.raises(ValueError, match="EGRESS"):
            Config.validate()
    finally:
        get_settings().EGRESS = original


def test_config_validate_rejects_bad_timeout():
    from cherenkov.core.settings import get_settings

    original = get_settings().OLLAMA_TIMEOUT
    get_settings().OLLAMA_TIMEOUT = 0  # below minimum of 1
    try:
        with pytest.raises(ValueError, match="OLLAMA_TIMEOUT"):
            Config.validate()
    finally:
        get_settings().OLLAMA_TIMEOUT = original


def test_config_validate_rejects_bad_port():
    from cherenkov.core.settings import get_settings

    original = get_settings().METRICS_PORT
    get_settings().METRICS_PORT = 99999  # above maximum of 65535
    try:
        with pytest.raises(ValueError, match="METRICS_PORT"):
            Config.validate()
    finally:
        get_settings().METRICS_PORT = original


def test_config_tiers_dict():
    from cherenkov.core.settings import get_settings

    assert "small" in get_settings().TIERS
    assert "deep" in get_settings().TIERS
    assert "provider" in get_settings().TIERS["small"]
    assert "model" in get_settings().TIERS["small"]
    assert "provider" in get_settings().TIERS["deep"]
    assert "model" in get_settings().TIERS["deep"]
