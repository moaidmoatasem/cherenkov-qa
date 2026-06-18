import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

def test_skill_sync_import():
    try:
        import skill_sync
        assert True
    except ImportError:
        pytest.fail("Could not import skill_sync")
