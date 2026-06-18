import json
import os
import tempfile
import unittest

from cherenkov.training import DataCollector, TrainingDataset, Trainer, TrainerConfig


class TestTrainingPipeline(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_telemetry.db")
        self.collector = DataCollector(db_path=self.db_path)

    def tearDown(self):
        self.collector.close()

    # ---- DataCollector tests ----

    def test_collector_init_creates_db(self):
        self.assertTrue(os.path.isfile(self.db_path))

    def test_collector_record_and_count(self):
        self.collector.record("spec1", "test1", "pass", "/api/v1", 1.5)
        self.collector.record("spec2", "test2", "fail", "/api/v2", 2.3)
        self.assertEqual(self.collector.count(), 2)

    def test_collector_query(self):
        self.collector.record("spec_q", "test_q", "pass", "/query", 0.5)
        results = self.collector.query(limit=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["spec_slice"], "spec_q")
        self.assertEqual(results[0]["verdict"], "pass")

    def test_collector_export_jsonl(self):
        self.collector.record("spec_e", "test_e", "fail", "/export", 3.0)
        export_path = os.path.join(self.tmpdir, "export.jsonl")
        self.collector.export_json(export_path)
        with open(export_path) as f:
            lines = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["spec_slice"], "spec_e")
        self.assertEqual(lines[0]["verdict"], "fail")

    def test_collector_clear(self):
        self.collector.record("spec_c", "test_c", "pass")
        self.assertEqual(self.collector.count(), 1)
        self.collector.clear()
        self.assertEqual(self.collector.count(), 0)

    # ---- TrainingDataset tests ----

    def test_dataset_from_jsonl(self):
        path = os.path.join(self.tmpdir, "data.jsonl")
        with open(path, "w") as f:
            f.write(
                json.dumps(
                    {
                        "spec_slice": "s1",
                        "test_code": "t1",
                        "verdict": "pass",
                        "endpoint": "/a",
                        "duration_ms": 1.0,
                        "created_at": "now",
                    }
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "spec_slice": "s2",
                        "test_code": "t2",
                        "verdict": "fail",
                        "endpoint": "/b",
                        "duration_ms": 2.0,
                        "created_at": "now",
                    }
                )
                + "\n"
            )
        ds = TrainingDataset.from_jsonl(path)
        self.assertEqual(len(ds), 2)

    def test_dataset_from_collector(self):
        self.collector.record("sc1", "tc1", "pass")
        self.collector.record("sc2", "tc2", "fail")
        ds = TrainingDataset.from_collector(self.collector, limit=10)
        self.assertEqual(len(ds), 2)

    def test_dataset_len_and_getitem(self):
        self.collector.record("s_gi", "t_gi", "pass")
        ds = TrainingDataset.from_collector(self.collector)
        self.assertEqual(len(ds), 1)
        prompt = ds[0]
        self.assertIn("### Spec:", prompt)
        self.assertIn("s_gi", prompt)
        self.assertIn("### Test:", prompt)
        self.assertIn("t_gi", prompt)
        self.assertIn("### Verdict:", prompt)
        self.assertIn("pass", prompt)

    def test_dataset_train_test_split(self):
        for i in range(10):
            self.collector.record(
                f"spec_{i}", f"test_{i}", "pass" if i % 2 == 0 else "fail"
            )
        ds = TrainingDataset.from_collector(self.collector)
        train, test = ds.train_test_split(test_size=0.2, shuffle=False)
        self.assertEqual(len(train), 8)
        self.assertEqual(len(test), 2)

    def test_dataset_save_jsonl(self):
        self.collector.record("sj1", "tj1", "pass")
        ds = TrainingDataset.from_collector(self.collector)
        save_path = os.path.join(self.tmpdir, "saved.jsonl")
        ds.save_jsonl(save_path)
        loaded = TrainingDataset.from_jsonl(save_path)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded.records[0]["spec_slice"], "sj1")

    # ---- Trainer tests ----

    def test_trainer_prepare(self):
        self.collector.record("spec_tr", "test_tr", "pass")
        ds = TrainingDataset.from_collector(self.collector)
        config = TrainerConfig()
        trainer = Trainer(config, ds)
        msgs = trainer.prepare()
        self.assertTrue(any("Pipeline ready" in m for m in msgs))

    def test_trainer_evaluate(self):
        records = [
            {
                "spec_slice": f"s{i}",
                "test_code": f"t{i}",
                "verdict": "pass",
                "endpoint": "",
                "duration_ms": 0.0,
                "created_at": "now",
            }
            for i in range(10)
        ]
        test_ds = TrainingDataset(records)
        config = TrainerConfig()
        trainer = Trainer(config, TrainingDataset(records[:5]))
        metrics = trainer.evaluate(test_ds)
        self.assertIn("accuracy", metrics)
        self.assertIn("loss", metrics)
        self.assertIn("total_examples", metrics)
        self.assertEqual(metrics["total_examples"], 10)


if __name__ == "__main__":
    unittest.main()
