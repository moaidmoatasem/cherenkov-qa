import json
import random


PROMPT_TEMPLATE = """### Spec:
{spec_slice}

### Test:
{test_code}

### Verdict:
{verdict}"""


class TrainingDataset:
    def __init__(self, records=None):
        self.records = records or []

    @classmethod
    def from_jsonl(cls, path):
        records = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return cls(records)

    @classmethod
    def from_collector(cls, collector, limit=1000):
        records = collector.query(limit=limit)
        return cls(records)

    def _format(self, record):
        return PROMPT_TEMPLATE.format(
            spec_slice=record["spec_slice"],
            test_code=record["test_code"],
            verdict=record["verdict"],
        )

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        record = self.records[idx]
        return self._format(record)

    def train_test_split(self, test_size=0.2, shuffle=True):
        indices = list(range(len(self.records)))
        if shuffle:
            random.shuffle(indices)
        split = int(len(indices) * (1 - test_size))
        train_indices = indices[:split]
        test_indices = indices[split:]
        train_records = [self.records[i] for i in train_indices]
        test_records = [self.records[i] for i in test_indices]
        return TrainingDataset(train_records), TrainingDataset(test_records)

    def save_jsonl(self, path):
        with open(path, "w", encoding="utf-8") as f:
            for record in self.records:
                f.write(json.dumps(record) + "\n")
