"""Cross-platform compatibility helpers."""
from __future__ import annotations

import shutil
import sys


def npx() -> str:
    """Return the npx executable suitable for subprocess on the current platform.

    On Windows, bare 'npx' is not found by subprocess because the real file is
    npx.cmd.  shutil.which resolves PATHEXT extensions on Windows so it returns
    the correct name; on POSIX it just returns 'npx' (or the absolute path if
    found on PATH).
    """
    found = shutil.which("npx")
    if found:
        return found
    return "npx.cmd" if sys.platform == "win32" else "npx"
