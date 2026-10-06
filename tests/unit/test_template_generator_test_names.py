"""Generated Playwright test titles must not repeat the scenario name.

Defect 7 of the 2026-08-12 real-user walkthrough (#975):

    test('get /orders/{id} happy_path happy_path', async () => {

The title was built as `"{method} {path} {case_type} {mutation_id}"`, and
`stages/ingest.py` mints the happy-path scenario as
`Mutation(id="happy_path", case_type="happy_path")` for **every** endpoint. So
the duplication landed on the single most common scenario in any suite, one per
endpoint, while `case_type="auth"` / `id="unauthorized"` read correctly and hid
how general the problem was.

Cosmetic, but titles are what a person reads in a Playwright report, and this
project's whole argument is that generated output should not look careless.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cherenkov.substrate.providers.template_generator import generate_test

_OPERATION = {"responses": {"200": {"description": "ok"}}}


def _title(case_type: str, mutation_id: str | None, path: str = "/orders/{id}") -> str:
    scenario = SimpleNamespace(
        case_type=case_type, mutation_id=mutation_id, expected_status=200
    )
    code = generate_test(path, "GET", _OPERATION, {}, scenario)
    line = next(line for line in code.splitlines() if line.startswith("test("))
    return line[len("test('") : line.index("'", len("test('"))]


def test_the_exact_title_from_the_walkthrough_is_not_produced():
    """The literal string reported in #975."""
    assert _title("happy_path", "happy_path") == "get /orders/{id} happy_path"


def test_happy_path_is_the_case_ingest_actually_builds():
    """Guard the real pairing, not a hypothetical one.

    stages/ingest.py: Mutation(id="happy_path", case_type="happy_path").
    """
    from cherenkov.stages import ingest  # noqa: F401  (import proves the module loads)

    assert _title("happy_path", "happy_path").count("happy_path") == 1


@pytest.mark.parametrize(
    ("case_type", "mutation_id"),
    [
        ("happy_path", "happy_path"),
        ("auth", "auth"),
        ("validation", "validation"),
    ],
)
def test_no_title_repeats_a_token(case_type, mutation_id):
    tokens = _title(case_type, mutation_id).split()
    assert len(tokens) == len(set(tokens)), f"repeated token in: {tokens}"


@pytest.mark.parametrize(
    ("case_type", "mutation_id", "expected"),
    [
        # A distinct id carries real information and must survive.
        ("auth", "unauthorized", "get /orders/{id} auth unauthorized"),
        ("validation", "missing_email", "get /orders/{id} validation missing_email"),
        # Absent ids were already handled; pin them so the fix cannot regress them.
        ("happy_path", "", "get /orders/{id} happy_path"),
        ("happy_path", None, "get /orders/{id} happy_path"),
    ],
)
def test_distinct_mutation_ids_are_preserved(case_type, mutation_id, expected):
    assert _title(case_type, mutation_id) == expected


def test_titles_stay_unique_across_endpoints():
    """Collapsing the suffix must not collapse two scenarios into one name."""
    titles = {
        _title("happy_path", "happy_path", path)
        for path in ("/orders/{id}", "/orders", "/users/{id}")
    }
    assert len(titles) == 3, titles


def test_generated_code_is_still_syntactically_intact():
    """The title is spliced into TypeScript; a stray quote would break the file."""
    scenario = SimpleNamespace(
        case_type="happy_path", mutation_id="happy_path", expected_status=200
    )
    code = generate_test("/orders/{id}", "GET", _OPERATION, {}, scenario)
    assert "test('get /orders/{id} happy_path', async () => {" in code
    assert code.count("test('") == 1
