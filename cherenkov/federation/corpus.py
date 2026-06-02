import hashlib, json, os
from pathlib import Path
from datetime import datetime, timezone
from cherenkov.federation.protocol import DivergenceEnvelope

class CorpusOptInError(Exception):
    pass

class CorpusEntry:
    def __init__(self, id: str, timestamp: str, payload: dict):
        self.id = id
        self.timestamp = timestamp
        self.anonymized_payload = payload

class Corpus:
    def __init__(self, path: str = None):
        self.path = Path(path or os.path.expanduser("~/.cherenkov/corpus.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.opt_in = os.getenv("CHERENKOV_CORPUS_OPT_IN", "false").lower() == "true"
    
    def submit(self, envelope: DivergenceEnvelope) -> CorpusEntry:
        if not self.opt_in:
            raise CorpusOptInError("Opt-in disabled")
        anon = self._anon(envelope)
        entry = CorpusEntry(envelope.divergence.id, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), anon)
        with open(self.path, "a") as f:
            f.write(json.dumps({"id": entry.id, "timestamp": entry.timestamp, "payload": anon}) + "\n")
        return entry
    
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