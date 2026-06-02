import os, tempfile, pytest
from cherenkov.core.contracts import DivergenceReport, DivergenceClass, Severity, DivergenceEvidence, StageMeta
from cherenkov.federation.protocol import DivergenceEnvelope
from cherenkov.federation.corpus import Corpus, CorpusOptInError

def make_divergence():
    return DivergenceReport(
        id="div-1",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="A",
        claim_b="B",
        evidence=DivergenceEvidence(
            request_summary="test",
            response_actual="actual",
            response_expected="expected",
            diff="diff",
        ),
        repro_steps=["step"],
        severity=Severity.HIGH,
        metadata=StageMeta(stage="test", schema_version=1),
    )

def test_opt_in_gate():
    os.environ.pop("CHERENKOV_CORPUS_OPT_IN", None)
    corpus = Corpus()
    envelope = DivergenceEnvelope(
        from_service="a",
        to_service="b",
        correlation_id="c1",
        divergence=make_divergence(),
    )
    with pytest.raises(CorpusOptInError):
        corpus.submit(envelope)

def test_opt_in_submit():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CHERENKOV_CORPUS_OPT_IN"] = "true"
        corpus = Corpus(path=f"{tmp}/corpus.jsonl")
        envelope = DivergenceEnvelope(
            from_service="prod-api",
            to_service="staging-api",
            correlation_id="trace-123",
            divergence=make_divergence(),
        )
        entry = corpus.submit(envelope)
        assert entry.id == "div-1"
        assert entry.timestamp
        os.environ.pop("CHERENKOV_CORPUS_OPT_IN")

def test_anonymization():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CHERENKOV_CORPUS_OPT_IN"] = "true"
        corpus = Corpus(path=f"{tmp}/corpus.jsonl")
        envelope = DivergenceEnvelope(
            from_service="acme-prod",
            to_service="acme-staging",
            correlation_id="trace-123",
            divergence=make_divergence(),
        )
        entry = corpus.submit(envelope)
        payload = entry.anonymized_payload
        assert "acme-prod" not in str(payload)
        assert "acme-staging" not in str(payload)
        assert payload["from_service"]
        assert payload["to_service"]
        os.environ.pop("CHERENKOV_CORPUS_OPT_IN")

def test_query_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CHERENKOV_CORPUS_OPT_IN"] = "true"
        corpus = Corpus(path=f"{tmp}/corpus.jsonl")
        envelope = DivergenceEnvelope(
            from_service="a",
            to_service="b",
            correlation_id="c1",
            divergence=make_divergence(),
        )
        corpus.submit(envelope)
        entries = corpus.query()
        assert len(entries) == 1
        assert entries[0].id == "div-1"
        os.environ.pop("CHERENKOV_CORPUS_OPT_IN")