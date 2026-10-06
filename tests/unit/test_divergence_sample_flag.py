"""#1041: the demo corpus must be labelled as sample data, real findings must not be."""
from __future__ import annotations

from cherenkov.web import divergences as div_mod


def test_empty_store_serves_corpus_flagged_as_sample(monkeypatch):
    monkeypatch.setattr(div_mod, "_stored_divergences", lambda: [])
    items = div_mod.list_divergences()
    assert items and all(i.get("sample") is True for i in items)


def test_stored_findings_are_never_flagged_as_sample(monkeypatch):
    real = [{"id": "D-real", "endpoint": "/x", "severity": "high", "status": "open"}]
    monkeypatch.setattr(div_mod, "_stored_divergences", lambda: real)
    items = div_mod.list_divergences()
    assert items == real and not any(i.get("sample") for i in items)
