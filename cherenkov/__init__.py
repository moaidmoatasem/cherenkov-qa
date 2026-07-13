# CHERENKOV package

from cherenkov.cli.core import main

try:
    from importlib.metadata import version as _version
    __version__ = _version("cherenkov")
except Exception:
    __version__ = "0.0.0"
