"""Execute a chained journey against a live target.

Two things this module refuses to do, both deliberate:

* It will not run a mutating chain without explicit opt-in. Walking a CRUD
  lifecycle writes to somebody's API; that has to be asked for, not defaulted.
* It will not leave what it created behind. Every resource a chain creates is
  torn down in reverse order, including when the chain fails partway. A
  teardown that fails is reported, never swallowed -- a tool that silently
  litters a real service has broken trust even if its verdict was right.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from cherenkov.core.contracts import ChainStep, JourneyScenario

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"\$\{([^}]+)\}")


class MutationNotAllowedError(RuntimeError):
    """Raised when a mutating chain is run without explicit opt-in."""


@dataclass
class StepResult:
    step_id: str
    method: str
    url: str
    expected_status: int
    actual_status: int | None = None
    passed: bool = False
    captured: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: int = 0


@dataclass
class TeardownResult:
    step_id: str
    url: str
    status: int | None = None
    ok: bool = False
    error: str = ""


@dataclass
class ChainResult:
    journey_id: str
    resource: str
    passed: bool
    steps: list[StepResult] = field(default_factory=list)
    teardown: list[TeardownResult] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)

    @property
    def teardown_clean(self) -> bool:
        return all(t.ok for t in self.teardown)

    @property
    def failed_step(self) -> StepResult | None:
        """The step that broke, which is the thing a triager needs first."""
        return next((s for s in self.steps if not s.passed), None)


def _json_pointer(payload: Any, pointer: str) -> Any:
    """RFC 6901 lookup. Returns None when the pointer does not resolve."""
    if not pointer or pointer == "/":
        return payload
    node = payload
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            if token not in node:
                return None
            node = node[token]
        elif isinstance(node, list):
            try:
                node = node[int(token)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return node


def _substitute(template: str, variables: dict[str, Any]) -> str:
    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in variables:
            raise KeyError(name)
        return str(variables[name])
    return _PLACEHOLDER_RE.sub(replace, template)


def _resolve_path(step: ChainStep, variables: dict[str, Any]) -> str:
    """Fill the templated path from captured values only.

    A parameter with no captured value is an error, not an invitation to make
    one up -- an invented id yields a 404 that says nothing about conformance.
    """
    path = step.endpoint
    for param, reference in step.uses.items():
        value = _substitute(reference, variables)
        path = path.replace(f"{{{param}}}", value)
    if "{" in path:
        raise KeyError(f"unbound path parameter in {path!r}")
    return path


def _example_body(spec: dict, path: str, method: str) -> Any:
    """A request body taken from the spec, or None.

    Only the spec's own example is used. Synthesising a body from types would
    be inventing input, and a rejection of invented input is not a divergence.
    """
    operation = ((spec.get("paths") or {}).get(path) or {}).get(method.lower())
    if not isinstance(operation, dict):
        return None
    content = ((operation.get("requestBody") or {}).get("content")) or {}
    for media_type, media in content.items():
        if "json" not in media_type:
            continue
        if isinstance(media, dict):
            if "example" in media:
                return media["example"]
            schema = media.get("schema") or {}
            if "example" in schema:
                return schema["example"]
    return None


class ChainExecutor:
    def __init__(
        self,
        base_url: str,
        spec: dict | None = None,
        allow_mutations: bool = False,
        timeout: float = 15.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.spec = spec or {}
        self.allow_mutations = allow_mutations
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json", **(headers or {})}

    def run(self, chain: JourneyScenario) -> ChainResult:
        if chain.mutating and not self.allow_mutations:
            raise MutationNotAllowedError(
                f"Chain {chain.id!r} writes to {self.base_url}. "
                "Pass --allow-mutations to run it."
            )

        import httpx

        result = ChainResult(journey_id=chain.id, resource=chain.resource, passed=True)
        created: list[tuple[ChainStep, str]] = []

        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            try:
                for step in chain.steps:
                    step_result = self._run_step(client, step, result.variables)
                    result.steps.append(step_result)
                    if step.creates_resource and step_result.passed:
                        created.append((step, self._item_url(chain, result.variables)))
                    if not step_result.passed:
                        result.passed = False
                        break  # later steps depend on this one; do not pretend
            finally:
                # Runs on success, failure, and exception alike.
                result.teardown = self._teardown(client, chain, created, result)

        return result

    def _run_step(self, client, step: ChainStep, variables: dict[str, Any]) -> StepResult:
        started = time.monotonic()
        try:
            path = _resolve_path(step, variables)
        except KeyError as exc:
            return StepResult(
                step_id=step.id, method=step.method, url=step.endpoint,
                expected_status=step.expected_status,
                error=f"could not resolve {exc} from captured values",
            )

        url = f"{self.base_url}{path}"
        body = None
        if step.method.upper() in ("POST", "PUT", "PATCH"):
            body = _example_body(self.spec, step.endpoint, step.method)

        outcome = StepResult(
            step_id=step.id, method=step.method.upper(), url=url,
            expected_status=step.expected_status,
        )
        try:
            response = client.request(step.method.upper(), url, json=body)
        except Exception as exc:
            outcome.error = f"{type(exc).__name__}: {exc}"
            outcome.duration_ms = int((time.monotonic() - started) * 1000)
            return outcome

        outcome.actual_status = response.status_code
        outcome.passed = response.status_code == step.expected_status
        outcome.duration_ms = int((time.monotonic() - started) * 1000)
        if not outcome.passed:
            outcome.error = (
                f"expected {step.expected_status}, got {response.status_code}"
            )
            return outcome

        for binding in step.captures:
            value = self._capture(binding, response)
            if value is None:
                outcome.passed = False
                outcome.error = (
                    f"response did not contain {binding.pointer!r} "
                    f"to capture as {binding.name!r}"
                )
                return outcome
            variables[binding.name] = value
            outcome.captured[binding.name] = value

        return outcome

    @staticmethod
    def _capture(binding, response) -> Any:
        if binding.source == "status":
            return response.status_code
        if binding.source == "response_header":
            return response.headers.get(binding.pointer)
        try:
            return _json_pointer(response.json(), binding.pointer)
        except Exception:
            return None

    def _item_url(self, chain: JourneyScenario, variables: dict[str, Any]) -> str:
        """The URL that addresses the created resource, for teardown.

        A DELETE step gives it directly. When the chain has no DELETE -- a
        create+read chain, say -- any step that addresses the item by its
        captured id gives the same URL, and we issue the DELETE ourselves.
        Without this, a chain that creates a resource and never deletes one
        would leave it behind on every run.
        """
        candidates = sorted(
            (s for s in chain.steps if s.uses),
            key=lambda s: 0 if s.method.upper() == "DELETE" else 1,
        )
        for step in candidates:
            try:
                return f"{self.base_url}{_resolve_path(step, variables)}"
            except KeyError:
                continue
        return ""

    def _teardown(
        self, client, chain: JourneyScenario,
        created: list[tuple[ChainStep, str]], result: ChainResult,
    ) -> list[TeardownResult]:
        """Remove what we created, newest first."""
        # A DELETE the chain already performed successfully has done the job.
        already_deleted = any(
            s.step_id == "delete" and s.passed for s in result.steps
        )
        outcomes: list[TeardownResult] = []
        for step, url in reversed(created):
            if already_deleted:
                continue
            if not url:
                # We created something we cannot address. Say so -- silently
                # skipping would leave a resource behind and report success.
                outcomes.append(TeardownResult(
                    step_id=step.id, url="", ok=False,
                    error="could not derive an address for the created resource",
                ))
                logger.warning("no teardown address for %s created by %s",
                               chain.resource, step.id)
                continue
            try:
                response = client.request("DELETE", url)
                outcomes.append(TeardownResult(
                    step_id=step.id, url=url, status=response.status_code,
                    # 404 means it is gone, which is the goal.
                    ok=response.status_code < 400 or response.status_code == 404,
                ))
            except Exception as exc:
                outcomes.append(TeardownResult(
                    step_id=step.id, url=url, ok=False,
                    error=f"{type(exc).__name__}: {exc}",
                ))
                logger.warning("teardown failed for %s: %s", url, exc)
        return outcomes


def harvest_identifiers(results: list[ChainResult]) -> dict[str, list[str]]:
    """Turn captured values into the known_identifiers shape verify consumes.

    These are real ids the server itself returned, which is what makes them
    usable where an inferred value would not be.
    """
    harvested: dict[str, list[str]] = {}
    for result in results:
        for name, value in result.variables.items():
            if value is None:
                continue
            harvested.setdefault(name, [])
            if str(value) not in harvested[name]:
                harvested[name].append(str(value))
    return harvested
