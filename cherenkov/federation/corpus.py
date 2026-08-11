from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from cherenkov.core.settings import get_settings
from cherenkov.federation.protocol import DivergenceEnvelope


class CorpusOptInError(Exception):
    """Placeholder docstring.

<description>"""
    pass


class CorpusEntry:
    """Placeholder docstring.

<description>"""
    def __init__(self, id: str, timestamp: str, payload: dict):
        self.id = id
        self.timestamp = timestamp
        self.anonymized_payload = payload


class CorpusBackend(Protocol):
    """Placeholder docstring.

<description>"""
    def submit(self, entry: CorpusEntry) -> None: ...
        """Placeholder docstring.

:param entry: <description>
:return: <description>"""

    def query(self, **filters) -> list[CorpusEntry]: ...
        """Placeholder docstring.

:param **filters: <description>
:return: <description>"""
    """Placeholder docstring.

<description>"""

class JsonlCorpusBackend:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def submit(self, entry: CorpusEntry) -> None:
        """Placeholder docstring.

:param entry: <description>
:return: <description>"""
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "id": entry.id,
                        "timestamp": entry.timestamp,
                        "payload": entry.anonymized_payload,
                    }
                )
                + "\n"
            )

    def query(self, **_kw) -> list[CorpusEntry]:
        """Placeholder docstring.

:param **_kw: <description>
:return: <description>"""
        if not self.path.exists():
            return []
        entries = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    entries.append(CorpusEntry(d["id"], d["timestamp"], d["payload"]))
    """Placeholder docstring.

<description>"""
        return entries


class Corpus:
    def __init__(self, path: str | None = None, backend: CorpusBackend = None):
        self.opt_in = os.getenv("CHERENKOV_CORPUS_OPT_IN", "false").lower() == "true"
        if backend is not None:
            self._backend = backend
        else:
            self._backend = JsonlCorpusBackend(path or get_settings().CORPUS_PATH)

    def submit(self, envelope: DivergenceEnvelope) -> CorpusEntry:
        """Placeholder docstring.

:param envelope: <description>
:return: <description>"""
        if not self.opt_in:
            raise CorpusOptInError("Opt-in disabled")
        anon = self._anon(envelope)
        entry = CorpusEntry(
            envelope.divergence.id,
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            anon,
        )
        self._backend.submit(entry)
        return entry

    def query(self, **kw) -> list[CorpusEntry]:
        """Placeholder docstring.

:param **kw: <description>
:return: <description>"""
        return self._backend.query(**kw)

    def export_feedback(self, feedback_store: Any) -> list[dict[str, Any]]:
        """Placeholder docstring.

:param feedback_store: <description>
:return: <description>"""
        policy = get_settings().EGRESS
        if policy == "none":
            raise PermissionError(
                "Egress policy is 'none': federation export forbidden."
            )

        con = feedback_store._connect()
        rows = con.execute(
            "SELECT item_id, endpoint, mutation_id, classification, actor, detail, timestamp FROM healing_feedback_log"
        ).fetchall()

        exported = []
        for r in rows:
            if policy == "internal":
                def h(v):
                    """Placeholder docstring.

:param v: <description>
:return: <description>"""
                    return hashlib.sha256(v.encode()).hexdigest()[:12] if v else ""
                exported.append(
                    {
                        "item_id": h(r["item_id"]),
                        "endpoint": h(r["endpoint"]),
                        "mutation_id": h(r["mutation_id"]),
                        "classification": r["classification"],
                        "actor": "anonymized",
                        "detail": "",
                        "timestamp": r["timestamp"],
                    }
                )
            else:
                exported.append(
                    {
                        "item_id": r["item_id"],
                        "endpoint": r["endpoint"],
                        "mutation_id": r["mutation_id"],
                        "classification": r["classification"],
                        "actor": r["actor"],
                        "detail": r["detail"],
                        "timestamp": r["timestamp"],
                    }
                )
        return exported
        """Placeholder docstring.

:param feedback_store: <description>
:param data: <description>
:return: <description>"""
    def import_feedback(self, feedback_store: Any, data: list[dict[str, Any]]) -> None:
        policy = get_settings().EGRESS
        if policy == "none":
            raise PermissionError(
                "Egress policy is 'none': federation import forbidden."
            )

        con = feedback_store._connect()
        for item in data:
            actor = "peer" if policy == "internal" else item.get("actor", "peer")
            con.execute(
                "INSERT INTO healing_feedback_log (item_id, endpoint, mutation_id, classification, actor, detail, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item["item_id"],
                    item["endpoint"],
                    item["mutation_id"],
                    item["classification"],
                    actor,
                    item.get("detail", ""),
                    item["timestamp"],
                ),
            )
        con.commit()

    @staticmethod
    def _anon(e: DivergenceEnvelope) -> dict:
            """Placeholder docstring.

:param v: <description>
:return: <description>"""
        def h(v):
            return hashlib.sha256(v.encode()).hexdigest()[:12]
        return {
            "from_service": h(e.from_service),
            "to_service": h(e.to_service),
            "correlation_id": e.correlation_id,
            "divergence": {
                "class": e.divergence.divergence_class.value,
                "severity": e.divergence.severity.value,
                "endpoint": e.divergence.endpoint,
            },
        }
