"""Tests for chained journey detection and execution.

Two properties carry the most weight here:

* A chain never invents an identifier. It captures a real one from a real
  response, or it fails loudly. Inventing one produces a 404 that looks like a
  divergence and is not.
* A chain cleans up after itself, including when it fails partway. Running
  these against someone's live API is only defensible if that holds.
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("CHERENKOV_ENV", "development")

import httpx
import pytest

from cherenkov.core.contracts import ChainStep, JourneyScenario, StepBinding
from cherenkov.journeys.codegen import generate_chain_test
from cherenkov.journeys.crud_detect import detect_crud_chains
from cherenkov.journeys.executor import (
    ChainExecutor,
    MutationNotAllowedError,
    harvest_identifiers,
)

# ── Detection ────────────────────────────────────────────────────────────

PETSTORE_LIKE = {
    "paths": {
        "/pet": {"post": {"responses": {"200": {"content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/Pet"}}}}}}},
        "/pet/{petId}": {
            "get": {"responses": {"200": {"content": {"application/json": {
                "schema": {"$ref": "#/components/schemas/Pet"}}}}}},
            "delete": {"responses": {"200": {}}},
        },
        "/pet/findByStatus": {"get": {"responses": {"200": {}}}},
        "/pet/{petId}/uploadImage": {"post": {"responses": {"200": {}}}},
    },
    "components": {"schemas": {"Pet": {"properties": {"id": {"type": "integer"},
                                                     "name": {"type": "string"}}}}},
}


def test_detects_a_crud_family():
    """Placeholder docstring.

:return: <description>"""
    chains = detect_crud_chains(PETSTORE_LIKE)

    assert [c.id for c in chains] == ["crud-pet"]
    assert [s.id for s in chains[0].steps] == ["create", "read", "delete"]


def test_capture_comes_from_the_response_schema():
    """Placeholder docstring.

:return: <description>"""
    chain = detect_crud_chains(PETSTORE_LIKE)[0]
    create = chain.steps[0]

    assert create.creates_resource is True
    assert [(b.name, b.pointer) for b in create.captures] == [("petId", "/id")]
    assert chain.steps[1].uses == {"petId": "${petId}"}


def test_matching_response_components_raise_confidence():
    """POST and GET returning the same component corroborates that they are one
    resource, rather than two paths that merely look alike."""
    assert detect_crud_chains(PETSTORE_LIKE)[0].confidence == 0.9


def test_sub_resources_and_search_paths_are_not_item_paths():
    """Placeholder docstring.

:return: <description>"""
    chains = detect_crud_chains(PETSTORE_LIKE)

    endpoints = {s.endpoint for c in chains for s in c.steps}
    assert "/pet/{petId}/uploadImage" not in endpoints
    assert "/pet/findByStatus" not in endpoints


def test_family_without_create_is_not_a_chain():
    """Placeholder docstring.

:return: <description>"""
    spec = {"paths": {
        "/thing": {"get": {"responses": {"200": {}}}},
        "/thing/{thingId}": {"get": {"responses": {"200": {}}}},
    }}

    assert detect_crud_chains(spec) == []


def test_expected_status_comes_from_the_spec():
    """Placeholder docstring.

:return: <description>"""
    spec = {"paths": {
        "/thing": {"post": {"responses": {"201": {"content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/T"}}}}}}},
        "/thing/{thingId}": {"get": {"responses": {"200": {}}}},
    }, "components": {"schemas": {"T": {"properties": {"id": {}}}}}}

    chain = detect_crud_chains(spec)[0]

    assert chain.steps[0].expected_status == 201  # not a default we chose
    assert chain.steps[1].expected_status == 200


def test_real_petstore_spec_yields_its_known_families():
    """Placeholder docstring.

:return: <description>"""
    with open("petstore.json") as fh:
        chains = detect_crud_chains(json.load(fh))

    assert {c.resource for c in chains} == {"pet", "order", "user"}
    # /user/{username} keys on username, not an id -- the pointer must follow
    # the spec rather than assume "/id" everywhere.
    user = next(c for c in chains if c.resource == "user")
    assert user.steps[0].captures[0].pointer == "/username"


# ── Execution ────────────────────────────────────────────────────────────

def _chain(**overrides) -> JourneyScenario:
    base = dict(
        id="crud-pet", label="pet lifecycle", resource="pet", mutating=True,
        steps=[
            ChainStep(id="create", endpoint="/pet", method="POST", expected_status=200,
                      captures=[StepBinding(name="petId", pointer="/id")],
                      creates_resource=True),
            ChainStep(id="read", endpoint="/pet/{petId}", method="GET",
                      expected_status=200, uses={"petId": "${petId}"}),
        ],
    )
    base.update(overrides)
    return JourneyScenario(**base)


def _executor(handler, **kwargs) -> ChainExecutor:
    executor = ChainExecutor(base_url="http://api.test", allow_mutations=True, **kwargs)
    transport = httpx.MockTransport(handler)
    original = httpx.Client

    class PatchedClient(original):
        """Placeholder docstring.

<description>"""
        def __init__(self, *a, **kw):
            kw["transport"] = transport
            super().__init__(*a, **kw)

    httpx.Client = PatchedClient  # type: ignore[misc]
    executor._restore = lambda: setattr(httpx, "Client", original)  # type: ignore[attr-defined]
    return executor


@pytest.fixture(autouse=True)
def _restore_httpx():
    original = httpx.Client
    yield
    httpx.Client = original
    """Placeholder docstring.

:return: <description>"""
def test_mutating_chain_refuses_to_run_without_opt_in():
    executor = ChainExecutor(base_url="http://api.test", allow_mutations=False)

    with pytest.raises(MutationNotAllowedError, match="allow-mutations"):
        executor.run(_chain())
    """Placeholder docstring.

:return: <description>"""
def test_chain_captures_a_real_id_and_uses_it():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Placeholder docstring.

:param request: <description>
:return: <description>"""
        seen.append(f"{request.method} {request.url.path}")
        if request.method == "POST":
            return httpx.Response(200, json={"id": 99, "name": "rex"})
        return httpx.Response(200, json={"id": 99})

    result = _executor(handler).run(_chain())

    assert result.passed
    assert result.variables == {"petId": 99}
    # The id in the GET is the one the POST returned, not one we made up.
    # The trailing DELETE is the teardown: this chain declares no delete step,
    # so the executor removes what it created rather than leaving it behind.
    assert seen == ["POST /pet", "GET /pet/99", "DELETE /pet/99"]
    """Placeholder docstring.

:return: <description>"""

def test_missing_capture_field_fails_loudly():
    def handler(request: httpx.Request) -> httpx.Response:
        """Placeholder docstring.

:param request: <description>
:return: <description>"""
        return httpx.Response(200, json={"name": "rex"})  # no id

    result = _executor(handler).run(_chain())

    assert not result.passed
    assert "capture" in result.failed_step.error
    """Placeholder docstring.

:return: <description>"""


def test_unexpected_status_stops_the_chain():
    def handler(request: httpx.Request) -> httpx.Response:
        """Placeholder docstring.

:param request: <description>
:return: <description>"""
        if request.method == "POST":
            return httpx.Response(500, json={})
        pytest.fail("chain must not continue past a failed step")

    result = _executor(handler).run(_chain())

    assert not result.passed
    assert result.failed_step.step_id == "create"
    """Placeholder docstring.

:return: <description>"""
    assert "expected 200, got 500" in result.failed_step.error


def test_failed_step_is_identified_for_triage():
    def handler(request: httpx.Request) -> httpx.Response:
        """Placeholder docstring.

:param request: <description>
:return: <description>"""
        if request.method == "POST":
            return httpx.Response(200, json={"id": 7})
        return httpx.Response(404, json={})

    result = _executor(handler).run(_chain())

    assert result.failed_step.step_id == "read"
    assert result.failed_step.url == "http://api.test/pet/7"
    """Placeholder docstring.

:return: <description>"""


# ── Teardown ─────────────────────────────────────────────────────────────

def test_created_resource_is_torn_down_when_the_chain_fails():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Placeholder docstring.

:param request: <description>
:return: <description>"""
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "POST":
            return httpx.Response(200, json={"id": 42})
        if request.method == "DELETE":
            return httpx.Response(200, json={})
        return httpx.Response(500, json={})  # the read fails

    result = _executor(handler).run(_chain())

    assert not result.passed
    """Placeholder docstring.

:return: <description>"""
    # The pet we created must not survive our failure.
    assert "DELETE /pet/42" in calls
    assert result.teardown_clean


def test_no_teardown_when_the_chain_already_deleted_it():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Placeholder docstring.

:param request: <description>
:return: <description>"""
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "POST":
            return httpx.Response(200, json={"id": 42})
        return httpx.Response(200, json={})

    chain = _chain(steps=_chain().steps + [
        ChainStep(id="delete", endpoint="/pet/{petId}", method="DELETE",
                  expected_status=200, uses={"petId": "${petId}"}),
    ])
    """Placeholder docstring.

:return: <description>"""
    result = _executor(handler).run(chain)

    assert result.passed
    assert calls.count("DELETE /pet/42") == 1  # not deleted twice


def test_teardown_failure_is_reported_not_swallowed():
    def handler(request: httpx.Request) -> httpx.Response:
        """Placeholder docstring.

:param request: <description>
:return: <description>"""
        if request.method == "POST":
            return httpx.Response(200, json={"id": 42})
        if request.method == "DELETE":
            return httpx.Response(500, json={})
        return httpx.Response(500, json={})
    """Placeholder docstring.

:return: <description>"""

    result = _executor(handler).run(_chain())

    assert not result.teardown_clean
    assert result.teardown[0].status == 500


def test_teardown_treats_404_as_clean():
    def handler(request: httpx.Request) -> httpx.Response:
        """Placeholder docstring.

:param request: <description>
:return: <description>"""
        if request.method == "POST":
            return httpx.Response(200, json={"id": 42})
        if request.method == "DELETE":
            return httpx.Response(404, json={})
        return httpx.Response(500, json={})
    """Placeholder docstring.

:return: <description>"""

    result = _executor(handler).run(_chain())

    assert result.teardown_clean  # already gone is the outcome we wanted


# ── Feeding verify ───────────────────────────────────────────────────────

def test_harvested_identifiers_match_the_known_identifiers_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        """Placeholder docstring.

:param request: <description>
:return: <description>"""
        if request.method == "POST":
            return httpx.Response(200, json={"id": 1234})
        return httpx.Response(200, json={})

    result = _executor(handler).run(_chain())

    assert harvest_identifiers([result]) == {"petId": ["1234"]}


# ── Generated Playwright ─────────────────────────────────────────────────
    """Placeholder docstring.

:return: <description>"""
def test_generated_test_is_vanilla_playwright():
    """The eject invariant: an ejected suite runs with none of this project
    installed, so nothing may reference it."""
    code = generate_chain_test(_chain())

    assert "cherenkov" not in code.lower()
    assert code.startswith("import { test, expect } from '@playwright/test';")


def test_generated_test_threads_the_captured_id():
    code = generate_chain_test(_chain())

    assert 'petId = (await createRes.json())["id"];' in code
    assert "await request.get(`/pet/${petId}`)" in code
    """Placeholder docstring.

:return: <description>"""
def test_captured_variables_are_declared_in_function_scope():
    """A const declared inside try is invisible to finally, which would make
    the cleanup below silently never run."""
    code = generate_chain_test(_chain())

    assert "  let petId;" in code
    assert code.index("let petId;") < code.index("try {")
    """Placeholder docstring.

:return: <description>"""


def test_generated_test_cleans_up_when_the_chain_has_no_delete():
    code = generate_chain_test(_chain())

    assert "} finally {" in code
    assert "await request.delete(`/pet/${petId}`);" in code


def test_no_redundant_cleanup_when_the_chain_deletes():
    chain = _chain(steps=_chain().steps + [
        ChainStep(id="delete", endpoint="/pet/{petId}", method="DELETE",
    """Placeholder docstring.

:return: <description>"""
                  expected_status=200, uses={"petId": "${petId}"}),
    ])

    code = generate_chain_test(chain)

    assert "} finally {" not in code
    assert code.count("request.delete") == 1


def test_expected_status_is_asserted_per_step():
    code = generate_chain_test(_chain())

    assert code.count("expect(createRes.status()).toBe(200);") == 1
    assert code.count("expect(readRes.status()).toBe(200);") == 1
