"""
CHERENKOV divergence/proof_run.py — E3-5 Proof Run Orchestrator.

Points CHERENKOV at a target service (spec + live base URL) and runs the full
Skeptic → Witness loop, collecting confirmed DivergenceReport instances.

Default target: Swagger Petstore v3 (https://petstore3.swagger.io)
  Spec:     https://petstore3.swagger.io/api/v3/openapi.json
  Base URL: https://petstore3.swagger.io/api/v3

Usage:
    python -m cherenkov.divergence.proof_run
    python -m cherenkov.divergence.proof_run --base-url http://localhost:8080 --spec ./openapi.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

from cherenkov.core.contracts import (
    DivergenceHypothesis,
    DivergenceReport,
    ReproductionResult,
    StageMeta,
    Status,
)
from cherenkov.divergence.skeptic import SkepticAgent
from cherenkov.divergence.witness import WitnessAgent
from cherenkov.reflector.reflector import Reflector
from cherenkov.reflector.store import VerdictStore

# ── default target ────────────────────────────────────────────────────────

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"
PETSTORE_SPEC_URL = "https://petstore3.swagger.io/api/v3/openapi.json"

# Bundled fallback spec for offline use: a minimal Petstore subset covering
# the five endpoints we probe in the proof run.
PETSTORE_SPEC_SUBSET: dict = {
    "openapi": "3.0.3",
    "info": {"title": "Swagger Petstore", "version": "1.0.17"},
    "paths": {
        "/pet/findByStatus": {
            "get": {
                "summary": "Finds Pets by status",
                "operationId": "findPetsByStatus",
                "parameters": [
                    {
                        "name": "status",
                        "in": "query",
                        "description": "Status values to filter by",
                        "required": False,
                        "schema": {
                            "type": "string",
                            "default": "available",
                            "enum": ["available", "pending", "sold"],
                        },
                    }
                ],
                "responses": {
                    "200": {
                        "description": "successful operation",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Pet"},
                                }
                            }
                        },
                    },
                    "400": {"description": "Invalid status value"},
                },
            }
        },
        "/pet/{petId}": {
            "get": {
                "summary": "Find pet by ID",
                "operationId": "getPetById",
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "description": "ID of pet to return",
                        "required": True,
                        "schema": {"type": "integer", "format": "int64"},
                    }
                ],
                "responses": {
                    "200": {"description": "successful operation"},
                    "400": {"description": "Invalid ID supplied"},
                    "404": {"description": "Pet not found"},
                },
            },
            "delete": {
                "summary": "Deletes a pet",
                "operationId": "deletePet",
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer", "format": "int64"},
                    }
                ],
                "responses": {
                    "200": {"description": "Pet deleted"},
                    "400": {"description": "Invalid pet value"},
                },
            },
        },
        "/pet": {
            "post": {
                "summary": "Add a new pet to the store",
                "operationId": "addPet",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Pet"}
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Successful operation"},
                    "405": {"description": "Invalid input"},
                },
            }
        },
        "/store/inventory": {
            "get": {
                "summary": "Returns pet inventories by status",
                "operationId": "getInventory",
                "responses": {
                    "200": {
                        "description": "successful operation",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": {
                                        "type": "integer",
                                        "format": "int32",
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        "/user/login": {
            "get": {
                "summary": "Logs user into the system",
                "operationId": "loginUser",
                "parameters": [
                    {
                        "name": "username",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "password",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "successful operation",
                        "headers": {
                            "X-Rate-Limit": {
                                "description": "calls per hour allowed by the user",
                                "schema": {"type": "integer", "format": "int32"},
                            },
                            "X-Expires-After": {
                                "description": "date in UTC when token expires",
                                "schema": {"type": "string", "format": "date-time"},
                            },
                        },
                    },
                    "400": {"description": "Invalid username/password supplied"},
                },
            }
        },
    },
    "components": {
        "schemas": {
            "Pet": {
                "required": ["name", "photoUrls"],
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string", "example": "doggie"},
                    "photoUrls": {"type": "array", "items": {"type": "string"}},
                    "status": {
                        "type": "string",
                        "enum": ["available", "pending", "sold"],
                    },
                },
            }
        }
    },
}


# ── endpoint probes ────────────────────────────────────────────────────────

# Each probe: (endpoint, method, spec_fragment, context_note)
# These five cover different divergence classes.
PROOF_RUN_PROBES: list[tuple[str, str, dict, str]] = [
    (
        "/pet/findByStatus",
        "GET",
        PETSTORE_SPEC_SUBSET["paths"]["/pet/findByStatus"],
        "The spec restricts 'status' to available|pending|sold. "
        "The reference server does not enforce enum validation — arbitrary strings return 200.",
    ),
    (
        "/pet",
        "POST",
        PETSTORE_SPEC_SUBSET["paths"]["/pet"],
        "The Pet schema marks 'photoUrls' as required. "
        "Adding a pet without this field should return 4xx per spec.",
    ),
    (
        "/pet/{petId}",
        "GET",
        PETSTORE_SPEC_SUBSET["paths"]["/pet/{petId}"]["get"],
        "The spec says petId 0 or negative is 'Invalid ID' (400). "
        "The reference server may return 404 or 200 instead.",
    ),
    (
        "/store/inventory",
        "GET",
        PETSTORE_SPEC_SUBSET["paths"]["/store/inventory"],
        "The spec says the response is a map of status-string → integer count. "
        "The reference server may return an empty object {} even when pets exist.",
    ),
    (
        "/user/login",
        "GET",
        PETSTORE_SPEC_SUBSET["paths"]["/user/login"],
        "The spec documents X-Rate-Limit and X-Expires-After response headers. "
        "The reference server frequently omits these headers.",
    ),
]


# ── report assembly ───────────────────────────────────────────────────────


def _make_report(
    hypothesis: DivergenceHypothesis,
    result: ReproductionResult,
    start_ms: int,
) -> DivergenceReport:
    if result.evidence is None:
        raise ValueError("Cannot build report without evidence")
    return DivergenceReport(
        id=str(uuid.uuid4()),
        divergence_class=hypothesis.divergence_class,
        claim_a=hypothesis.claim_a,
        claim_b=hypothesis.claim_b,
        evidence=result.evidence,
        repro_steps=hypothesis.repro_steps,
        severity=hypothesis.severity,
        endpoint=hypothesis.endpoint,
        status=Status.OK,
        errors=[],
        metadata=StageMeta(
            stage="divergence_engine",
            duration_ms=int(time.time() * 1000) - start_ms,
        ),
    )


# ── main orchestration loop ───────────────────────────────────────────────


def run_proof(
    base_url: str,
    spec: dict | None = None,
    use_llm: bool = True,
    reflector: Reflector | None = None,
) -> list[DivergenceReport]:
    """
    Run the Skeptic → Witness loop against *base_url*.

    When a Reflector is provided, each reproduction result is ingested as a
    VerdictRecord (E7-1) and previously rejected hypotheses are suppressed
    from re-surfacing (E7-2 / E7-4 exit criterion).

    Args:
        base_url:  Live server base URL (e.g. "https://petstore3.swagger.io/api/v3")
        spec:      OpenAPI spec dict; defaults to the bundled Petstore subset
        use_llm:   If False, use hand-crafted hypotheses (offline / CI mode)
        reflector: Optional Reflector instance for verdict-memory learning loop.

    Returns:
        List of confirmed DivergenceReport instances.
    """
    if spec is None:
        spec = PETSTORE_SPEC_SUBSET

    skeptic = SkepticAgent(reflector=reflector) if use_llm else None
    witness = WitnessAgent(base_url=base_url)

    reports: list[DivergenceReport] = []
    t0_ms = int(time.time() * 1000)

    for endpoint, method, spec_fragment, context in PROOF_RUN_PROBES:
        print(f"\n── Probing {method} {endpoint} ──────────────────")

        if use_llm and skeptic is not None:
            hypotheses = skeptic.hypothesise(endpoint, method, spec_fragment, context)
            print(f"  Skeptic: {len(hypotheses)} hypothesis(es)")
        else:
            # Offline mode: use the hand-crafted hypotheses below
            hypotheses = _offline_hypotheses(endpoint, method)
            print(f"  Offline: {len(hypotheses)} hypothesis(es)")

        # A7 #114 — live rerank: suppress rejected fingerprints before witness loop
        if reflector is not None and hypotheses:
            before = len(hypotheses)
            hypotheses = reflector.rerank(hypotheses, endpoint=f"{method} {endpoint}")
            suppressed = before - len(hypotheses)
            if suppressed:
                print(f"  Reflector: suppressed {suppressed} rejected hypothesis(es)")

        for h in hypotheses:
            result = witness.reproduce(h)
            status = "REPRODUCED" if result.reproduced else "rejected"
            print(f"  [{status}] {h.divergence_class.value}: {h.claim_a[:80]}")

            # Feed every result into the Reflector (E7-1 / E7-4)
            if reflector is not None:
                reflector.ingest_from_reproduction(h, result)

            if result.reproduced and result.evidence:
                report = _make_report(h, result, t0_ms)
                reports.append(report)
                print(f"    Evidence: {result.evidence.request_summary}")
                print(f"    Diff    : {result.evidence.diff[:120]}")

    return reports


def _offline_hypotheses(endpoint: str, method: str) -> list[DivergenceHypothesis]:
    """
    Hand-crafted hypotheses for offline / CI use — no LLM needed.
    These encode known Petstore divergences so the proof run can verify them
    deterministically against the live server.
    """
    h: list[DivergenceHypothesis] = []
    def hid():
        return str(uuid.uuid4())

    from cherenkov.core.contracts import DivergenceClass, Severity

    if endpoint == "/pet/findByStatus" and method == "GET":
        h.append(
            DivergenceHypothesis(
                id=hid(),
                divergence_class=DivergenceClass.D1_SPEC_CODE,
                claim_a="spec: 'status' query param is enum(available|pending|sold); invalid value → 400",
                claim_b="implementation accepts arbitrary status strings and returns 200",
                predicted_evidence="GET /pet/findByStatus?status=INVALID_VALUE returns 200 with empty array",
                severity=Severity.MEDIUM,
                endpoint=f"{method} {endpoint}",
                repro_steps=[
                    "Send GET /pet/findByStatus?status=INVALID_VALUE_XYZ",
                    "Expect 400 response per spec enum constraint",
                ],
            )
        )

    elif endpoint == "/pet" and method == "POST":
        h.append(
            DivergenceHypothesis(
                id=hid(),
                divergence_class=DivergenceClass.D1_SPEC_CODE,
                claim_a="spec: Pet.photoUrls is a required field; omitting it → 4xx",
                claim_b="implementation accepts Pet without photoUrls and returns 200",
                predicted_evidence='POST /pet with body {"name":"test"} (no photoUrls) returns 200',
                severity=Severity.HIGH,
                endpoint=f"{method} {endpoint}",
                repro_steps=[
                    'Send POST /pet with body {"name": "test-dog", "status": "available"}',
                    "Expect 400 or 422 because photoUrls is required per schema",
                ],
            )
        )

    elif endpoint == "/pet/{petId}" and method == "GET":
        h.append(
            DivergenceHypothesis(
                id=hid(),
                divergence_class=DivergenceClass.D5_SPEC_PROD,
                claim_a="spec: petId=0 is 'Invalid ID supplied' → 400",
                claim_b="production returns 404 Not Found instead of 400 for petId=0",
                predicted_evidence="GET /pet/0 returns 404 instead of 400",
                severity=Severity.LOW,
                endpoint=f"{method} {endpoint}",
                repro_steps=[
                    "Send GET /pet/0",
                    "Expect 400 Invalid ID per spec",
                ],
            )
        )

    elif endpoint == "/store/inventory" and method == "GET":
        h.append(
            DivergenceHypothesis(
                id=hid(),
                divergence_class=DivergenceClass.D2_CODE_PROD,
                claim_a="spec: response is additionalProperties{integer} — a non-empty status map",
                claim_b="production returns an empty object {} even when pets are present",
                predicted_evidence="GET /store/inventory returns {} or very sparse map",
                severity=Severity.MEDIUM,
                endpoint=f"{method} {endpoint}",
                repro_steps=[
                    "Send GET /store/inventory",
                    "Expect non-empty JSON object mapping status strings to integer counts",
                ],
            )
        )

    elif endpoint == "/user/login" and method == "GET":
        h.append(
            DivergenceHypothesis(
                id=hid(),
                divergence_class=DivergenceClass.D5_SPEC_PROD,
                claim_a="spec: 200 response MUST include X-Rate-Limit and X-Expires-After headers",
                claim_b="production omits these response headers on login",
                predicted_evidence="GET /user/login?username=test&password=test returns 200 without X-Rate-Limit",
                severity=Severity.MEDIUM,
                endpoint=f"{method} {endpoint}",
                repro_steps=[
                    "Send GET /user/login?username=test&password=abc123",
                    "Expect X-Rate-Limit header in response per spec",
                ],
            )
        )

    return h


# ── CLI ────────────────────────────────────────────────────────────────────


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="CHERENKOV E3-5 Proof Run — find divergences in a real service"
    )
    parser.add_argument(
        "--base-url",
        default=PETSTORE_BASE_URL,
        help=f"Target service base URL (default: {PETSTORE_BASE_URL})",
    )
    parser.add_argument(
        "--spec",
        help="Path to OpenAPI spec JSON file (default: bundled Petstore subset)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use hand-crafted hypotheses instead of the LLM Skeptic",
    )
    parser.add_argument(
        "--reflector",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable the Reflector verdict-memory loop (default: enabled)",
    )
    parser.add_argument(
        "--reflector-stats",
        action="store_true",
        help="Print reflector statistics after the run",
    )
    parser.add_argument(
        "--learn",
        action="store_true",
        help="Offline replay: re-learn idioms from stored verdict history before the run",
    )
    parser.add_argument(
        "--output",
        help="Write divergence reports to this JSON file",
    )
    args = parser.parse_args()

    spec: dict | None = None
    if args.spec:
        spec_path = Path(args.spec)
        if not spec_path.exists():
            print(f"ERROR: spec file not found: {spec_path}", file=sys.stderr)
            sys.exit(1)
        spec = json.loads(spec_path.read_text())

    reflector: Reflector | None = None
    if args.reflector:
        store = VerdictStore()
        reflector = Reflector(store=store)

    if args.learn and reflector:
        n = reflector.learn_from_history()
        print(f"  Offline replay : {n} idiom(s) reinforced from verdict history")

    print("CHERENKOV Proof Run")
    print(f"  Target : {args.base_url}")
    print(f"  Mode   : {'offline (hand-crafted)' if args.offline else 'LLM Skeptic'}")
    print(f"  Reflector : {'enabled' if reflector else 'disabled'}")

    reports = run_proof(
        base_url=args.base_url,
        spec=spec,
        use_llm=not args.offline,
        reflector=reflector,
    )

    print(f"\n{'═' * 60}")
    print(f"PROOF RUN COMPLETE — {len(reports)} divergence(s) reproduced")
    print(f"{'═' * 60}\n")

    for i, report in enumerate(reports, 1):
        print(f"[{i}] {report.render()}\n")

    if reflector and args.reflector_stats:
        stats = reflector.get_stats()
        print("Reflector stats:")
        print(f"  Verdicts stored : {stats['verdict_count']}")
        print(f"  Idioms active   : {stats['idiom_count']}")
        print(f"  Store path      : {stats['store_path']}")

        # Persist snapshot to StatsStore
        try:
            from cherenkov.core.stats_store import StatsStore

            StatsStore().snapshot(
                verdict_count=stats.get("verdict_count", 0),
                idiom_count=stats.get("idiom_count", 0),
                source="proof_run",
            )
        except Exception as e_ss:
            print(f"  (stats snapshot failed: {e_ss})", file=sys.stderr)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(
            json.dumps([r.model_dump() for r in reports], indent=2, default=str)
        )
        print(f"Reports written to {out_path}")

    sys.exit(0 if len(reports) >= 5 else 1)


if __name__ == "__main__":
    _cli()
