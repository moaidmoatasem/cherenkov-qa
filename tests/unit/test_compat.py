"""Unit tests for cherenkov/core/compat.py."""

from __future__ import annotations

import sys
from unittest.mock import patch


class TestNpx:
    def test_returns_string(self):
        from cherenkov.core.compat import npx
        result = npx()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_found_path_when_on_path(self):
        from cherenkov.core.compat import npx
        with patch("shutil.which", return_value="/usr/local/bin/npx"):
            result = npx()
        assert result == "/usr/local/bin/npx"

    def test_falls_back_to_npx_cmd_on_windows_when_not_found(self):
        with patch("shutil.which", return_value=None), \
             patch("sys.platform", "win32"):
            from importlib import reload
            import cherenkov.core.compat as compat
            result = compat.npx()
        assert result == "npx.cmd"

    def test_falls_back_to_npx_on_posix_when_not_found(self):
        with patch("shutil.which", return_value=None), \
             patch("sys.platform", "linux"):
            import cherenkov.core.compat as compat
            result = compat.npx()
        assert result == "npx"
