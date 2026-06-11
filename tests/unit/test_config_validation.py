import pytest


def test_config_validate_passes_with_defaults():
    from cherenkov.core.config import Config
    # Should not raise with valid defaults
    try:
        Config.validate()
    except ValueError as e:
        pytest.fail(f"Config.validate() raised with defaults: {e}")


def test_config_validate_rejects_bad_egress():
    from cherenkov.core.config import Config
    original = getattr(Config, 'EGRESS', 'internal')
    Config.EGRESS = 'invalid_value'
    try:
        with pytest.raises(ValueError, match="EGRESS"):
            Config.validate()
    finally:
        Config.EGRESS = original


def test_config_validate_rejects_bad_timeout():
    from cherenkov.core.config import Config
    original = Config.OLLAMA_TIMEOUT
    Config.OLLAMA_TIMEOUT = 0  # below minimum of 1
    try:
        with pytest.raises(ValueError, match="OLLAMA_TIMEOUT"):
            Config.validate()
    finally:
        Config.OLLAMA_TIMEOUT = original


def test_config_validate_rejects_bad_port():
    from cherenkov.core.config import Config
    original = Config.METRICS_PORT
    Config.METRICS_PORT = 99999  # above maximum of 65535
    try:
        with pytest.raises(ValueError, match="METRICS_PORT"):
            Config.validate()
    finally:
        Config.METRICS_PORT = original


def test_config_tiers_dict():
    from cherenkov.core.config import Config
    assert "small" in Config.TIERS
    assert "deep" in Config.TIERS
    assert "provider" in Config.TIERS["small"]
    assert "model" in Config.TIERS["small"]
    assert "provider" in Config.TIERS["deep"]
    assert "model" in Config.TIERS["deep"]
