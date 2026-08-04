from __future__ import annotations

from cherenkov.execution.failure_classifier import FailureCategory, classify_failure

_CORPUS = [
    {
        "id": "D-01",
        "endpoint": "GET /pet/findByStatus",
        "claimA": "schema: enum [available, pending, sold]",
        "claimB": "accepts arbitrary status strings",
        "reproSteps": 'curl "https://example.test/pet/findByStatus?status=bogus"',
        "confidence": 0.95,
    },
    {
        "id": "D-02",
        "endpoint": "POST /pet",
        "claimA": "required: [name, photoUrls]",
        "claimB": "accepts missing photoUrls",
        "reproSteps": 'curl -X POST "https://example.test/pet"',
        "confidence": 0.99,
    },
]


def test_matching_endpoint_classifies_as_product_bug():
    result = classify_failure("/pet/findByStatus", "GET", divergences=_CORPUS)
    assert result.category == FailureCategory.PRODUCT_BUG
    assert result.divergence_id == "D-01"
    assert result.confidence == 0.95
    assert result.expected == "schema: enum [available, pending, sold]"
    assert result.actual == "accepts arbitrary status strings"
    assert result.repro is not None and "curl" in result.repro


def test_method_matching_is_case_insensitive_and_normalizes():
    result = classify_failure("/pet", "post", divergences=_CORPUS)
    assert result.category == FailureCategory.PRODUCT_BUG
    assert result.divergence_id == "D-02"
    assert result.method == "POST"


def test_no_correlating_divergence_is_unknown_not_guessed():
    result = classify_failure("/store/order", "DELETE", divergences=_CORPUS)
    assert result.category == FailureCategory.UNKNOWN
    assert result.divergence_id is None
    assert result.confidence is None
    assert "not built yet" in result.reason


def test_wrong_method_on_known_endpoint_does_not_match():
    result = classify_failure("/pet", "DELETE", divergences=_CORPUS)
    assert result.category == FailureCategory.UNKNOWN


def test_defaults_to_live_divergence_corpus_when_none_passed():
    result = classify_failure("/pet/findByStatus", "GET")
    assert result.category == FailureCategory.PRODUCT_BUG
    assert result.divergence_id == "D-01"
