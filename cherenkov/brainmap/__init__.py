"""CHERENKOV Brain Map — a reconciled, incrementally-synced map of a codebase.

The engine walks a project, extracts concepts and relationships from source,
docs, routes, commands and tests, reconciles the references between them, and
publishes the result three ways: an Obsidian vault you can open and browse, a
JSON graph the dashboard renders, and a SQLite store the API queries.

Typical use::

    from cherenkov.brainmap import build_engine

    engine = build_engine()          # profile discovered from the cwd
    report = engine.sync()           # incremental: only changed files parsed
    map_ = engine.graph()            # the reconciled graph

Nothing here is CHERENKOV-specific. Point ``build_engine(root=...)`` at any
repository and it maps that one instead — the profile in
:mod:`cherenkov.brainmap.config` is the only thing that knows about a project.
"""

from cherenkov.brainmap.config import BrainMapProfile, load_profile
from cherenkov.brainmap.domain.models import BrainMap, Edge, Finding, MapDelta, Node
from cherenkov.brainmap.reconcile import ReconcileOptions, Reconciler
from cherenkov.brainmap.use_cases.sync import BrainMapEngine, SyncReport, build_engine

__all__ = [
    "BrainMap",
    "BrainMapEngine",
    "BrainMapProfile",
    "Edge",
    "Finding",
    "MapDelta",
    "Node",
    "ReconcileOptions",
    "Reconciler",
    "SyncReport",
    "build_engine",
    "load_profile",
]
