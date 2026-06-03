import hashlib, json, os
from pathlib import Path
from typing import Protocol, Any
from datetime import datetime, timezone
from cherenkov.core.config import Config
from cherenkov.federation.protocol import DivergenceEnvelope

class CorpusOptInError(Exception):
    pass

class CorpusEntry:
    def __init__(self, id: str, timestamp: str, payload: dict):
        self.id = id
        self.timestamp = timestamp
        self.anonymized_payload = payload

class CorpusBackend(Protocol):
    def submit(self, entry: CorpusEntry) -> None:
        ...

    def query(self, **filters) -> list[CorpusEntry]:
        ...

class JsonlCorpusBackend:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def submit(self, entry: CorpusEntry) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps({"id": entry.id, "timestamp": entry.timestamp, "payload": entry.anonymized_payload}) + "\n")

    def query(self, **kw) -> list[CorpusEntry]:
        if not self.path.exists():
            return []
        entries = []
        with open(self.path) as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    entries.append(CorpusEntry(d["id"], d["timestamp"], d["payload"]))
        return entries

class Corpus:
    def __init__(self, path: str = None, backend: CorpusBackend = None):
        self.opt_in = os.getenv("CHERENKOV_CORPUS_OPT_IN", "false").lower() == "true"
        if backend is not None:
            self._backend = backend
        else:
            self._backend = JsonlCorpusBackend(path or Config.CORPUS_PATH)

    def submit(self, envelope: DivergenceEnvelope) -> CorpusEntry:
        if not self.opt_in:
            raise CorpusOptInError("Opt-in disabled")
        anon = self._anon(envelope)
        entry = CorpusEntry(envelope.divergence.id, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), anon)
        self._backend.submit(entry)
        return entry

    def query(self, **kw) -> list[CorpusEntry]:
        return self._backend.query(**kw)

    @staticmethod
    def _anon(e: DivergenceEnvelope) -> dict:
        h = lambda v: hashlib.sha256(v.encode()).hexdigest()[:12]
        return {
            "from_service": h(e.from_service),
            "to_service": h(e.to_service),
            "correlation_id": e.correlation_id,
            "divergence": {
                "class": e.divergence.divergence_class.value,
                "severity": e.divergence.severity.value,
                "endpoint": e.divergence.endpoint,
            }
        }
