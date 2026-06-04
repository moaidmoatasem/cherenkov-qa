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

    def export_feedback(self, feedback_store: Any) -> list[dict[str, Any]]:
        policy = Config.EGRESS
        if policy == "none":
            raise PermissionError("Egress policy is 'none': federation export forbidden.")
        
        con = feedback_store._connect()
        rows = con.execute("SELECT item_id, endpoint, mutation_id, classification, actor, detail, timestamp FROM healing_feedback_log").fetchall()
        con.close()
        
        exported = []
        for r in rows:
            if policy == "internal":
                h = lambda v: hashlib.sha256(v.encode()).hexdigest()[:12] if v else ""
                exported.append({
                    "item_id": h(r["item_id"]),
                    "endpoint": h(r["endpoint"]),
                    "mutation_id": h(r["mutation_id"]),
                    "classification": r["classification"],
                    "actor": "anonymized",
                    "detail": "",
                    "timestamp": r["timestamp"]
                })
            else:
                exported.append({
                    "item_id": r["item_id"],
                    "endpoint": r["endpoint"],
                    "mutation_id": r["mutation_id"],
                    "classification": r["classification"],
                    "actor": r["actor"],
                    "detail": r["detail"],
                    "timestamp": r["timestamp"]
                })
        return exported

    def import_feedback(self, feedback_store: Any, data: list[dict[str, Any]]) -> None:
        policy = Config.EGRESS
        if policy == "none":
            raise PermissionError("Egress policy is 'none': federation import forbidden.")
            
        con = feedback_store._connect()
        for item in data:
            actor = "peer" if policy == "internal" else item.get("actor", "peer")
            con.execute(
                "INSERT INTO healing_feedback_log (item_id, endpoint, mutation_id, classification, actor, detail, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (item["item_id"], item["endpoint"], item["mutation_id"], item["classification"], actor, item.get("detail", ""), item["timestamp"])
            )
        con.commit()
        con.close()

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
