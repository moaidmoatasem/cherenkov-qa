# Endpoints

Discovered API endpoints, methods, request/response schemas from OpenAPI spec ingestion.
Source: `cherenkov/stages/ingest.py` + `stub/target_spec.json` + `stripe_spec.json`

## Track A Target Endpoints (from `stub/target_spec.json`)

### POST /users
- **Method**: POST
- **Summary**: Create a new user
- **Request body**: `{ email: string, password: string }`
- **Responses**:
  - `201` — User created
  - `422` — Validation error (spec-defined)
- **Mutations**: happy_path, password_too_short (validation error), missing_email (omit required field)

### POST /orders
- **Method**: POST
- **Summary**: Place a new order
- **Mutations**: happy_path, missing_items, invalid_quantity

### GET /users/{id}
- **Method**: GET
- **Summary**: Retrieve user by ID
- **Responses**:
  - `200` — User found
  - `404` — Not found

## Production Spec (`stripe_spec.json`)
- 7.8 MB OpenAPI spec covering the full Stripe API
- Currently used for RAG testing (Issue #195)
- Too large for depth-1 slicing without semantic chunking

## Key Implementation Details

### Ingest Stage (`cherenkov/stages/ingest.py`)
- Supports JSON and YAML (.yaml/.yml) spec files
- Depth-1 reference resolution via `resolve_refs_depth()` (prevents context blowup)
- Mutation generation includes: happy_path, validation errors, edge cases, auth, DAST (opt-in)

### DAST Mutations (opt-in, `DAST_ENABLED`)
| Name | Payload |
|------|---------|
| sqli_tautology | `' OR '1'='1` |
| sqli_stacked | `'; DROP TABLE users;--` |
| xss_reflected | `<script>alert(1)</script>` |
| xss_attribute | `" onmouseover="alert(1)` |
| path_traversal | `../../../../etc/passwd` |
| template_injection | `${{7*7}}` |

### Mutation Types
- `happy_path` — valid request, expected success (P1 priority)
- `validation_error` — violates schema constraints (P2)
- `edge_case` — boundary values (P2)
- `auth` — authentication variations (P1)
- `security` — DAST payloads (opt-in, P2)

## Cross-references
- See `known-bugs.md` for conformance drift patterns on these endpoints
- See `test-patterns.md` for generated test examples
