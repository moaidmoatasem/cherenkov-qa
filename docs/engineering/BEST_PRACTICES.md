# BEST PRACTICES

## Coding Standards
- Follow PEP 8 guidelines for Python code.
- Implement strict type hints for all functions.
- Every public function must have a descriptive docstring.
- Avoid circular imports, specifically ensuring that `domain` never imports from `adapters` or `api`.

## Testing
- **TDD (Test-Driven Development)**: Write failing tests before implementing new features.
- Maintain a minimum of 80% test coverage.
- Tests must be independent of CHERENKOV specifics so they can run without it (`eject`).
- Design invariants dictate that tests must only report and suggest; never auto-edit test code.

## Error Handling
- Follow the graceful degradation pattern. If a primary service (e.g., LocalAI) is unavailable, fallback gracefully (e.g., Ollama or Demo mode).
- Utilize structured errors that can be captured and queried via the `/healthz` endpoints.

## Logging
- Use structured JSON logging across the application.
- Include correlation IDs to track requests across different layers and adapters.

## Security
- Review and adhere to the guidelines outlined in `SECURITY.md`.
- Ensure proper sanitization of inputs in all API endpoints.
