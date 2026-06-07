---
last_updated: 2026-06-07
source: cherenkov/stages/ingest.py, stub/target_spec.json
scope: API endpoint inventory extracted by the ingest stage
---

# Endpoints

## Target Spec Endpoints (`stub/target_spec.json`)

| Endpoint | Method | Request Body | Responses | Schema |
|----------|--------|-------------|-----------|--------|
| `/users` | POST | `UserCreate` (email: string maxLength=50, password: string minLength=8, both required) | 201 (UserResponse), 422 (HTTPValidationError) | `UserCreate`, `UserResponse`, `HTTPValidationError`, `ValidationError` |
| `/health` | GET | None | 200 (empty) | --- |

## Dynamic Extraction (from `ingest.py`)

The ingest stage iterates `spec["paths"]` for methods GET/POST/PUT/DELETE/PATCH. It resolves `$ref` schemas via `resolve_refs_depth()` up to `Config.SCHEMA_DEPTH` and computes a **richness score** (fields + params, capped at 1.0). Endpoints with richness < 0.2 are skipped.

## Mutation Menu Structure

For each endpoint, the ingest stage generates a deterministic mutation menu:

| Mutation ID Pattern | Case Type | Expected Status | Trigger |
|---------------------|-----------|----------------|---------|
| `happy_path` | happy_path | 201 (POST) / 200 (other) | Valid request payload |
| `unauthorized` | auth | 401 | Missing/invalid auth headers |
| `missing_{field}` | validation | 422 or 400 (from spec) | Omit each required field |
| `{prop}_too_long` | validation | 422 or 400 | String exceeds maxLength |
| `{prop}_too_short` | validation | 422 or 400 | String below minLength |
| `{prop}_exceeds_max` | validation | 422 or 400 | Number exceeds maximum |
| `{prop}_below_min` | validation | 422 or 400 | Number below minimum |
| `{prop}_{payload_id}` | security | 422 or 400 | DAST payload injection (opt-in) |

## DAST Security Payloads (opt-in via `CHERENKOV_DAST_ENABLED`)

| ID | Payload | Class |
|----|---------|-------|
| `sqli_tautology` | `' OR '1'='1` | SQL Injection |
| `sqli_stacked` | `'; DROP TABLE users;--` | SQL Injection (Stacked) |
| `xss_reflected` | `<script>alert(1)</script>` | XSS Reflected |
| `xss_attribute` | `" onmouseover="alert(1)` | XSS Attribute |
| `path_traversal` | `../../../../etc/passwd` | Path Traversal |
| `template_injection` | `${{7*7}}` | SSTI |

## Dashboard API Endpoints (Track B/C, deferred)

From `track-b-c-deferred/smoke_tests/smoke_test_dashboard.py`:

| Endpoint | Method | Expected Status | Notes |
|----------|--------|----------------|-------|
| `/api/v1/health` | GET | 200 | Returns status=online, device, gen_model |
| `/tests` | GET | 200 | List of tests |
| `/review/approve` | POST | 200 | Returns status=approved |
| `/ingest` | POST | 400 | Validation error on missing input |
| `/review/reject` | POST | 200 | Returns status=rejected |
| `/review/edit` | POST | 400/200 | Validation with/without code |
| `/run` | POST | 404 | Nonexistent spec_path |
| `/eject` | POST | 200 | Returns status=ejected |
| `/divergences` | GET | 200 | Non-empty list |
| `/divergences/act` | POST | 200/404 | Reject or unknown id |

## Client Stub

Generated tests use `openapi-fetch` client from `stub/client.ts` (referenced as `client_stub_path` in `IngestOutput`).

## AI Diagnostics Stage (Track B)

The AI Diagnostics stage integrates with the Orchestrator to analyze HTTP 500s or timeouts.
It receives contextual parameters:
- `endpoint`: The failed URL path.
- `method`: HTTP method used.
- `payload`: The JSON payload (if any).
- `response_text`: Server traceback or error message.
- `status_code`: The HTTP status code received.

It heuristically determines the root cause (e.g. database disconnect, null pointer, syntax error) using the local Ollama model.

---

*Cross-ref: [test-patterns.md](test-patterns.md) for generated test code, [known-bugs.md](known-bugs.md) for conformance drift patterns*
