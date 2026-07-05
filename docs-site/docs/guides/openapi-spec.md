---
title: OpenAPI Spec Integration
---

# OpenAPI Spec Integration

CHERENKOV supports **OpenAPI 3.x** specifications in YAML or JSON format. The spec is the single source of truth for all conformance testing — endpoints, schemas, status codes, and constraints are all derived from it.

## Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| OpenAPI 3.0 | `.yaml`, `.yml`, `.json` | Full support |
| OpenAPI 3.1 | `.yaml`, `.yml`, `.json` | Full support (JSON Schema 2020-12) |

## Point to Your Spec

```bash
# Local file
cherenkov validate --spec ./api/openapi.yaml --target http://localhost:8000

# Remote URL
cherenkov validate --spec https://example.com/openapi.json --target http://localhost:8000

# Read from stdin (pipe)
cat api.yaml | cherenkov validate --spec - --target http://localhost:8000
```

## What CHERENKOV Reads from the Spec

CHERENKOV extracts the following from your OpenAPI specification:

| Element | Used For |
|---------|----------|
| Paths + methods | Endpoint discovery and test generation |
| Request schemas | Request body and parameter validation |
| Response schemas | Response body type assertions |
| Status codes | Expected HTTP status per operation |
| Parameters (path, query, header, cookie) | Parameterized test scenarios |
| Security schemes | Authentication setup |
| `$ref` references | Resolved schema composition |

## Spec Validation on Ingest

When you run `cherenkov validate`, the spec is validated before any tests are generated:

1. **Structure check** — valid OpenAPI 3.x document
2. **Reference resolution** — all `$ref` pointers resolve
3. **Schema coherence** — no contradictory constraints
4. **Path uniqueness** — no duplicate path+method combinations

If validation fails, CHERENKOV exits with code `2` and reports the specific errors.

## Tips for Spec Quality

- Use **`example`** fields — they help the LLM generate more realistic test data
- Define **`required`** fields explicitly — CHERENKOV checks response bodies against these
- Set **`minimum`/`maximum`** on numeric fields — enables boundary testing
- Use **`enum`** for constrained values — tests will validate against allowed values
- Include **`description`** on operations — the LLM uses this for test scenario planning

A well-annotated spec produces better conformance coverage:

```yaml
paths:
  /pets:
    get:
      summary: List all pets
      description: Returns a paginated list of pets with optional filters
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
      responses:
        '200':
          description: A list of pets
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Pet'
```

## Debugging Spec Issues

```bash
# Validate just the spec parsing without running tests
cherenkov doctor

# Generate tests only (no execution) to see what CHERENKOV extracts
cherenkov generate --spec api.yaml --output ./tests
```
