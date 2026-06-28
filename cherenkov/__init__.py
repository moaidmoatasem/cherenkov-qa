# CHERENKOV package

from cherenkov.cli.core import main  # noqa: F401 — entry-point for pyproject.toml [project.scripts]

try:
    from importlib.metadata import version as _version
    __version__ = _version("cherenkov")
except Exception:
    __version__ = "0.0.0"
