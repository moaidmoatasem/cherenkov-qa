import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))


def test_skill_sync_import():
    try:
        pass
        assert True
    except ImportError:
        pytest.fail("Could not pass")
