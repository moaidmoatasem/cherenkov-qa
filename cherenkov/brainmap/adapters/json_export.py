"""JSON exporters — the map as data, for the UI and for other tools.

Two shapes are produced. ``JsonExporter`` writes the full map for archival or
for a downstream consumer. ``graph_payload`` builds the trimmed, ranked view
the dashboard renders: a browser cannot lay out fifty thousand nodes, so the
server decides which slice matters and says how much it left out — silently
truncating a graph is how a visualisation starts lying.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cherenkov.brainmap.domain.models import BrainMap


class JsonExporter:
    """Writes a whole map to a single JSON document."""

    name = "json"

    def export(self, map_: BrainMap, target: Path) -> dict[str, Any]:
        """Write ``map_`` to ``target``.

        Args:
            map_ (BrainMap): A reconciled map.
            target (Path): Output file, or a directory to write
                ``brainmap.json`` into.

        Returns:
            dict[str, Any]: Where it went and how large it is.
        """
        target = Path(target)
        if target.is_dir() or not target.suffix:
            target.mkdir(parents=True, exist_ok=True)
            target = target / "brainmap.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(map_.to_dict(), indent=2, sort_keys=False)
        target.write_text(payload, encoding="utf-8")
        return {"path": str(target), "bytes": len(payload), "nodes": len(map_.nodes)}


def graph_payload(
    map_: BrainMap,
    limit: int = 600,
    kinds: list[str] | None = None,
    layers: list[str] | None = None,
    query: str = "",
) -> dict[str, Any]:
    """Build a render-ready, size-bounded view of a map.

    Filters apply first, then ranking by connectivity, then the limit. Ranking
    before truncating means the slice you get is the map's backbone rather
    than whichever nodes happened to sort first.

    Args:
        map_ (BrainMap): The map to render.
        limit (int): Maximum nodes to return, clamped to 1–5000.
        kinds (list[str] | None): Keep only these node kinds.
        layers (list[str] | None): Keep only these layers.
        query (str): Case-insensitive substring match on title or summary.

    Returns:
        dict[str, Any]: ``nodes``, ``edges``, ``stats`` and a ``truncated``
        block naming how many nodes and edges were dropped.
    """
    limit = max(1, min(int(limit), 5000))
    kind_set = set(kinds or [])
    layer_set = set(layers or [])
    needle = query.strip().lower()

    selected = [
        node
        for node in map_.nodes.values()
        if (not kind_set or node.kind in kind_set)
        and (not layer_set or node.layer in layer_set)
        and (not needle or needle in node.title.lower() or needle in node.summary.lower())
    ]
    degree = map_.degree()
    selected.sort(key=lambda n: (-degree.get(n.id, 0), -n.weight, n.id))
    kept = selected[:limit]
    kept_ids = {node.id for node in kept}

    edges = [e for e in map_.edges if e.src in kept_ids and e.dst in kept_ids]
    return {
        "project": map_.project,
        "built_at": map_.built_at,
        "nodes": [
            {
                "id": n.id,
                "kind": n.kind,
                "title": n.title,
                "summary": n.summary,
                "layer": n.layer,
                "origin": n.origin,
                "tags": n.tags,
                "degree": degree.get(n.id, 0),
                "weight": n.weight,
            }
            for n in kept
        ],
        "edges": [{"src": e.src, "dst": e.dst, "kind": e.kind, "weight": e.weight} for e in edges],
        "stats": map_.stats(),
        "truncated": {
            "nodes_hidden": max(0, len(selected) - len(kept)),
            "edges_hidden": max(0, len(map_.edges) - len(edges)),
            "matched": len(selected),
            "limit": limit,
        },
    }
