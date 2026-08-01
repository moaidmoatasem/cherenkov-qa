# Spec-Shape Conformance Corpus (E0.5d)

This directory contains `evaluate_corpus.py`, a script used to measure how CHERENKOV's probe planner behaves against 10 real-world OpenAPI specifications (Stripe, GitHub, Kubernetes, etc.).

## Usage

```bash
python evaluate_corpus.py
```

This will download the specs, run the probe planner, and generate `corpus_report.md` detailing the reasons endpoints were dropped (e.g., non-GET, unfillable templated paths).

This report directly informs the prioritization for task **E0.5i (Raise real coverage)** by showing which obstacles actually block the most endpoints in practice.
