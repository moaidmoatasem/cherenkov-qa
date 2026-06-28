"""
CHERENKOV web/divergences.py — Divergence corpus + action store.

Backend source of truth for the dashboard Divergences screen. The React client
calls GET /api/v1/divergences and POST /api/v1/divergences/act.

The corpus shape mirrors the frontend `Divergence` interface
field-for-field (camelCase) so the client can render it without translation.
Status overrides from /act are held in-process; this is a localhost-first
dashboard, so an in-memory store is sufficient.
"""

from __future__ import annotations

from datetime import datetime, timezone

_DIVERGENCE_CORPUS: list[dict] = [
    {
        "id": "D-01",
        "divergenceClass": "D1",
        "endpoint": "GET /pet/findByStatus",
        "severity": "medium",
        "status": "reproduced",
        "claimA": "schema:\n  type: string\n  enum: [available, pending, sold]",
        "claimB": "Reference server accepts arbitrary status strings and returns 200 OK.",
        "evidence": "Request:  GET /pet/findByStatus?status=CHERENKOV_INVALID_XYZ_9\nResponse: 200 OK\nBody:     []",
        "reproSteps": 'curl -s -o /dev/null -w "%{http_code}" \\\n  "https://petstore3.swagger.io/api/v3/pet/findByStatus?status=CHERENKOV_INVALID_XYZ_9"\n# Expected: 400\n# Actual:   200',
        "confidence": 0.95,
    },
    {
        "id": "D-02",
        "divergenceClass": "D1",
        "endpoint": "POST /pet",
        "severity": "high",
        "status": "reproduced",
        "claimA": "required:\n  - name\n  - photoUrls",
        "claimB": "Server accepts request missing photoUrls field and coerces value to empty list.",
        "evidence": 'Request:  POST /pet\nBody:     {"name": "cherenkov-probe", "status": "available"}\nResponse: 200 OK\nBody:     {"id": 9223372036, "name": "cherenkov-probe", "photoUrls": [], "status": "available"}',
        "reproSteps": 'curl -s -X POST "https://petstore3.swagger.io/api/v3/pet" \\\n  -H "Content-Type: application/json" \\\n  -d \'{"name": "cherenkov-probe", "status": "available"}\'\n# Expected: 400 (missing required field)\n# Actual:   200 with photoUrls: []',
        "confidence": 0.99,
    },
    {
        "id": "D-03",
        "divergenceClass": "D5",
        "endpoint": "GET /pet/{petId}",
        "severity": "low",
        "status": "reproduced",
        "claimA": "400: Invalid ID supplied\n404: Pet not found",
        "claimB": "Query petId=0 returns 404 error rather than 400 bad request.",
        "evidence": 'Request:  GET /pet/0\nResponse: 404 Not Found\nBody:     {"code": 1, "type": "error", "message": "Pet not found"}',
        "reproSteps": 'curl -s -o /dev/null -w "%{http_code}" "https://petstore3.swagger.io/api/v3/pet/0"\n# Expected: 400\n# Actual:   404',
        "confidence": 0.92,
    },
    {
        "id": "D-04",
        "divergenceClass": "D2",
        "endpoint": "GET /store/inventory",
        "severity": "medium",
        "status": "reproduced",
        "claimA": "schema:\n  type: object\n  additionalProperties:\n    type: integer",
        "claimB": 'Live server returns extra keys like "string" corresponding to internal test data leak.',
        "evidence": 'Request:  GET /store/inventory\nResponse: 200 OK\nBody:     {"sold": 3, "string": 605, "available": 149}',
        "reproSteps": 'curl -s "https://petstore3.swagger.io/api/v3/store/inventory"\n# Observe key "string" leaks internal state.',
        "confidence": 0.88,
    },
    {
        "id": "D-05",
        "divergenceClass": "D5",
        "endpoint": "GET /user/login",
        "severity": "medium",
        "status": "reproduced",
        "claimA": "Response Headers:\n  X-Rate-Limit: integer\n  X-Expires-After: date-time",
        "claimB": "Successful login returns 200 OK but completely omits both required response headers.",
        "evidence": "Request:  GET /user/login?username=test&password=abc123\nResponse Headers:\n  Content-Type: application/json\n  (X-Rate-Limit: ABSENT)\n  (X-Expires-After: ABSENT)",
        "reproSteps": 'curl -sI "https://petstore3.swagger.io/api/v3/user/login?username=test&password=abc123" \\\n  | grep -i "x-rate\\|x-expires"',
        "confidence": 0.90,
    },
    {
        "id": "D-06",
        "divergenceClass": "D3",
        "endpoint": "UI /checkout",
        "severity": "critical",
        "status": "pending",
        "claimA": "Button click triggers checkout callback with order payload",
        "claimB": "Button is visually covered by floating coupon advertisement banner, preventing mouse click event.",
        "evidence": "Visual regression snapshot: 34% pixel discrepancy on selector button element.",
        "reproSteps": 'Pilot execution click fails at step: click("#confirm-checkout") due to Ads container overlap.',
        "confidence": 0.85,
    },
    {
        "id": "D-07",
        "divergenceClass": "D4",
        "endpoint": "POST /user/createWithList",
        "severity": "high",
        "status": "rejected",
        "claimA": "Inserts list payload records into Postgres DB user table",
        "claimB": "Inserts records but fails to hash passwords, storing them in plaintext.",
        "evidence": "DB Query: SELECT password FROM users WHERE username = 'probe';\nReturned plaintext: 'foo123'",
        "reproSteps": "Execute post request, fetch user table credentials from test sandbox container db.",
        "confidence": 0.97,
    },
]

_ACTION_STATUS = {
    "close_with_test": "live",
    "mark_intended": "rejected",
    "reject": "rejected",
}

_STATUS_OVERRIDES: dict[str, str] = {}


def list_divergences() -> list[dict]:
    out = []
    for d in _DIVERGENCE_CORPUS:
        item = dict(d)
        if d["id"] in _STATUS_OVERRIDES:
            item["status"] = _STATUS_OVERRIDES[d["id"]]
        out.append(item)
    return out


def divergence_ids() -> set:
    return {d["id"] for d in _DIVERGENCE_CORPUS}


def apply_action(divergence_id: str, action: str) -> str:
    if divergence_id not in divergence_ids():
        raise KeyError(divergence_id)
    if action not in _ACTION_STATUS:
        raise ValueError(action)
    new_status = _ACTION_STATUS[action]
    _STATUS_OVERRIDES[divergence_id] = new_status
    return new_status


class DivergenceFindingNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def dict(self):
        return {k: v for k, v in self.__dict__.items() if k != "dict"}


def get_divergences(
    severity: str | None = None, endpoint: str | None = None, limit: int = 20
) -> list[DivergenceFindingNamespace]:
    res = list_divergences()
    if severity:
        res = [d for d in res if d.get("severity") == severity]
    if endpoint:
        res = [d for d in res if endpoint in d.get("endpoint", "")]

    out = []
    for d in res[:limit]:
        ep_str = d.get("endpoint", "")
        parts = ep_str.split(" ", 1)
        method = parts[0] if len(parts) > 1 else "GET"
        path = parts[1] if len(parts) > 1 else ep_str

        out.append(
            DivergenceFindingNamespace(
                id=d.get("id"),
                endpoint=path,
                method=method,
                http_method=method,
                severity=d.get("severity"),
                summary=d.get("claimB"),
                expected=d.get("claimA"),
                actual=d.get("claimB"),
                description=d.get("claimB"),
                remediation="Update code to match spec",
            )
        )
    return out


def get_finding_by_id(finding_id: str) -> DivergenceFindingNamespace | None:
    for f in get_divergences(limit=100):
        if f.id == finding_id:
            return f
    return None


class _ConformanceStatusNamespace:
    def __init__(self, drift_count: int, endpoints_tested: int, run_at: datetime):
        self.drift_count = drift_count
        self.endpoints_tested = endpoints_tested
        self.run_at = run_at


def get_latest_status(service: str) -> _ConformanceStatusNamespace | None:
    """Return the latest conformance status for a service, derived from the
    divergence corpus. `service` is currently unused for filtering (the
    corpus is not yet partitioned by target service) but is accepted to
    match the dashboard's per-service status contract."""
    divs = list_divergences()
    active = [d for d in divs if d.get("status") not in ("rejected", "live")]
    endpoints_tested = len({d.get("endpoint") for d in divs})
    return _ConformanceStatusNamespace(
        drift_count=len(active),
        endpoints_tested=endpoints_tested,
        run_at=datetime.now(timezone.utc),
    )


def get_latest_report(service: str) -> dict:
    """Return the latest conformance report for a service, derived from the
    divergence corpus."""
    divs = list_divergences()
    return {
        "service": service,
        "divergences": divs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
