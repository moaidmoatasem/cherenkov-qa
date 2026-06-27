"""Cross-platform compatibility helpers."""

from __future__ import annotations

import os
import glob as _glob
import shutil
import sys

# nvm-managed node/npx are not on the detached server PATH in WSL.
# These fallbacks mirror the same list used in doctor_cmd.py.
_NODE_FALLBACK_DIRS = [
    "/usr/local/bin",
    "/usr/bin",
    "/home/moaid/.local/bin",
    "/home/moaid/.nvm/versions/node/v22.23.0/bin",
]


def _find_posix_bin(name: str) -> str | None:
    """Find a POSIX binary, skipping Windows-side executables mounted via WSL."""
    found = shutil.which(name)
    # Reject Windows-side binaries (mounted under /mnt/) — they invoke cmd.exe
    # which cannot handle UNC paths (\\wsl.localhost\...).
    if found and not found.startswith("/mnt/"):
        return found
    # Probe known nvm/system locations
    for d in _NODE_FALLBACK_DIRS:
        candidate = os.path.join(d, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    # Last resort: glob nvm versions
    matches = _glob.glob(f"/home/*/.nvm/versions/node/*/bin/{name}")
    if matches:
        return sorted(matches)[-1]
    return None


def npx() -> str:
    """Return the npx executable suitable for subprocess on the current platform.

    On Windows, bare 'npx' is not found by subprocess because the real file is
    npx.cmd.  shutil.which resolves PATHEXT extensions on Windows so it returns
    the correct name; on POSIX it just returns 'npx' (or the absolute path if
    found on PATH).

    In WSL, the Windows-side npx (under /mnt/c/...) must be skipped — it
    invokes cmd.exe which cannot handle UNC paths.  We probe nvm fallback
    directories first.
    """
    if sys.platform == "win32":
        found = shutil.which("npx")
        return found if found else "npx.cmd"
    found = _find_posix_bin("npx")
    return found if found else "npx"


def node() -> str:
    """Return the node executable, with nvm fallback for detached WSL processes."""
    if sys.platform == "win32":
        found = shutil.which("node")
        return found if found else "node"
    found = _find_posix_bin("node")
    return found if found else "node"


def subprocess_env() -> dict:
    """Return an os.environ copy with the nvm node bin directory prepended to PATH.

    npx/tsc scripts use #!/usr/bin/env node — they fail if node isn't on PATH
    even when the script itself was found via _find_posix_bin().  This ensures
    the child process can resolve node.
    """
    env = os.environ.copy()
    node_bin = _find_posix_bin("node")
    if node_bin:
        node_dir = os.path.dirname(node_bin)
        existing = env.get("PATH", "")
        if node_dir not in existing.split(os.pathsep):
            env["PATH"] = node_dir + os.pathsep + existing
    return env
